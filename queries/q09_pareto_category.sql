-- Q9 品类帕累托：多少个品类贡献了 80% 的 GMV
-- 业务问题：资源该集中在少数品类，还是铺开？这是选品与备货的入口问题
-- 关键写法：SUM(...) OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING) 算累计占比
-- 注意：窗口里的 ORDER BY 必须和展示的排序一致，否则累计值对不上

WITH cat_gmv AS (
    SELECT p.category,
           SUM(o.amount) AS gmv
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    WHERE o.status = 'paid'
    GROUP BY p.category
),
ranked AS (
    SELECT category,
           gmv,
           100.0 * gmv / SUM(gmv) OVER () AS pct,
           SUM(gmv) OVER (ORDER BY gmv DESC ROWS UNBOUNDED PRECEDING) AS running_gmv,
           SUM(gmv) OVER () AS total_gmv
    FROM cat_gmv
)
SELECT category,
       ROUND(gmv, 2)                                   AS gmv,
       ROUND(pct, 2)                                   AS gmv_pct,
       ROUND(100.0 * running_gmv / total_gmv, 2)       AS cum_pct
FROM ranked
ORDER BY gmv DESC;
