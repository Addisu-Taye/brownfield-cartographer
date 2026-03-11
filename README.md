````markdown
# 🗺️ Brownfield Cartographer

**Codebase Intelligence System for Rapid FDE Onboarding in Production Environments**

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

A **multi-agent code intelligence system** that ingests any GitHub repository and generates a **living, queryable knowledge graph** describing the system’s architecture, data flows, and semantic structure.

Designed to help **Forward Deployed Engineers (FDEs)** understand unfamiliar production codebases in hours instead of weeks.

---

# 📋 Overview

Brownfield Cartographer addresses the **"Day-One Problem"** faced by engineers working with legacy or unfamiliar production systems.

It automatically analyzes mixed-language repositories and extracts:

- System architecture
- Data lineage
- Semantic relationships
- Operational insights

The result is a **machine-readable knowledge graph** enabling fast onboarding, system comprehension, and impact analysis.

```bash
# One command to understand any repository
uv run python src/cli.py analyze your-repo
````

---

# 🎯 The Problem

| Challenge             | Description                                                        | Solution                                                        |
| --------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------- |
| Navigation Blindness  | Engineers can search for functions but cannot visualize the system | Module import graph with PageRank identifies architectural hubs |
| Contextual Amnesia    | Every LLM session starts without system context                    | Living architecture context (`CODEBASE.md`)                     |
| Dependency Opacity    | Difficult to determine dataset dependencies                        | Automated lineage graph with blast-radius analysis              |
| Silent Technical Debt | Documentation diverges from code reality                           | Dead-code detection and documentation drift signals             |

---

# ✨ Features

## ✅ Phase 1 — Surveyor (Static Code Analysis)

* 📊 **Module Graph** — Maps imports, classes, and functions across **50+ languages**
* 📈 **Change Velocity** — Git history analysis for **30d / 90d / lifetime commits**
* 🎯 **Critical Path Detection** — PageRank highlights architectural hubs
* 💀 **Dead Code Detection** — Multi-signal unused module detection

---

## ✅ Phase 2 — Hydrologist (Data Lineage Analysis)

* 💧 **SQL Parsing** via `sqlglot` with **20+ dialects**
* 🔄 **dbt Support** including `{{ ref() }}` and `{{ source() }}`
* 📊 **CTE Extraction** separating logical vs physical tables
* 🔗 **Lineage Graph** using NetworkX `DiGraph`
* 📤 **Source Detection** for ingestion datasets

---

## 🚧 Phase 3 — Semanticist (LLM Intelligence)

Planned capabilities:

* 🤖 LLM-generated module summaries
* 📝 Documentation drift detection
* 🏷️ Domain clustering via embeddings
* 📋 Automatic **FDE onboarding brief**

---

## 🚧 Phase 4 — Archivist (Living Context System)

* 📄 Auto-generated **CODEBASE.md**
* 📑 Structured onboarding documentation
* 🔍 Semantic vector search across the codebase
* 📊 Full analysis trace logs

---

# 🏗️ Architecture

## System Architecture

*(Mermaid diagram placeholder)*

```mermaid
%% Mermaid diagram goes here
```

---

## Data Lineage Flow Example (jaffle_shop)

*(Mermaid diagram placeholder)*

```mermaid
%% Mermaid lineage diagram goes here
```

---

# 🚀 Getting Started

## Prerequisites

```bash
python --version   # Python 3.9+
pip install uv     # Recommended package manager
```

---

## Installation

```bash
git clone https://github.com/Addisu-Taye/brownfield-cartographer.git
cd brownfield-cartographer

# Install with uv
uv pip install -e .

# Or install with pip
pip install -e .
```

---

# ⚡ Quick Start

```bash
# Clone a target repository
git clone https://github.com/dbt-labs/jaffle_shop.git

# Analyze repository
uv run python src/cli.py analyze jaffle_shop

# Check analysis status
uv run python src/cli.py status jaffle_shop

