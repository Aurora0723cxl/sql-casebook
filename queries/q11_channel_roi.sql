-- Q11 渠道 ROI：花一块钱换回几块钱，拉一个新客多少钱
-- 业务问题：五个渠道的钱该怎么分？哪个渠道是“贵但值”，哪个是“便宜但没用”
-- 关键写法：三个口径分开算再 JOIN —— 花费（财务）、GMV（订单）、新客（注册）
-- 陷阱：GMV 归因用的是「用户注册渠道」，不是「下单渠道」；归因口径不同结论会翻

WITH spend AS (
    SELECT channel, SUM(spend) AS spend
    FROM channel_spend
    GROUP BY channel
),
gmv AS (
    SELECT u.channel,
           SUM(o.amount)      AS gmv,
           COUNT(*)           AS orders,
           COUNT(DISTINCT o.user_id) AS buyers
    FROM orders o
    JOIN users u ON u.user_id = o.user_id
    WHERE o.status = 'paid'
    GROUP BY u.channel
),
newbies AS (
    SELECT channel, COUNT(*) AS new_users
    FROM users
    GROUP BY channel
)
SELECT s.channel,
       ROUND(s.spend, 0)                          AS spend,
       ROUND(g.gmv, 0)                            AS gmv,
       ROUND(g.gmv / s.spend, 2)                  AS roas,
       ROUND(s.spend / n.new_users, 2)            AS cac,
       n.new_users,
       g.buyers,
       ROUND(100.0 * g.buyers / n.new_users, 2)   AS buyer_rate_pct,
       ROUND(g.gmv / g.orders, 2)                 AS aov
FROM spend s
JOIN gmv g     ON g.channel = s.channel
JOIN newbies n ON n.channel = s.channel
ORDER BY roas DESC;
