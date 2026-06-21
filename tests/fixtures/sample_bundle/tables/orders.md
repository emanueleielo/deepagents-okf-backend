---
type: BigQuery Table
title: Orders
description: One row per completed customer order.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, revenue]
---
# Schema

| Column | Type | Description |
|--------|------|-------------|
| `order_id` | STRING | Globally unique order identifier. |
| `customer_id` | STRING | FK to [customers](customers.md). |

# Joins

Joined with [customers](customers.md) on `customer_id`.