# View generated artifacts
ls jaffle_shop/.cartography/
```

---

# 📖 Usage Guide

## CLI Commands

| Command           | Description                | Example                                 |
| ----------------- | -------------------------- | --------------------------------------- |
| analyze           | Run full analysis pipeline | `uv run python src/cli.py analyze repo` |
| analyze --phase 1 | Run static analysis only   | `--phase 1`                             |
| analyze --phase 2 | Run lineage analysis only  | `--phase 2`                             |
| status            | Show analysis status       | `status repo`                           |
| lineage           | Trace dataset lineage      | `lineage repo customers`                |
| blast             | Calculate blast radius     | `blast repo stg_orders`                 |
| sources           | List source datasets       | `sources repo`                          |
| sinks             | List sink datasets         | `sinks repo`                            |
| graph             | Visualize lineage graph    | `graph repo`                            |

---

# 🔎 Example Workflow

```bash
# Run full analysis
uv run python src/cli.py analyze jaffle_shop

# Inspect analysis results
uv run python src/cli.py status jaffle_shop

# List ingestion datasets
uv run python src/cli.py sources jaffle_shop

# Trace lineage
uv run python src/cli.py lineage jaffle_shop customers

# Calculate impact
uv run python src/cli.py blast jaffle_shop stg_orders
```

---

# 📊 Example Results

### jaffle_shop Analysis (March 2026)

```
Repository: dbt-labs/jaffle_shop

Files analyzed:
  SQL: 5
  YAML: 2

Lineage graph:
  Datasets: 6
  Transformations: 10
  Edges: 9

Sources:
  raw_customers
  raw_orders
  raw_payments
```

---

# 🛠️ Project Structure

```
brownfield-cartographer/
│
├── .cartography/
│   ├── module_graph.json
│   └── lineage_graph.json
│
├── src/
│   ├── agents/
│   │   ├── surveyor.py
│   │   └── hydrologist.py
│   │
│   ├── analyzers/
│   │   └── tree_sitter_analyzer.py
│   │
│   ├── models/
│   │   └── nodes.py
│   │
│   ├── graph/
│   │   └── knowledge_graph.py
│   │
│   ├── cli.py
│   └── orchestrator.py
│
├── tests/
├── pyproject.toml
├── README.md
└── interim_report.md
```

---

# 📦 Dependencies

```toml
[project]
name = "brownfield-cartographer"
version = "0.1.0"

dependencies = [
    "tree-sitter>=0.23.0",
    "tree-sitter-python>=0.23.0",
    "tree-sitter-sql>=0.23.0",
    "tree-sitter-yaml>=0.23.0",
    "sqlglot>=25.0.0",
    "networkx>=3.0",
    "gitpython>=3.1.0",
    "pydantic>=2.0.0",
    "click>=8.0.0",
    "pyyaml>=6.0"
]
```

---

# 📈 Roadmap

## Interim (Completed)

* Phase 1: Static structure analysis
* Phase 2: Core data lineage detection
* CLI interface
* Knowledge graph models

---

## Final Release (In Progress)

* Complete lineage graph
* LLM-powered semantic analysis
* CODEBASE.md generation
* Incremental git-diff analysis
* 6-minute demo video
* Automated onboarding brief

---

# 🤝 Contributing

Contributions are welcome.

```bash
git fork
git checkout -b feature/amazing-feature
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature
```

---

## Commit Convention

| Prefix   | Meaning              |
| -------- | -------------------- |
| feat     | New feature          |
| fix      | Bug fix              |
| docs     | Documentation update |
| style    | Formatting changes   |
| refactor | Code refactoring     |
| test     | Test updates         |
| chore    | Maintenance          |

---

# 📄 License

Distributed under the **MIT License**.

---

# 👥 Author

**Addisu Taye**
Lead Developer
GitHub: https://github.com/Addisu-Taye

---

# 🙏 Acknowledgments

* TRP-1 Program
* dbt Labs for `jaffle_shop`
* tree-sitter community
* sqlglot community

---

<div align="center">

⭐ **Star the repository if you find it useful**

Built with ❤️ for Forward Deployed Engineers

</div>
```
