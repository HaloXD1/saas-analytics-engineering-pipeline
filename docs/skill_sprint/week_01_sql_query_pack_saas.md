# Week 1 SQL Query Pack (SaaS Analytics Pipeline)

Goal: SQL fluency for Data Engineering internship interviews using this repo's DuckDB tables.

Run data + build warehouse (optional):

```bash
python3 -m saas_analytics.cli generate-data
python3 -m saas_analytics.cli run-pipeline --mode full
```

DuckDB file (default): `data/warehouse/saas_analytics.duckdb`

Tables: `dim_customers`, `dim_plans`, `fact_subscriptions`, `fact_invoices`, `fact_product_events`, `fact_support_tickets`.

---

## Task 1: Core SQL (15)

### 1) Paid revenue by invoice month
```sql
SELECT
  invoice_month,
  ROUND(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END), 2) AS paid_revenue
FROM fact_invoices
GROUP BY 1
ORDER BY 1;
```
Measure: paid revenue trend. Risk: mixing failed/pending with paid. Validate: compare with `mart_mrr.mrr`.

### 2) Invoice count by month
```sql
SELECT invoice_month, COUNT(*) AS invoices
FROM fact_invoices
GROUP BY 1
ORDER BY 1;
```
Measure: billing volume. Risk: duplicates. Validate: `COUNT(DISTINCT invoice_id)` vs `COUNT(*)`.

### 3) ARPA (avg revenue per paying account) by month
```sql
SELECT
  invoice_month,
  ROUND(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) / NULLIF(COUNT(DISTINCT CASE WHEN status='paid' THEN customer_id END), 0), 2) AS arpa
FROM fact_invoices
GROUP BY 1
ORDER BY 1;
```
Measure: monetization per account. Risk: NULL customer_id, partial months. Validate: spot-check a month customer list.

### 4) Top 10 customers by paid revenue (all-time)
```sql
SELECT customer_id, ROUND(SUM(amount), 2) AS paid_revenue
FROM fact_invoices
WHERE status = 'paid'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```
Measure: key accounts. Risk: refunds/credits absent. Validate: compare with subscription tiers (plan).

### 5) Customers with no paid invoices
```sql
SELECT c.customer_id, c.customer_name
FROM dim_customers c
LEFT JOIN fact_invoices i
  ON c.customer_id = i.customer_id AND i.status = 'paid'
WHERE i.customer_id IS NULL
ORDER BY 1;
```
Measure: non-paying customers. Risk: invoices missing loads. Validate: check they have `trial`/`active` subscriptions.

### 6) Invoices with missing/unknown customer_id
```sql
SELECT i.*
FROM fact_invoices i
LEFT JOIN dim_customers c ON i.customer_id = c.customer_id
WHERE i.customer_id IS NULL OR c.customer_id IS NULL
ORDER BY invoice_month, invoice_id;
```
Measure: referential integrity issues. Risk: joins silently dropping rows. Validate: row counts pre/post join.

### 7) Data quality: non-positive invoice amounts
```sql
SELECT COUNT(*) AS bad_rows
FROM fact_invoices
WHERE amount <= 0 OR amount IS NULL;
```
Measure: invalid billing rows. Risk: currency/credits semantics. Validate: sample 20 bad rows + confirm contract rules.

### 8) Paid revenue by customer segment
```sql
SELECT c.segment, ROUND(SUM(i.amount), 2) AS paid_revenue
FROM fact_invoices i
JOIN dim_customers c ON i.customer_id = c.customer_id
WHERE i.status = 'paid'
GROUP BY 1
ORDER BY 2 DESC;
```
Measure: segment value. Risk: segment changes over time (SCD). Validate: ensure `dim_customers` is latest-only.

### 9) Active subscriptions by plan
```sql
SELECT plan, COUNT(*) AS active_subscriptions
FROM fact_subscriptions
WHERE status = 'active'
GROUP BY 1
ORDER BY 2 DESC;
```
Measure: current plan mix. Risk: multiple subs per customer. Validate: `COUNT(DISTINCT customer_id)` too.

### 10) MRR by plan (active only)
```sql
SELECT plan, ROUND(SUM(mrr), 2) AS active_mrr
FROM fact_subscriptions
WHERE status = 'active'
GROUP BY 1
ORDER BY 2 DESC;
```
Measure: MRR concentration. Risk: stale statuses. Validate: compare with invoices paid by month.

### 11) Cancelled subscriptions (count + MRR) by churn month
```sql
SELECT
  DATE_TRUNC('month', CAST(end_date AS DATE))::DATE AS churn_month,
  COUNT(*) AS cancelled_subscriptions,
  ROUND(SUM(mrr), 2) AS cancelled_mrr
FROM fact_subscriptions
WHERE status = 'cancelled' AND end_date IS NOT NULL AND end_date != ''
GROUP BY 1
ORDER BY 1;
```
Measure: churn timing. Risk: end_date empty strings. Validate: `mart_churn` matches.

