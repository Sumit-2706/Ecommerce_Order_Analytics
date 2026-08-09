-- =====================================================================
-- analysis.sql
-- Intern Mini Project - E-Commerce Order Analytics System
-- Author: Sumit Kumar Singh | Celebal Excellence Intern (CEI)
--
-- Run against database.db (SQLite). Revenue is always calculated as:
--     quantity * unit_price * (1 - discount_percent / 100.0)
-- Returns (negative quantity rows) naturally reduce revenue since
-- quantity is negative, which correctly nets out returned value.
-- =====================================================================


-- =====================================================================
-- BASIC QUERIES
-- =====================================================================

-- 1. Total revenue per category
-- ---------------------------------------------------------------------
SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 2. Top 10 customers by total order value
-- ---------------------------------------------------------------------
SELECT
    c.customer_id,
    c.customer_name,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_order_value
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_order_value DESC
LIMIT 10;


-- 3. Month-wise order count for the last 12 months
-- ---------------------------------------------------------------------
SELECT
    strftime('%Y-%m', order_date) AS order_month,
    COUNT(DISTINCT order_id) AS order_count
FROM orders
WHERE order_date >= date('now', '-12 months')
GROUP BY order_month
ORDER BY order_month;


-- =====================================================================
-- INTERMEDIATE QUERIES
-- =====================================================================

-- 4. Customers who placed orders but never had any item delivered
-- ---------------------------------------------------------------------
SELECT
    c.customer_id,
    c.customer_name
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
HAVING SUM(CASE WHEN o.status = 'DELIVERED' THEN 1 ELSE 0 END) = 0;


-- 5. Products that were ordered but had more returns than purchases
--    (return = negative quantity rows, purchase = positive quantity rows)
-- ---------------------------------------------------------------------
SELECT
    p.product_id,
    p.product_name,
    SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) AS units_purchased,
    SUM(CASE WHEN oi.quantity < 0 THEN -oi.quantity ELSE 0 END) AS units_returned
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
HAVING units_returned > units_purchased;


-- 6. Return rate (returned items / total items) per category
-- ---------------------------------------------------------------------
SELECT
    p.category,
    SUM(CASE WHEN oi.quantity < 0 THEN -oi.quantity ELSE 0 END) AS returned_items,
    SUM(ABS(oi.quantity)) AS total_items,
    ROUND(
        100.0 * SUM(CASE WHEN oi.quantity < 0 THEN -oi.quantity ELSE 0 END)
        / NULLIF(SUM(ABS(oi.quantity)), 0), 2
    ) AS return_rate_percent
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY return_rate_percent DESC;


-- =====================================================================
-- ADVANCED QUERIES (Window Functions, CTEs, Subqueries)
-- =====================================================================

