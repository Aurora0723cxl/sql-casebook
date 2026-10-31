-- Q3 渠道转化漏斗：曝光 → 点击 → 加购 → 下单 → 支付
-- 业务问题：哪个渠道“看着热闹、实际不成交”？钱该往哪挪？
-- 关键写法：imps 与 events 分别聚合再 JOIN，避免多对多把曝光数放大（这是最常见的错）
-- 口径：曝光来自广告后台（汇总数），点击及之后来自埋点（用户级）

WITH imps AS (
    SELECT channel, SUM(impressions) AS imp
    FROM impressions
    GROUP BY channel
),
ev AS (
    SELECT channel,
           SUM(event_type = '点击') AS click,
           SUM(event_type = '加购') AS cart,
           SUM(event_type = '下单') AS ord,
           SUM(event_type = '支付') AS pay
    FROM events
    GROUP BY channel
)
SELECT i.channel,
       i.imp,
       e.click,
       e.cart,
       e.ord,
       e.pay,
       ROUND(100.0 * e.click / i.imp, 3) AS ctr_pct,
       ROUND(100.0 * e.cart / e.click, 2) AS click_to_cart_pct,
       ROUND(100.0 * e.ord / e.cart, 2)  AS cart_to_order_pct,
       ROUND(100.0 * e.pay / e.ord, 2)   AS order_to_pay_pct,
       ROUND(100.0 * e.pay / i.imp, 3)   AS cvr_pct
FROM imps i
JOIN ev e ON e.channel = i.channel
ORDER BY cvr_pct DESC;
