# Data Model

## Silver Tables

- `dim_customers`
- `dim_plans`
- `fact_subscriptions`
- `fact_invoices`
- `fact_product_events`
- `fact_support_tickets`

## Gold Marts

- `mart_mrr`
- `mart_churn`
- `mart_feature_adoption`
- `mart_customer_health`
- `executive_overview`

The model separates raw source files, cleaned warehouse tables, and KPI marts.

## ERD

```mermaid
erDiagram
    dim_customers {
        string customer_id
        string customer_name
        string segment
        string signup_date
    }
    dim_plans {
        string plan
        int monthly_price
        int tier
    }
    fact_subscriptions {
        string subscription_id
        string customer_id
        string plan
        float mrr
        string status
    }
    fact_invoices {
        string invoice_id
        string customer_id
        float amount
        string status
        string invoice_month
    }
    fact_product_events {
        string event_id
        string customer_id
        string user_id
        string feature
        string event_time
    }
    fact_support_tickets {
        string ticket_id
        string customer_id
        string priority
        string status
    }
    dim_customers ||--o{ fact_subscriptions : has
    dim_customers ||--o{ fact_invoices : billed
    dim_customers ||--o{ fact_product_events : uses
    dim_customers ||--o{ fact_support_tickets : opens
    dim_plans ||--o{ fact_subscriptions : prices
```