-- 7. Running total of revenue per region, ordered by date
-- ---------------------------------------------------------------------
WITH daily_region_revenue AS (
    SELECT
        o.region_code,
        date(o.order_date) AS order_date,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS daily_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY o.region_code, date(o.order_date)
)
SELECT
    region_code,
    order_date,
    ROUND(daily_revenue, 2) AS daily_revenue,
    ROUND(SUM(daily_revenue) OVER (
        PARTITION BY region_code ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS running_total
FROM daily_region_revenue
ORDER BY region_code, order_date;


-- 8. Rank products by total revenue within each category (DENSE_RANK)
-- ---------------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        p.category,
        p.product_name,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS total_revenue
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.category, p.product_name
)
SELECT
    category,
    product_name,
    ROUND(total_revenue, 2) AS total_revenue,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category
FROM product_revenue
ORDER BY category, rank_in_category;


-- 9. Days between consecutive orders per customer (LAG), flag "At Risk"
-- ---------------------------------------------------------------------
WITH customer_orders AS (
    SELECT
        customer_id,
        date(order_date) AS order_date
    FROM orders
    WHERE customer_id IS NOT NULL
),
gaps AS (
    SELECT
        customer_id,
        order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order_date,
        julianday(order_date) - julianday(
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS days_gap
    FROM customer_orders
),
avg_gap AS (
    SELECT customer_id, AVG(days_gap) AS avg_days_gap
    FROM gaps
    WHERE days_gap IS NOT NULL
    GROUP BY customer_id
)
SELECT
    g.customer_id,
    g.order_date,
    g.previous_order_date,
    g.days_gap,
    CASE WHEN a.avg_days_gap > 30 THEN 'At Risk' ELSE 'Active' END AS risk_flag
FROM gaps g
JOIN avg_gap a ON a.customer_id = g.customer_id
ORDER BY g.customer_id, g.order_date;


-- 10. Multi-level CTE: monthly revenue per customer -> tier -> counts
-- ---------------------------------------------------------------------
WITH monthly_customer_revenue AS (
    SELECT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS revenue_month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS monthly_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id, revenue_month
),
tiered AS (
    SELECT
        customer_id,
        revenue_month,
        monthly_revenue,
        CASE
            WHEN monthly_revenue > 10000 THEN 'High'
            WHEN monthly_revenue >= 5000 THEN 'Medium'
            ELSE 'Low'
        END AS revenue_tier
    FROM monthly_customer_revenue
)
SELECT
    revenue_month,
    revenue_tier,
    COUNT(DISTINCT customer_id) AS customer_count
FROM tiered
GROUP BY revenue_month, revenue_tier
ORDER BY revenue_month, revenue_tier;


-- 11. NTILE(4) customer segmentation by lifetime value
-- ---------------------------------------------------------------------
WITH customer_ltv AS (
    SELECT
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS total_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
),
quartiled AS (
    SELECT
        customer_id,
        total_value,
        NTILE(4) OVER (ORDER BY total_value DESC) AS quartile
    FROM customer_ltv
)
SELECT
    customer_id,
    ROUND(total_value, 2) AS total_value,
    quartile,
    CASE quartile
        WHEN 1 THEN 'Platinum'
        WHEN 2 THEN 'Gold'
        WHEN 3 THEN 'Silver'
        WHEN 4 THEN 'Bronze'
    END AS quartile_label
FROM quartiled
ORDER BY quartile, total_value DESC;


-- 12. Year-over-Year monthly revenue comparison
-- ---------------------------------------------------------------------
WITH monthly_revenue AS (
    SELECT
        CAST(strftime('%Y', o.order_date) AS INTEGER) AS year,
        CAST(strftime('%m', o.order_date) AS INTEGER) AS month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY year, month
)
SELECT
    curr.year,
    curr.month,
    ROUND(curr.revenue, 2) AS revenue,
    ROUND(prev.revenue, 2) AS prev_year_revenue,
    CASE
        WHEN prev.revenue IS NULL OR prev.revenue = 0 THEN NULL
        ELSE ROUND(100.0 * (curr.revenue - prev.revenue) / prev.revenue, 2)
    END AS yoy_growth_percent
FROM monthly_revenue curr
LEFT JOIN monthly_revenue prev
    ON prev.year = curr.year - 1 AND prev.month = curr.month
ORDER BY curr.year, curr.month;


-- 13. First vs most recent purchased category per customer (FIRST/LAST VALUE)
-- ---------------------------------------------------------------------
WITH customer_category_orders AS (
    SELECT
        o.customer_id,
        p.category,
        o.order_date,
        FIRST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_category,
        LAST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_category
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.customer_id IS NOT NULL
)
SELECT DISTINCT
    customer_id,
    first_category,
    last_category,
    CASE WHEN first_category != last_category THEN 'Yes' ELSE 'No' END AS category_shift
FROM customer_category_orders
ORDER BY customer_id;


-- 14. Cumulative revenue distribution (what % comes from top customers)
-- ---------------------------------------------------------------------
WITH customer_revenue AS (
    SELECT
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
),
ranked AS (
    SELECT
        customer_id,
        revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
        SUM(revenue) OVER () AS grand_total
    FROM customer_revenue
)
SELECT
    customer_id,
    ROUND(revenue, 2) AS revenue,
    ROUND(cumulative_revenue, 2) AS cumulative_revenue,
    ROUND(100.0 * cumulative_revenue / grand_total, 2) AS cumulative_percent
FROM ranked
ORDER BY revenue DESC;


-- 15. Cohort analysis: registration-month cohorts, retention by month 0-3
-- ---------------------------------------------------------------------
WITH cohorts AS (
    SELECT
        customer_id,
        strftime('%Y-%m', registration_date) AS cohort_month
    FROM customers
),
customer_order_months AS (
    SELECT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS order_month
    FROM orders o
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id, order_month
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        c.customer_id,
        CAST(
            (strftime('%Y', com.order_month || '-01') - strftime('%Y', c.cohort_month || '-01')) * 12 +
            (strftime('%m', com.order_month || '-01') - strftime('%m', c.cohort_month || '-01'))
        AS INTEGER) AS month_number
    FROM cohorts c
    JOIN customer_order_months com ON com.customer_id = c.customer_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.cohort_size,
    COUNT(DISTINCT CASE WHEN ca.month_number = 0 THEN ca.customer_id END) AS month_0,
    COUNT(DISTINCT CASE WHEN ca.month_number = 1 THEN ca.customer_id END) AS month_1,
    COUNT(DISTINCT CASE WHEN ca.month_number = 2 THEN ca.customer_id END) AS month_2,
    COUNT(DISTINCT CASE WHEN ca.month_number = 3 THEN ca.customer_id END) AS month_3,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN ca.month_number = 1 THEN ca.customer_id END) / cs.cohort_size, 2) AS retention_month_1_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN ca.month_number = 2 THEN ca.customer_id END) / cs.cohort_size, 2) AS retention_month_2_pct,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN ca.month_number = 3 THEN ca.customer_id END) / cs.cohort_size, 2) AS retention_month_3_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON cs.cohort_month = ca.cohort_month
GROUP BY ca.cohort_month, cs.cohort_size
ORDER BY ca.cohort_month;


-- 16. Frequently bought together products (self-join, A-B once only)
-- ---------------------------------------------------------------------
SELECT
    pa.product_name AS product_a,
    pb.product_name AS product_b,
    COUNT(*) AS times_bought_together
FROM order_items oi1
JOIN order_items oi2
    ON oi1.order_id = oi2.order_id
    AND oi1.product_id < oi2.product_id   -- avoids A-B/B-A duplicates and self-pairs
JOIN products pa ON pa.product_id = oi1.product_id
JOIN products pb ON pb.product_id = oi2.product_id
GROUP BY pa.product_name, pb.product_name
ORDER BY times_bought_together DESC
LIMIT 20;
