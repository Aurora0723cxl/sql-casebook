-- Q10 退款率异常：哪个品类在哪个月“不正常”
-- 业务问题：退款率突然抬升，是偶发还是系统性问题？
-- 关键写法：先算「品类 × 月」的退款率，再和该品类自己的历史均值比（基线要选对）
-- 为什么不用全站均值：品类之间退款率天生不同，拿全站均值会把正常波动当异常

WITH monthly AS (
    SELECT p.category,
           substr(o.created_at, 1, 7) AS ym,
           COUNT(*)                   AS orders,
           SUM(o.status = 'refunded') AS refunds
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.status IN ('paid', 'refunded')
    GROUP BY 1, 2
),
rated AS (
    SELECT category,
           ym,
           orders,
           refunds,
           100.0 * refunds / orders AS rate
    FROM monthly
),
baseline AS (
    SELECT category,
           AVG(rate) AS avg_rate
    FROM rated
    GROUP BY category
)
SELECT r.category,
       r.ym,
       r.orders,
       r.refunds,
       ROUND(r.rate, 2)                                AS refund_rate_pct,
       ROUND(b.avg_rate, 2)                            AS category_avg_pct,
       ROUND(r.rate - b.avg_rate, 2)                   AS diff_pp,
       ROUND(r.rate / b.avg_rate, 2)                   AS times_of_avg
FROM rated r
JOIN baseline b ON b.category = r.category
WHERE r.orders >= 30
  AND r.rate > b.avg_rate * 1.8
ORDER BY diff_pp DESC;
