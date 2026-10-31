-- Q7 连续活跃天数（gap and islands）
-- 业务问题：谁在连续来？连续活跃是留存最强的正向信号。
-- 关键写法：用「日期序号 - 行号」作为分组键，连续日期会得到同一个键
-- 这是 SQL 里最经典的一类题，考的是能不能把「连续」翻译成「同一个分组」

WITH active AS (
    SELECT DISTINCT user_id, date(ts) AS d
    FROM events
    WHERE user_id IS NOT NULL
),
grouped AS (
    SELECT user_id,
           d,
           julianday(d) - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY d) AS grp
    FROM active
),
runs AS (
    SELECT user_id,
           COUNT(*) AS streak_days,
           MIN(d)   AS run_start,
           MAX(d)   AS run_end
    FROM grouped
    GROUP BY user_id, grp
)
SELECT user_id,
       MAX(streak_days) AS max_streak,
       COUNT(*)         AS run_count
FROM runs
GROUP BY user_id
ORDER BY max_streak DESC, user_id
LIMIT 15;
