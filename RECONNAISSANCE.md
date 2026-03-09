# RECONNAISSANCE.md

## Manual Day-One Analysis: dbt's jaffle_shop

**Date:** March 9, 2026  
**Target Repository:** dbt-labs/jaffle_shop  
**Analysis Time:** 30 minutes  
**Analyst:** Manual Reconnaissance  

---

# Executive Summary

`jaffle_shop` is a fictional e-commerce dbt project used as the canonical example for dbt training. It demonstrates a simple but complete data transformation pipeline from raw CSV seeds to analytical models.

The codebase is stable (last meaningful code changes in 2022) and intentionally minimal, making it an ideal ground truth for validating the Cartographer's outputs.

---

# The Five FDE Day-One Questions

## Q1: What is the primary data ingestion path?

**Answer:** CSV seed files → Staging models

### Evidence

**Entry points**

- `seeds/raw_customers.csv`
- `seeds/raw_orders.csv`
- `seeds/raw_payments.csv`

**First transformations**

- `models/staging/stg_customers.sql`
- `models/staging/stg_orders.sql`
- `models/staging/stg_payments.sql`

**Configuration**

- `dbt_project.yml` seeds configuration

### Lineage

```
raw_customers.csv ──► stg_customers.sql
raw_orders.csv    ──► stg_orders.sql
raw_payments.csv  ──► stg_payments.sql
```

---

## Q2: What are the 3–5 most critical output datasets?

**Answer:** The analytical models in the root `models/` directory.

| Dataset | Path | Purpose | Downstream Dependents |
|------|------|------|------|
| customers | models/customers.sql | Customer 360 view with lifetime value | None (terminal node) |
| orders | models/orders.sql | Enriched orders with payment breakdown | None (terminal node) |
| stg_customers | models/staging/stg_customers.sql | Cleaned customer data | customers |
| stg_orders | models/staging/stg_orders.sql | Cleaned order data | customers, orders |
| stg_payments | models/staging/stg_payments.sql | Cleaned payment data | customers, orders |

**Critical path:**  
All paths lead to `customers.sql` and `orders.sql` as the final output nodes.

---

## Q3: What is the blast radius if the most critical module fails?

**Selected critical module:**  
`models/customers.sql`

### Upstream dependencies (what it needs)

- `stg_customers` via `{{ ref('stg_customers') }}`
- `stg_orders` via `{{ ref('stg_orders') }}`
- `stg_payments` via `{{ ref('stg_payments') }}`

### Downstream impact (what breaks)

**Direct**

- Any BI tool or dashboard querying the `customers` table

**Indirect**

- None within the repository (no models depend on `customers`)

### Dependency Graph

```
stg_customers ──┐
stg_orders    ──┼──► customers
stg_payments  ──┘

stg_orders    ──┐
stg_payments  ──┼──► orders
```

**If `stg_orders` fails (higher impact):**

Both **customers** AND **orders** break.

**Blast radius = 2 critical models**

---

## Q4: Where is the business logic concentrated?

Business logic is distributed across SQL models with different responsibilities.

| Logic Type | Location | Examples |
|------|------|------|
| Analytical / ML Features | models/customers.sql | Customer lifetime value (LTV), first/last order dates, order count |
| Business Rules | models/orders.sql | Payment method attribution, order status handling |
| Data Cleaning | models/staging/*.sql | Column renaming, type casting, null handling |
| Business Definitions | models/schema.yml | Tests, column descriptions, terminology |

### Key Business Logic Snippet (customers.sql)

```sql
select
    customers.customer_id,
    customers.first_name,
    customers.last_name,
    min(orders.order_date) as first_order,
    max(orders.order_date) as most_recent_order,
    count(orders.order_id) as number_of_orders,
    sum(payments.amount) as lifetime_value
from ...
```

Core business metric: **lifetime_value**

### Key Business Logic Snippet (orders.sql - Jinja Pivot)

```sql
{%- for payment_method in ['credit_card', 'coupon', 'bank_transfer', 'gift_card'] %}
sum(case when payment_method = '{{payment_method}}' then amount else 0 end) as {{payment_method}}_amount
{%- endfor %}
```

---

## Q5: What has changed most frequently in the last 90 days?

**Analysis period:** December 2025 – March 2026

| File | Recent Changes | Change Type | Velocity |
|----|----|----|----|
| README.md | fd7bfac (typo fix), 81ddf7b (disclaimer) | Documentation | HIGH 🔴 |
| dbt_project.yml | b1680f3, ec36ae1 (Feb 2022) | Config updates | NONE |
| SQL models | No commits in analyzed period | Code | NONE |
| Seed CSVs | No commits in analyzed period | Data | NONE |

### Change Velocity Insights

Active development:
- README only (documentation maintenance)

Stable/dead code:
- All SQL models and seeds (last changed ~4 years ago)

Project status:
- **Maintenance mode** (explicitly stated in README)

### 30-Day Change Frequency

```
README.md: 2 changes (100% of recent activity)
All other files: 0 changes
```

---

# What Was Hardest to Figure Out Manually?

| Task | Difficulty | Why |
|----|----|----|
| Blast radius mapping | 8/10 | Had to manually trace `ref()` calls across many files |
| Change velocity quantification | 9/10 | Required manual `git log` analysis |
| Business logic identification | 6/10 | Needed to separate cleaning vs business logic |
| Critical path identification | 5/10 | Follow dependency chain manually |
| Dead code detection | 7/10 | Hard to verify if seeds are still source of truth |

---

# Where Did I Get Lost?

### 1. Blindness to Jinja Complexity

Initial pass missed that `orders.sql` contains Jinja loops generating dynamic SQL.

### 2. False Assumption About Directory Structure

Initially assumed `models/marts/` existed based on dbt conventions.

### 3. Git History Rabbit Hole

Spent time exploring commits before realizing meaningful code changes stopped in 2022.

### 4. schema.yml Blind Spot

Nearly missed that `schema.yml` contains important business definitions and tests.

### 5. Unclear Dead Code Signals

Staging models are referenced, but unclear whether CSV seeds are still the active data source.

---

# Cartographer Requirements Emerging from This Analysis

The Cartographer MUST:

- Parse dbt `ref()` functions across multiple files
- Understand Jinja templating
- Analyze git history with file-level granularity
- Parse YAML configs (`schema.yml`, `dbt_project.yml`)
- Detect dead code candidates
- Handle multiple SQL dialects
- Trace lineage across language boundaries (CSV → SQL → YAML)

---

# Ground Truth Data for Validation

When the Cartographer runs on `jaffle_shop`, expected outputs:

| Expected Output | Ground Truth |
|----|----|
| Number of modules | 8 SQL + 3 CSV + 2 YAML + 1 MD |
| Source nodes | raw_customers, raw_orders, raw_payments |
| Sink nodes | customers, orders |
| Most referenced module | stg_orders |
| Circular dependencies | None (pure DAG) |
| High velocity files | README.md |
| Documentation drift | Unknown |

---

# Manual vs Automated: What I'd Pay For

If entering this codebase blind, the Cartographer should immediately provide:

- **DAG visualization**
- **Critical path files**
- **Dead code alerts**
- **Business logic location**
- **Change velocity insights**

Examples:

- "Here's the DAG visualization"
- "These 3 files are the critical path"
- "This model hasn't changed in 4 years"
- "Business logic lives in customers.sql LTV calc and orders.sql payment pivot"
- "README changed recently but core code is stable"