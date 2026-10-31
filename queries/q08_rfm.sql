-- Q8 RFM 分层
-- 业务问题：把用户分成「高价值 / 潜力 / 流失预警 / 沉睡」，运营动作才能分开做
-- 关键写法：NTILE(4) 把 R/F/M 各切成四档（4 = 最好），再用档位组合打标签
-- R 是「越小越好」，所以排序用 recency DESC —— 反向排序，别写反了

WITH per_user AS (
    SELECT user_id,
           MAX(created_at) AS last_at,
           COUNT(*)        AS freq,
           SUM(amount)     AS money
    FROM orders
    WHERE status = 'paid'
    GROUP BY user_id
),
scored AS (
    SELECT user_id,
           julianday((SELECT MAX(created_at) FROM orders WHERE status = 'paid')) - julianday(last_at) AS recency,
           freq,
           money,
           NTILE(4) OVER (ORDER BY julianday((SELECT MAX(created_at) FROM orders WHERE status = 'paid')) - julianday(last_at) DESC) AS r_score,
           NTILE(4) OVER (ORDER BY freq)   AS f_score,
           NTILE(4) OVER (ORDER BY money)  AS m_score
    FROM per_user
),
tagged AS (
    SELECT *,
           CASE
               WHEN r_score >= 3 AND f_score >= 3 THEN '高价值'
               WHEN r_score >= 3 AND f_score <= 2 THEN '潜力'
               WHEN r_score <= 2 AND f_score >= 3 THEN '流失预警'
               ELSE '沉睡'
           END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                          AS users,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM tagged), 2) AS user_pct,
       ROUND(SUM(money), 2)              AS total_gmv,
       ROUND(100.0 * SUM(money) / (SELECT SUM(money) FROM tagged), 2) AS gmv_pct,
       ROUND(AVG(recency), 0)            AS avg_recency_days,
       ROUND(AVG(freq), 2)               AS avg_orders,
       ROUND(AVG(money), 2)              AS avg_gmv
FROM tagged
GROUP BY segment
ORDER BY total_gmv DESC;
