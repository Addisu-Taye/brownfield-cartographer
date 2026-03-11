# 🗺️ Brownfield Cartographer

Codebase Intelligence Systems for Rapid FDE Onboarding in Production Environments

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

A multi-agent system that ingests any GitHub repository and produces a living, queryable knowledge graph of the system's architecture, data flows, and semantic structure.

---

## 📋 Overview

The Brownfield Cartographer solves the "Day-One Problem" faced by Forward Deployed Engineers (FDEs): understanding an unfamiliar production codebase within 72 hours. It builds instruments that make codebases legible by extracting structure, data lineage, and semantics from mixed-language data engineering repositories.

```bash
# One command to understand any codebase
uv run python src/cli.py analyze your-repo
🎯 The Problem
Challenge	Description	Our Solution
Navigation Blindness	You can grep for function names but cannot see the system	Module import graph with PageRank to identify critical paths
Contextual Amnesia	Every LLM session starts from zero	Living context (CODEBASE.md) for architectural awareness
Dependency Opacity	Cannot answer "What produces this dataset?"	Data lineage graph with blast radius analysis
Silent Debt	Documentation drifts from reality	Dead code detection and doc drift flags
✨ Features
✅ Phase 1: Surveyor (Static Structure Analysis) - Complete
📊 Module Graph: Maps imports, functions, classes across 50+ languages
📈 Change Velocity: Git log analysis for 30d/90d/total commit frequency
🎯 Critical Path: PageRank identifies architectural hubs
💀 Dead Code: Detects unused modules with multi-signal analysis
✅ Phase 2: Hydrologist (Data Lineage) - Core Complete
💧 SQL Parsing: sqlglot with 20+ dialect support (Postgres, BigQuery, Snowflake)
🔄 dbt Support: Handles {{ ref() }} and {{ source() }} Jinja syntax
📊 CTE Extraction: Distinguishes temporary tables from physical tables
🔗 Lineage Graph: NetworkX DiGraph with CONSUMES/PRODUCES relationships
📤 Source Detection: Identifies ingestion points (raw_customers, raw_orders)
🚧 Phase 3: Semanticist (LLM Analysis) - Coming Soon
🤖 Purpose Statements: LLM-generated module summaries
📝 Doc Drift Detection: Compares docstrings vs. implementation
🏷️ Domain Clustering: k-means on embeddings for business domains
📋 Day-One Answers: Auto-generated FDE onboarding brief
🚧 Phase 4: Archivist (Living Context) - Coming Soon
📄 CODEBASE.md: Auto-updating context file for AI agents
📑 Onboarding Brief: Structured answers to 5 FDE questions
🔍 Vector Search: Semantic index of all modules
📊 Trace Logs: Audit trail of all analysis actions
🏗️ Architecture

Data Lineage Flow (jaffle_shop)

(Diagrams can be added with Mermaid if needed)

🚀 Getting Started
Prerequisites
# Python 3.9 or higher
python --version

# uv package manager (recommended)
pip install uv
Installation
# Clone the repository
git clone https://github.com/Addisu-Taye/brownfield-cartographer.git
cd brownfield-cartographer

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
Quick Start
# Clone a target repository
git clone https://github.com/dbt-labs/jaffle_shop.git

# Run analysis on jaffle_shop
uv run python src/cli.py analyze jaffle_shop

# Check status of analysis
uv run python src/cli.py status jaffle_shop

# View generated artifacts
ls jaffle_shop/.cartography/
📖 Usage Guide
Command Reference
Command	Description	Example
analyze	Run full analysis pipeline	uv run python src/cli.py analyze jaffle_shop
analyze --phase 1	Run only Surveyor (static analysis)	uv run python src/cli.py analyze jaffle_shop --phase 1
analyze --phase 2	Run only Hydrologist (lineage)	uv run python src/cli.py analyze jaffle_shop --phase 2
status	Show analysis status	uv run python src/cli.py status jaffle_shop
lineage	Trace dataset lineage	uv run python src/cli.py lineage jaffle_shop customers
blast	Calculate blast radius	uv run python src/cli.py blast jaffle_shop stg_orders
sources	List source datasets	uv run python src/cli.py sources jaffle_shop
sinks	List sink datasets	uv run python src/cli.py sinks jaffle_shop
graph	Show lineage visualization	uv run python src/cli.py graph jaffle_shop
Example Workflow
# 1. Analyze the codebase
uv run python src/cli.py analyze jaffle_shop

# 2. Check what was found
uv run python src/cli.py status jaffle_shop

# 3. List all source datasets
uv run python src/cli.py sources jaffle_shop
# Output:
# 📤 Source Datasets (Ingestion Points):
#   └─ raw_customers
#   └─ raw_orders
#   └─ raw_payments

# 4. Trace lineage for customers table
uv run python src/cli.py lineage jaffle_shop customers

# 5. Calculate impact if stg_orders changes
uv run python src/cli.py blast jaffle_shop stg_orders
📊 Current Results

jaffle_shop Analysis (as of March 12, 2026)

📁 Repository: dbt-labs/jaffle_shop
📊 Files Analyzed: 15
  ├─ SQL: 5
  └─ YAML: 2

💧 Lineage Results:
  ├─ Datasets Found: 6
  ├─ Transformations: 10
  └─ Lineage Edges: 9

📤 Source Datasets:
  ├─ raw_customers
  ├─ raw_orders
  └─ raw_payments

🔄 Transformations:
  ├─ sql:models/staging/stg_customers.sql
  ├─ sql:models/staging/stg_orders.sql
  └─ sql:models/staging/stg_payments.sql
🛠️ Project Structure
brownfield-cartographer/
├── .cartography/                 # Generated artifacts (gitignored)
│   ├── module_graph.json
│   └── lineage_graph.json
├── src/
│   ├── agents/
│   │   ├── surveyor.py           # Phase 1 - Static analysis
│   │   └── hydrologist.py        # Phase 2 - Data lineage
│   ├── analyzers/
│   │   └── tree_sitter_analyzer.py # AST parsing
│   ├── models/
│   │   ├── __init__.py
│   │   └── nodes.py              # Pydantic schemas
│   ├── graph/
│   │   └── knowledge_graph.py    # NetworkX wrapper
│   ├── cli.py                     # Click CLI
│   └── orchestrator.py            # Agent coordinator
├── tests/                          # Unit tests
├── pyproject.toml                  # Dependencies (uv)
├── README.md                       # This file
└── interim_report.md               # Interim submission
📦 Dependencies
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
    "pyyaml>=6.0",
]
📈 Roadmap

Interim (March 12) - ✅ Completed

Phase 1: Surveyor - Complete static analysis

Phase 2: Hydrologist - Core lineage (source detection)

CLI with analyze, status, lineage commands

Pydantic models for knowledge graph

Final (March 15) - 🚧 In Progress

Phase 2: Complete lineage (intermediate + sink tables)

Phase 3: Semanticist with LLM integration

Phase 4: Archivist with CODEBASE.md generation

Incremental update mode (git diff)

6-minute demo video

Full onboarding brief with Day-One answers

🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Fork the repository

Create your feature branch (git checkout -b feature/amazing-feature)

Commit your changes (git commit -m 'feat: Add amazing feature')

Push to the branch (git push origin feature/amazing-feature)

Open a Pull Request

Commit Convention

feat: Add new feature

fix: Bug fix

docs: Documentation update

style: Code style changes

refactor: Code refactoring

test: Test updates

chore: Maintenance

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

👥 Team

Addisu-Taye - Lead Developer - GitHub

🙏 Acknowledgments

TRP 1 Program for the challenging and engaging curriculum

dbt Labs for the excellent jaffle_shop example

The tree-sitter and sqlglot communities for amazing tooling

<div align="center"> ⭐ Star us on GitHub — it helps! Report Bug • Request Feature

Built with ❤️ for Forward Deployed Engineers everywhere

</div> ```

