-- Q5 首次复购间隔分布
-- 业务问题：第二单通常在下单后多少天来？召回券应该第几天发？
-- 关键写法：ROW_NUMBER 给每个用户排号，用 rn 与 rn+1 自连接取相邻两单
-- 业务结论：间隔中位数落在哪个桶，就把召回触达放在那个窗口之前

WITH numbered AS (
    SELECT user_id,
           created_at,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) AS rn
    FROM orders
    WHERE status = 'paid'
),
first_repeat AS (
    SELECT a.user_id,
           julianday(b.created_at) - julianday(a.created_at) AS gap_days
    FROM numbered a
    JOIN numbered b
      ON b.user_id = a.user_id
     AND b.rn = a.rn + 1
    WHERE a.rn = 1
),
bucketed AS (
    SELECT CASE
               WHEN gap_days <= 7  THEN '1　0–7 天'
               WHEN gap_days <= 30 THEN '2　8–30 天'
               WHEN gap_days <= 90 THEN '3　31–90 天'
               ELSE '4　90 天以上'
           END AS bucket,
           gap_days
    FROM first_repeat
)
SELECT bucket,
       COUNT(*)                                                        AS users,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM bucketed), 2)     AS share_pct,
       ROUND(AVG(gap_days), 1)                                         AS avg_days
FROM bucketed
GROUP BY bucket
ORDER BY bucket;