### 12) Support tickets by priority + status
```sql
SELECT priority, status, COUNT(*) AS tickets
FROM fact_support_tickets
GROUP BY 1,2
ORDER BY 3 DESC;
```
Measure: support load. Risk: status taxonomy drift. Validate: distinct statuses list.

### 13) Ticket rate per customer (top 10)
```sql
SELECT customer_id, COUNT(*) AS tickets
FROM fact_support_tickets
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```
Measure: noisy customers. Risk: high usage correlates with tickets (not "bad"). Validate: compare with revenue/usage.

### 14) Product events by feature
```sql
SELECT feature, COUNT(*) AS events, COUNT(DISTINCT user_id) AS users
FROM fact_product_events
GROUP BY 1
ORDER BY 2 DESC;
```
Measure: adoption. Risk: event spam/dup. Validate: check event_id uniqueness.

### 15) Duplicate IDs (invoice_id, subscription_id, ticket_id, event_id)
```sql
WITH dups AS (
  SELECT 'fact_invoices' AS table_name, COUNT(*) - COUNT(DISTINCT invoice_id) AS dup_count FROM fact_invoices
  UNION ALL
  SELECT 'fact_subscriptions', COUNT(*) - COUNT(DISTINCT subscription_id) FROM fact_subscriptions
  UNION ALL
  SELECT 'fact_support_tickets', COUNT(*) - COUNT(DISTINCT ticket_id) FROM fact_support_tickets
  UNION ALL
  SELECT 'fact_product_events', COUNT(*) - COUNT(DISTINCT event_id) FROM fact_product_events
)
SELECT * FROM dups ORDER BY dup_count DESC;
```
Measure: key health. Risk: upstream replays. Validate: enforce PK tests in dbt-style layer.

---

## Task 2: Analytics SQL (15)

### 1) Month-over-month paid revenue growth
```sql
WITH m AS (
  SELECT invoice_month, SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) AS paid_revenue
  FROM fact_invoices
  GROUP BY 1
)
SELECT
  invoice_month,
  ROUND(paid_revenue, 2) AS paid_revenue,
  ROUND(paid_revenue - LAG(paid_revenue) OVER (ORDER BY invoice_month), 2) AS mom_abs,
  ROUND((paid_revenue / NULLIF(LAG(paid_revenue) OVER (ORDER BY invoice_month), 0) - 1) * 100, 2) AS mom_pct
FROM m
ORDER BY invoice_month;
```
Measure: growth rate. Risk: missing months. Validate: fill missing months if used for charts.

### 2) Running paid revenue total
```sql
WITH m AS (
  SELECT invoice_month, SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) AS paid_revenue
  FROM fact_invoices
  GROUP BY 1
)
SELECT
  invoice_month,
  ROUND(paid_revenue, 2) AS paid_revenue,
  ROUND(SUM(paid_revenue) OVER (ORDER BY invoice_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total
FROM m
ORDER BY invoice_month;
```
Measure: cumulative revenue. Risk: backfilled historical months. Validate: recompute full history in batch.

### 3) Rank customers by monthly paid revenue
```sql
WITH cm AS (
  SELECT invoice_month, customer_id, SUM(amount) AS paid_revenue
  FROM fact_invoices
  WHERE status='paid'
  GROUP BY 1,2
)
SELECT
  invoice_month,
  customer_id,
  ROUND(paid_revenue, 2) AS paid_revenue,
  DENSE_RANK() OVER (PARTITION BY invoice_month ORDER BY paid_revenue DESC) AS revenue_rank
FROM cm
ORDER BY invoice_month, revenue_rank, customer_id;
```
Measure: top accounts by month. Risk: ties/dup invoices. Validate: compare top 5 with raw invoice exports.

### 4) Rank customers by lifetime paid revenue
```sql
WITH ltv AS (
  SELECT customer_id, SUM(amount) AS paid_revenue
  FROM fact_invoices
  WHERE status='paid'
  GROUP BY 1
)
SELECT
  customer_id,
  ROUND(paid_revenue, 2) AS lifetime_paid_revenue,
  DENSE_RANK() OVER (ORDER BY paid_revenue DESC) AS ltv_rank
FROM ltv
ORDER BY ltv_rank, customer_id;
```
Measure: account LTV proxy. Risk: ignores subscription churn/resume. Validate: compare with subscription durations.

### 5) Customer first paid invoice month
```sql
SELECT customer_id, MIN(invoice_month) AS first_paid_month
FROM fact_invoices
WHERE status='paid'
GROUP BY 1
ORDER BY 2,1;
```
Measure: acquisition timing. Risk: unpaid invoices present earlier. Validate: confirm status filter.

### 6) New customers by signup month
```sql
SELECT
  DATE_TRUNC('month', CAST(signup_date AS DATE))::DATE AS signup_month,
  COUNT(*) AS new_customers
FROM dim_customers
GROUP BY 1
ORDER BY 1;
```
Measure: acquisition volume. Risk: signup_date parsing. Validate: `TRY_CAST`/bad dates check.