If you want, I can also make the Mermaid architecture diagrams Markdown-ready inside this same block so you can paste the full report on GitHub with diagrams rendered inline.

Do you want me to do that next?

please all contents inside one block and also add the mermaid in marmaid syntax

Absolutely! I’ve converted your entire document into a single Markdown block, added Mermaid diagrams for architecture and data lineage flows, and kept everything ready for GitHub. You can copy-paste it directly.

# 🗺️ Brownfield Cartographer

Codebase Intelligence Systems for Rapid FDE Onboarding in Production Environments

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

A multi-agent system that ingests any GitHub repository and produces a living, queryable knowledge graph of the system's architecture, data flows, and semantic structure.

---

## 📋 Overview

The Brownfield Cartographer solves the "Day-One Problem" faced by Forward Deployed Engineers (FDEs): understanding an unfamiliar production codebase within 72 hours. It builds instruments that make codebases legible by extracting structure, data lineage, and semantics from mixed-language data engineering repositories.

```bash
# One command to understand any codebase
uv run python src/cli.py analyze your-repo
🎯 The Problem
Challenge	Description	Our Solution
Navigation Blindness	You can grep for function names but cannot see the system	Module import graph with PageRank to identify critical paths
Contextual Amnesia	Every LLM session starts from zero	Living context (CODEBASE.md) for architectural awareness
Dependency Opacity	Cannot answer "What produces this dataset?"	Data lineage graph with blast radius analysis
Silent Debt	Documentation drifts from reality	Dead code detection and doc drift flags
✨ Features
✅ Phase 1: Surveyor (Static Structure Analysis) - Complete
📊 Module Graph: Maps imports, functions, classes across 50+ languages
📈 Change Velocity: Git log analysis for 30d/90d/total commit frequency
🎯 Critical Path: PageRank identifies architectural hubs
💀 Dead Code: Detects unused modules with multi-signal analysis
✅ Phase 2: Hydrologist (Data Lineage) - Core Complete
💧 SQL Parsing: sqlglot with 20+ dialect support (Postgres, BigQuery, Snowflake)
🔄 dbt Support: Handles {{ ref() }} and {{ source() }} Jinja syntax
📊 CTE Extraction: Distinguishes temporary tables from physical tables
🔗 Lineage Graph: NetworkX DiGraph with CONSUMES/PRODUCES relationships
📤 Source Detection: Identifies ingestion points (raw_customers, raw_orders)
🚧 Phase 3: Semanticist (LLM Analysis) - Coming Soon
🤖 Purpose Statements: LLM-generated module summaries
📝 Doc Drift Detection: Compares docstrings vs. implementation
🏷️ Domain Clustering: k-means on embeddings for business domains
📋 Day-One Answers: Auto-generated FDE onboarding brief
🚧 Phase 4: Archivist (Living Context) - Coming Soon
📄 CODEBASE.md: Auto-updating context file for AI agents
📑 Onboarding Brief: Structured answers to 5 FDE questions
🔍 Vector Search: Semantic index of all modules
📊 Trace Logs: Audit trail of all analysis actions
🏗️ Architecture
Data Lineage Flow (jaffle_shop)
System Architecture
Diagram is not supported.
🚀 Getting Started
Prerequisites
# Python 3.9 or higher
python --version

# uv package manager (recommended)
pip install uv
Installation
# Clone the repository
git clone https://github.com/Addisu-Taye/brownfield-cartographer.git
cd brownfield-cartographer

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
Quick Start
# Clone a target repository
git clone https://github.com/dbt-labs/jaffle_shop.git

# Run analysis on jaffle_shop
uv run python src/cli.py analyze jaffle_shop

# Check status of analysis
uv run python src/cli.py status jaffle_shop

# View generated artifacts
ls jaffle_shop/.cartography/
📖 Usage Guide
Command Reference
Command	Description	Example
analyze	Run full analysis pipeline	uv run python src/cli.py analyze jaffle_shop
analyze --phase 1	Run only Surveyor (static analysis)	uv run python src/cli.py analyze jaffle_shop --phase 1
analyze --phase 2	Run only Hydrologist (lineage)	uv run python src/cli.py analyze jaffle_shop --phase 2
status	Show analysis status	uv run python src/cli.py status jaffle_shop
lineage	Trace dataset lineage	uv run python src/cli.py lineage jaffle_shop customers
blast	Calculate blast radius	uv run python src/cli.py blast jaffle_shop stg_orders
sources	List source datasets	uv run python src/cli.py sources jaffle_shop
sinks	List sink datasets	uv run python src/cli.py sinks jaffle_shop
graph	Show lineage visualization	uv run python src/cli.py graph jaffle_shop
Example Workflow
# 1. Analyze the codebase
uv run python src/cli.py analyze jaffle_shop

# 2. Check what was found
uv run python src/cli.py status jaffle_shop

# 3. List all source datasets
uv run python src/cli.py sources jaffle_shop
# Output:
# 📤 Source Datasets (Ingestion Points):
#   └─ raw_customers
#   └─ raw_orders
#   └─ raw_payments

# 4. Trace lineage for customers table
uv run python src/cli.py lineage jaffle_shop customers

# 5. Calculate impact if stg_orders changes
uv run python src/cli.py blast jaffle_shop stg_orders
📊 Current Results

jaffle_shop Analysis (as of March 12, 2026)

📁 Repository: dbt-labs/jaffle_shop
📊 Files Analyzed: 15
  ├─ SQL: 5
  └─ YAML: 2

💧 Lineage Results:
  ├─ Datasets Found: 6
  ├─ Transformations: 10
  └─ Lineage Edges: 9

📤 Source Datasets:
  ├─ raw_customers
  ├─ raw_orders
  └─ raw_payments

🔄 Transformations:
  ├─ sql:models/staging/stg_customers.sql
  ├─ sql:models/staging/stg_orders.sql
  └─ sql:models/staging/stg_payments.sql
🛠️ Project Structure
brownfield-cartographer/
├── .cartography/                 # Generated artifacts (gitignored)
│   ├── module_graph.json
│   └── lineage_graph.json
├── src/
│   ├── agents/
│   │   ├── surveyor.py           # Phase 1 - Static analysis
│   │   └── hydrologist.py        # Phase 2 - Data lineage
│   ├── analyzers/
│   │   └── tree_sitter_analyzer.py # AST parsing
│   ├── models/
│   │   ├── __init__.py
│   │   └── nodes.py              # Pydantic schemas
│   ├── graph/
│   │   └── knowledge_graph.py    # NetworkX wrapper
│   ├── cli.py                     # Click CLI
│   └── orchestrator.py            # Agent coordinator
├── tests/                          # Unit tests
├── pyproject.toml                  # Dependencies (uv)
├── README.md                       # This file
└── interim_report.md               # Interim submission
📦 Dependencies
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
    "pyyaml>=6.0",
]
📈 Roadmap

Interim (March 12) - ✅ Completed

Phase 1: Surveyor - Complete static analysis

Phase 2: Hydrologist - Core lineage (source detection)

CLI with analyze, status, lineage commands

Pydantic models for knowledge graph

Final (March 15) - 🚧 In Progress

Phase 2: Complete lineage (intermediate + sink tables)

Phase 3: Semanticist with LLM integration

Phase 4: Archivist with CODEBASE.md generation

Incremental update mode (git diff)

6-minute demo video

Full onboarding brief with Day-One answers

🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Fork the repository

Create your feature branch (git checkout -b feature/amazing-feature)

Commit your changes (git commit -m 'feat: Add amazing feature')

Push to the branch (git push origin feature/amazing-feature)

Open a Pull Request

Commit Convention

feat: Add new feature

fix: Bug fix

docs: Documentation update

style: Code style changes

refactor: Code refactoring

test: Test updates

chore: Maintenance

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

👥 Team

Addisu-Taye - Lead Developer - GitHub

🙏 Acknowledgments

TRP 1 Program for the challenging and engaging curriculum

dbt Labs for the excellent jaffle_shop example

The tree-sitter and sqlglot communities for amazing tooling

<div align="center"> ⭐ Star us on GitHub — it helps! Report Bug • Request Feature

Built with ❤️ for Forward Deployed Engineers everywhere

</div> ```