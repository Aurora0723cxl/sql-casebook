-- Q4 复购率与人均单量
-- 业务问题：买过的人里，有多少会再买？平均买几次？
-- 关键写法：先按用户聚合再算比率，不要在订单粒度上直接算（会重复计数）
-- 口径：只算 paid；「复购」= 支付订单数 >= 2

WITH per_user AS (
    SELECT user_id,
           COUNT(*)      AS n_orders,
           SUM(amount)   AS amount,
           MIN(created_at) AS first_at,
           MAX(created_at) AS last_at
    FROM orders
    WHERE status = 'paid'
    GROUP BY user_id
)
SELECT COUNT(*)                                                     AS buyers,
       SUM(n_orders >= 2)                                           AS repeat_buyers,
       ROUND(100.0 * SUM(n_orders >= 2) / COUNT(*), 2)              AS repeat_rate_pct,
       ROUND(AVG(n_orders), 2)                                      AS avg_orders_per_buyer,
       ROUND(AVG(CASE WHEN n_orders >= 2 THEN n_orders END), 2)     AS avg_orders_repeat_buyer,
       ROUND(AVG(amount), 2)                                        AS arpu,
       ROUND(AVG(julianday(last_at) - julianday(first_at)), 1)      AS avg_life_days
FROM per_user;
