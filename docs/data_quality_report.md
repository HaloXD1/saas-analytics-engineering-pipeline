# Data Quality Report

| table_name      | raw_rows | clean_rows | rejected_rows | validation_issues | quality_score |
| --------------- | -------- | ---------- | ------------- | ----------------- | ------------- |
| customers       | 101      | 100        | 1             | 1                 | 0.9901        |
| subscriptions   | 101      | 96         | 5             | 5                 | 0.9505        |
| invoices        | 919      | 919        | 0             | 0                 | 1.0           |
| product_events  | 1800     | 1783       | 17            | 17                | 0.9906        |
| support_tickets | 140      | 140        | 0             | 0                 | 1.0           |

## Issue Breakdown

| table_name     | issue_type          | issue_count |
| -------------- | ------------------- | ----------- |
| customers      | duplicate_key       | 1           |
| product_events | missing_foreign_key | 17          |
| subscriptions  | duplicate_key       | 1           |
| subscriptions  | missing_foreign_key | 2           |
| subscriptions  | numeric_below_min   | 2           |
