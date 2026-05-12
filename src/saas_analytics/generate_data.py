from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from saas_analytics.config import ensure_parent, load_settings, project_path

SEGMENTS = ["Startup", "SMB", "Mid-Market", "Enterprise"]
COUNTRIES = ["Egypt", "UAE", "Saudi Arabia", "Germany", "Netherlands"]
PLANS = {"Starter": 49, "Growth": 149, "Scale": 399}
FEATURES = ["Dashboard", "Reports", "Automation", "Integrations", "Billing"]
EVENT_TYPES = ["view", "click", "export", "create"]
TICKET_CATEGORIES = ["billing", "bug", "onboarding", "feature_request"]


def generate_all() -> dict[str, Path]:
    settings = load_settings()
    random.seed(settings["generator"]["seed"])

    customers = generate_customers(settings["generator"]["customers"])
    subscriptions = generate_subscriptions(customers)
    invoices = generate_invoices(subscriptions)
    product_events = generate_product_events(customers, settings["generator"]["events"])
    support_tickets = generate_support_tickets(customers, settings["generator"]["tickets"])

    outputs = {
        "customers": project_path(settings["raw_files"]["customers"]),
        "subscriptions": project_path(settings["raw_files"]["subscriptions"]),
        "invoices": project_path(settings["raw_files"]["invoices"]),
        "product_events": project_path(settings["raw_files"]["product_events"]),
        "support_tickets": project_path(settings["raw_files"]["support_tickets"]),
    }
    _write_csv(customers, outputs["customers"])
    _write_csv(subscriptions, outputs["subscriptions"])
    _write_csv(invoices, outputs["invoices"])
    _write_jsonl(product_events, outputs["product_events"])
    _write_csv(support_tickets, outputs["support_tickets"])
    return outputs


def generate_customers(count: int) -> pd.DataFrame:
    rows = []
    for index in range(1, count + 1):
        rows.append(
            {
                "customer_id": f"C-{index:04d}",
                "customer_name": f"Customer {index}",
                "segment": random.choice(SEGMENTS),
                "country": random.choice(COUNTRIES),
                "signup_date": _random_date(date(2024, 1, 1), date(2025, 6, 30)).isoformat(),
            }
        )
    frame = pd.DataFrame(rows)
    return pd.concat([frame, frame.iloc[[2]]], ignore_index=True)


def generate_subscriptions(customers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    clean_customers = customers.drop_duplicates("customer_id")
    for index, customer in enumerate(clean_customers.itertuples(index=False), start=1):
        plan = random.choice(list(PLANS))
        start_date = _random_date(date(2025, 1, 1), date(2025, 5, 31))
        status = random.choice(["active", "active", "active", "trial", "cancelled"])
        end_date = ""
        if status == "cancelled":
            end_date = (start_date + timedelta(days=random.randint(45, 250))).isoformat()
        mrr = PLANS[plan]
        if index % 41 == 0:
            mrr = -10
        rows.append(
            {
                "subscription_id": f"S-{index:05d}",
                "customer_id": customer.customer_id if index % 37 else "C-9999",
                "plan": plan,
                "start_date": start_date.isoformat(),
                "end_date": end_date,
                "status": status,
                "mrr": mrr,
            }
        )
    frame = pd.DataFrame(rows)
    return pd.concat([frame, frame.iloc[[4]]], ignore_index=True)


def generate_invoices(subscriptions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    invoice_index = 1
    for subscription in subscriptions.drop_duplicates("subscription_id").itertuples(index=False):
        if subscription.mrr <= 0 or subscription.customer_id == "C-9999":
            continue
        start_month = pd.Period(subscription.start_date, freq="M")
        end_month = pd.Period("2025-12", freq="M")
        if subscription.end_date:
            end_month = min(end_month, pd.Period(subscription.end_date, freq="M"))
        for month in pd.period_range(start_month, end_month, freq="M"):
            status = random.choice(["paid", "paid", "paid", "failed", "refunded"])
            amount = float(subscription.mrr)
            if status == "failed":
                amount = round(amount * 0.5, 2)
            rows.append(
                {
                    "invoice_id": f"I-{invoice_index:06d}",
                    "customer_id": subscription.customer_id,
                    "invoice_month": month.start_time.date().isoformat(),
                    "amount": amount,
                    "status": status,
                }
            )
            invoice_index += 1
    return pd.DataFrame(rows)


def generate_product_events(customers: pd.DataFrame, count: int) -> pd.DataFrame:
    customer_ids = customers["customer_id"].drop_duplicates().tolist()
    rows = []
    for index in range(1, count + 1):
        customer_id = random.choice(customer_ids)
        rows.append(
            {
                "event_id": f"E-{index:07d}",
                "customer_id": customer_id if index % 101 else "C-9999",
                "user_id": f"U-{random.randint(1, 350):04d}",
                "event_time": _random_date(date(2025, 1, 1), date(2025, 12, 31)).isoformat(),
                "feature": random.choice(FEATURES),
                "event_type": random.choice(EVENT_TYPES),
            }
        )
    return pd.DataFrame(rows)


def generate_support_tickets(customers: pd.DataFrame, count: int) -> pd.DataFrame:
    customer_ids = customers["customer_id"].drop_duplicates().tolist()
    rows = []
    for index in range(1, count + 1):
        rows.append(
            {
                "ticket_id": f"T-{index:05d}",
                "customer_id": random.choice(customer_ids),
                "opened_date": _random_date(date(2025, 1, 1), date(2025, 12, 31)).isoformat(),
                "priority": random.choice(["low", "medium", "medium", "high"]),
                "status": random.choice(["open", "solved", "solved"]),
                "category": random.choice(TICKET_CATEGORIES),
            }
        )
    return pd.DataFrame(rows)


def _random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    ensure_parent(path)
    frame.to_csv(path, index=False)


def _write_jsonl(frame: pd.DataFrame, path: Path) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as file:
        for row in frame.to_dict(orient="records"):
            file.write(json.dumps(row) + "\n")
