-- Q1 每日 GMV 与 7 日移动平均
-- 业务问题：大盘每天在涨还是在跌？去掉单日噪声后趋势如何？
-- 关键写法：窗口函数 ROWS BETWEEN 6 PRECEDING AND CURRENT ROW 做移动平均
-- 注意：只统计 paid，退款不计入 GMV（口径写清楚，换口径要同步改所有查询）

WITH daily AS (
    SELECT date(created_at) AS d,
           COUNT(*)         AS orders,
           SUM(amount)      AS gmv
    FROM orders
    WHERE status = 'paid'
    GROUP BY 1
)
SELECT d,
       orders,
       ROUND(gmv, 2) AS gmv,
       ROUND(AVG(gmv) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS gmv_ma7
FROM daily
ORDER BY d;
