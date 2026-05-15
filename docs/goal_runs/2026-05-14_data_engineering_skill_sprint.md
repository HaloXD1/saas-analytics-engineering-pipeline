# Data Engineering Skill Sprint - 2026-05-14

Focus: Week 1 (SQL foundations) execution on SaaS warehouse tables in this repo.

## 2 Skill Tasks

1) Core SQL: answer 15 business questions on `fact_invoices`, `fact_subscriptions`, `dim_customers` (joins, CTEs, agg, NULL handling).
2) Analytics SQL: answer 15 KPI questions (windows, ranks, growth, churn proxy, reconciliation).

## Mini Deliverable

- Completed query + explanation pack: `docs/skill_sprint/week_01_sql_query_pack_saas.md`.

## 5 Interview Questions (with answer guidance)

1) Grain: "Why does grain matter in KPI SQL?"
   - Guidance: define entity+time level first; joins must not explode rows; aggregate after dedup; validate totals.
2) LEFT JOIN pitfalls: "How can LEFT JOIN still drop rows?"
   - Guidance: predicates in `WHERE` on right table turn it into INNER; put filters in `ON` when preserving left.
3) Window vs GROUP BY: "When use windows instead of GROUP BY?"
   - Guidance: windows keep detail rows + add metrics (rank, running totals); group by collapses rows.
4) MoM growth edge cases: "What breaks MoM %?"
   - Guidance: missing months, zero prior month, backfills; use `NULLIF`, generate calendar, document behavior.
5) Reconciliation: "How to trust a mart/export?"
   - Guidance: recompute from base facts; compare totals by month; sample-level spot checks; automate in health check.

## Weak-Skill Note

- Watch for: filters placed in `WHERE` after a LEFT JOIN; do 3 drills rewriting filters into `ON` + validate row counts.

## Next Sprint Step

- Week 2 (Analytics SQL deeper): rewrite 5 of these using calendar tables + stricter churn definitions.

## Blockers / Notes

- Sandbox note: I cannot write to `/Users/ahmedyasser/Documents/NotUseless/Intern/ahmed-yasser-portfolio/docs/goal_runs/`; copy this log there if needed.

