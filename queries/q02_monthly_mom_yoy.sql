-- Q2 月度 GMV 的环比（MoM）与同比（YoY）
-- 业务问题：这个月比上月怎么样？比去年同月怎么样？
-- 关键写法：LAG(x, 1) 做环比、LAG(x, 12) 做同比——前提是月份连续、不能缺月
-- 面试常被追问：如果某个月没有订单怎么办？（答案：用日历表左连接补齐，不能直接 LAG）

WITH monthly AS (
    SELECT substr(created_at, 1, 7) AS ym,
           SUM(amount)              AS gmv
    FROM orders
    WHERE status = 'paid'
    GROUP BY 1
)
SELECT ym,
       ROUND(gmv, 2) AS gmv,
       ROUND(100.0 * (gmv - LAG(gmv, 1) OVER (ORDER BY ym)) / LAG(gmv, 1) OVER (ORDER BY ym), 2) AS mom_pct,
       ROUND(100.0 * (gmv - LAG(gmv, 12) OVER (ORDER BY ym)) / LAG(gmv, 12) OVER (ORDER BY ym), 2) AS yoy_pct
FROM monthly
ORDER BY ym;
