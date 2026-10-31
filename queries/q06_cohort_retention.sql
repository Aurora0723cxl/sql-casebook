-- Q6 队列留存：按「首单月份」分组，看第 0/1/2/3 个月还有多少人下单
-- 业务问题：拉来的用户，第二个月还在吗？哪一批用户质量最高？
-- 关键写法：把「年月」转成「月序号」（年*12+月）再相减，避免跨年算错
-- 面试常被追问：留存分母是谁？（答案：该队列在首月的去重下单用户数）

WITH first_order AS (
    SELECT user_id,
           substr(MIN(created_at), 1, 7) AS cohort
    FROM orders
    WHERE status = 'paid'
    GROUP BY user_id
),
activity AS (
    SELECT DISTINCT user_id, substr(created_at, 1, 7) AS ym
    FROM orders
    WHERE status = 'paid'
),
joined AS (
    SELECT f.cohort,
           a.user_id,
           (CAST(substr(a.ym, 1, 4) AS INTEGER) * 12 + CAST(substr(a.ym, 6, 2) AS INTEGER))
         - (CAST(substr(f.cohort, 1, 4) AS INTEGER) * 12 + CAST(substr(f.cohort, 6, 2) AS INTEGER)) AS m
    FROM first_order f
    JOIN activity a ON a.user_id = f.user_id
)
SELECT cohort,
       COUNT(DISTINCT user_id)                                                          AS cohort_size,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 0 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m0_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 1 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m1_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 2 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m2_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 3 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m3_pct
FROM joined
GROUP BY cohort
ORDER BY cohort;