### 7) Repeat paying customers by month
```sql
WITH paid AS (
  SELECT DISTINCT customer_id, invoice_month
  FROM fact_invoices
  WHERE status='paid'
),
first_paid AS (
  SELECT customer_id, MIN(invoice_month) AS first_paid_month
  FROM paid
  GROUP BY 1
)
SELECT
  p.invoice_month,
  COUNT(DISTINCT CASE WHEN p.invoice_month = f.first_paid_month THEN p.customer_id END) AS new_payers,
  COUNT(DISTINCT CASE WHEN p.invoice_month > f.first_paid_month THEN p.customer_id END) AS repeat_payers
FROM paid p
JOIN first_paid f USING (customer_id)
GROUP BY 1
ORDER BY 1;
```
Measure: retention mix. Risk: first_paid definition changes. Validate: pick 5 customers and trace months.

### 8) Churned customers (90-day inactivity; based on paid invoices)
```sql
WITH last_paid AS (
  SELECT customer_id, MAX(CAST(invoice_month AS DATE)) AS last_paid_month
  FROM fact_invoices
  WHERE status='paid'
  GROUP BY 1
)
SELECT COUNT(*) AS churned_customers_90d
FROM last_paid
WHERE last_paid_month < (CURRENT_DATE - INTERVAL 90 DAY);
```
Measure: churn proxy. Risk: invoice_month granularity (1st of month). Validate: use event_time or day-level invoices if available.

### 9) MRR by month (from mart_mrr)
```sql
SELECT invoice_month, mrr, paying_customers, arpa
FROM mart_mrr
ORDER BY invoice_month;
```
Measure: canonical KPI. Risk: mart stale. Validate: rebuild marts and compare with raw aggregation.

### 10) Churned MRR by month (from mart_churn)
```sql
SELECT churn_month, churned_customers, churned_mrr
FROM mart_churn
ORDER BY churn_month;
```
Measure: churn impact. Risk: end_date quality. Validate: cancelled subs sample check.

### 11) Feature adoption: active users per customer segment
```sql
SELECT
  c.segment,
  e.feature,
  COUNT(DISTINCT e.user_id) AS active_users
FROM fact_product_events e
JOIN dim_customers c ON e.customer_id = c.customer_id
GROUP BY 1,2
ORDER BY active_users DESC;
```
Measure: segment-feature fit. Risk: bot/duplicate users. Validate: users/day distribution sanity.

### 12) Trial conversion rate (customer-level)
```sql
WITH flags AS (
  SELECT
    customer_id,
    MAX(CASE WHEN status='trial' THEN 1 ELSE 0 END) AS ever_trial,
    MAX(CASE WHEN status='active' THEN 1 ELSE 0 END) AS ever_active
  FROM fact_subscriptions
  GROUP BY 1
)
SELECT
  ROUND(SUM(CASE WHEN ever_trial=1 AND ever_active=1 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN ever_trial=1 THEN 1 ELSE 0 END), 0) * 100, 2) AS trial_to_active_pct
FROM flags;
```
Measure: trial->active conversion proxy. Risk: lacks timeline ordering. Validate: add start_date sequencing if needed.

### 13) Data quality issue counts (from exported issues file)
```sql
SELECT issue_type, COUNT(*) AS issue_count
FROM read_csv_auto('data/exports/data_quality_issues.csv')
GROUP BY 1
ORDER BY 2 DESC;
```
Measure: quality hotspots. Risk: export out of date. Validate: rerun `validate-contracts` then compare.

### 14) Customer health score breakdown (top 20)
```sql
SELECT customer_id, customer_name, segment, revenue, product_events, support_tickets, health_score
FROM mart_customer_health
ORDER BY health_score DESC
LIMIT 20;
```
Measure: account health. Risk: scoring weights arbitrary. Validate: confirm monotonicity vs revenue, tickets.

### 15) KPI reconciliation: exported `mart_mrr.csv` vs DuckDB `mart_mrr`
```sql
WITH exp AS (
  SELECT invoice_month, CAST(mrr AS DOUBLE) AS mrr
  FROM read_csv_auto('data/exports/mart_mrr.csv')
),
db AS (
  SELECT invoice_month, CAST(mrr AS DOUBLE) AS mrr
  FROM mart_mrr
)
SELECT
  COALESCE(exp.invoice_month, db.invoice_month) AS invoice_month,
  ROUND(exp.mrr, 2) AS export_mrr,
  ROUND(db.mrr, 2) AS db_mrr,
  ROUND(COALESCE(exp.mrr,0) - COALESCE(db.mrr,0), 2) AS diff
FROM exp
FULL OUTER JOIN db USING (invoice_month)
ORDER BY invoice_month;
```
Measure: pipeline correctness. Risk: float parsing / differing builds. Validate: rerun pipeline then rerun this query.

