"""Test Archivist agent with existing data."""

import json
from pathlib import Path
from src.agents.archivist import Archivist

print("="*60)
print("🧪 Testing Archivist Agent")
print("="*60)

# Initialize
arch = Archivist("jaffle_shop")

# Load existing data if available
surveyor_data = {}
lineage_data = {}
semantic_data = {}

# Check for module graph
module_path = Path("jaffle_shop/.cartography/module_graph.json")
if module_path.exists():
    with open(module_path, 'r', encoding='utf-8') as f:
        surveyor_data = json.load(f)
    print(f"✅ Loaded module graph: {len(surveyor_data.get('nodes', {}))} nodes")
    print(f"   Stats: {surveyor_data.get('metadata', {}).get('stats', {})}")
else:
    print("⚠️ No module graph found. Using mock data.")
    surveyor_data = {
        "nodes": {
            "models/customers.sql": {
                "language": "sql",
                "change_velocity_30d": 2,
                "is_dead_code_candidate": False
            },
            "models/orders.sql": {
                "language": "sql",
                "change_velocity_30d": 3,
                "is_dead_code_candidate": False
            },
            "models/staging/stg_customers.sql": {
                "language": "sql",
                "change_velocity_30d": 0,
                "is_dead_code_candidate": False
            },
            "models/staging/stg_orders.sql": {
                "language": "sql",
                "change_velocity_30d": 0,
                "is_dead_code_candidate": False
            },
            "models/staging/stg_payments.sql": {
                "language": "sql",
                "change_velocity_30d": 0,
                "is_dead_code_candidate": False
            }
        },
        "metadata": {
            "velocity_summary": {
                "total_changes_30d": 5,
                "files_with_changes": 2,
                "stale_files": 3
            },
            "stats": {
                "circular_dependencies": 0,
                "dead_code_candidates": 0
            }
        },
        "graph": {
            "nodes": [],
            "links": []
        }
    }
    print("   Using mock data with 5 modules")

# Check for lineage graph
lineage_path = Path("jaffle_shop/.cartography/lineage_graph.json")
if lineage_path.exists():
    with open(lineage_path, 'r', encoding='utf-8') as f:
        lineage_data = json.load(f)
    print(f"✅ Loaded lineage graph: {len(lineage_data.get('datasets', {}))} datasets")
    print(f"   Sources: {lineage_data.get('sources', [])}")
    print(f"   Sinks: {lineage_data.get('sinks', [])}")
else:
    print("⚠️ No lineage graph found. Using mock data.")
    lineage_data = {
        "sources": ["raw_customers", "raw_orders", "raw_payments"],
        "sinks": ["customers", "orders"],
        "datasets": {
            "raw_customers": {
                "name": "raw_customers",
                "type": "source",
                "files": ["models/staging/stg_customers.sql"]
            },
            "raw_orders": {
                "name": "raw_orders",
                "type": "source",
                "files": ["models/staging/stg_orders.sql"]
            },
            "raw_payments": {
                "name": "raw_payments",
                "type": "source",
                "files": ["models/staging/stg_payments.sql"]
            },
            "stg_customers": {
                "name": "stg_customers",
                "type": "table",
                "files": ["models/staging/stg_customers.sql"]
            },
            "stg_orders": {
                "name": "stg_orders",
                "type": "table",
                "files": ["models/staging/stg_orders.sql"]
            },
            "stg_payments": {
                "name": "stg_payments",
                "type": "table",
                "files": ["models/staging/stg_payments.sql"]
            },
            "customers": {
                "name": "customers",
                "type": "table",
                "files": ["models/customers.sql"]
            },
            "orders": {
                "name": "orders",
                "type": "table",
                "files": ["models/orders.sql"]
            }
        },
        "transformations": {
            "sql:models/staging/stg_customers.sql": {
                "reads": ["raw_customers"],
                "writes": ["stg_customers"],
                "file": "models/staging/stg_customers.sql"
            },
            "sql:models/staging/stg_orders.sql": {
                "reads": ["raw_orders"],
                "writes": ["stg_orders"],
                "file": "models/staging/stg_orders.sql"
            },
            "sql:models/staging/stg_payments.sql": {
                "reads": ["raw_payments"],
                "writes": ["stg_payments"],
                "file": "models/staging/stg_payments.sql"
            },
            "sql:models/customers.sql": {
                "reads": ["stg_customers", "stg_orders", "stg_payments"],
                "writes": ["customers"],
                "file": "models/customers.sql"
            },
            "sql:models/orders.sql": {
                "reads": ["stg_orders", "stg_payments"],
                "writes": ["orders"],
                "file": "models/orders.sql"
            }
        }
    }
    print("   Using mock data with 8 datasets and 5 transformations")

# Check for semantic index
semantic_path = Path("jaffle_shop/.cartography/semantic_index.json")
if semantic_path.exists():
    with open(semantic_path, 'r', encoding='utf-8') as f:
        semantic_data = json.load(f)
    print(f"✅ Loaded semantic index: {len(semantic_data.get('purpose_statements', {}))} statements")
    print(f"   Domains: {set(semantic_data.get('domain_clusters', {}).values())}")
else:
    print("⚠️ No semantic index found. Using mock data.")
    semantic_data = {
        "purpose_statements": {
            "models/customers.sql": "Customer lifetime value calculation and customer segmentation",
            "models/orders.sql": "Order processing and payment method attribution",
            "models/staging/stg_customers.sql": "Raw customer data cleaning and type casting",
            "models/staging/stg_orders.sql": "Raw order data cleaning and status normalization",
            "models/staging/stg_payments.sql": "Raw payment data cleaning and amount validation",
        },
        "doc_drift_flags": {
            "models/customers.sql": False,
            "models/orders.sql": True,
        },
        "domain_clusters": {
            "models/customers.sql": "Customer Analytics",
            "models/orders.sql": "Order Processing",
            "models/staging/stg_customers.sql": "Data Ingestion",
            "models/staging/stg_orders.sql": "Data Ingestion",
            "models/staging/stg_payments.sql": "Data Ingestion",
        }
    }
    print("   Using mock data with 5 purpose statements")

# Test logging
print("\n📋 Testing trace logging...")
arch.log_trace("test_start", "user", {"action": "Testing Archivist"})
arch.log_trace("data_loaded", "archivist", {
    "surveyor": bool(surveyor_data),
    "lineage": bool(lineage_data),
    "semantic": bool(semantic_data)
})
print(f"  ✅ Logged {len(arch.trace_log)} traces")

# Test CODEBASE.md generation
print("\n📄 Testing CODEBASE.md generation...")
codebase_content = arch.generate_codebase_md(surveyor_data, lineage_data, semantic_data)
print(f"  ✅ Generated {len(codebase_content.split(chr(10)))} lines")
print("\n  Preview (first 10 lines):")
print("-" * 40)
for line in codebase_content.split('\n')[:10]:
    print(f"  {line}")
print("  ...")

# Test onboarding brief generation
print("\n📋 Testing onboarding brief generation...")
brief_content = arch.generate_onboarding_brief(surveyor_data, lineage_data, semantic_data)
print(f"  ✅ Generated {len(brief_content.split(chr(10)))} lines")
print("\n  Preview (first 10 lines):")
print("-" * 40)
for line in brief_content.split('\n')[:10]:
    print(f"  {line}")
print("  ...")

# Save all artifacts
print("\n💾 Saving all artifacts...")
arch.save_artifacts(surveyor_data, lineage_data, semantic_data)

# Check generated files
artifacts = ["CODEBASE.md", "onboarding_brief.md", "cartography_trace.jsonl"]
print("\n📁 Generated Artifacts:")
print("-" * 40)
for artifact in artifacts:
    path = Path("jaffle_shop/.cartography") / artifact
    if path.exists():
        size = path.stat().st_size
        print(f"  ✅ {artifact:25} {size:8} bytes")
        
        # Show preview of each artifact with UTF-8 encoding
        if artifact in ["CODEBASE.md", "onboarding_brief.md"]:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            preview = content[:100].replace('\n', ' ')
            print(f"     Preview: {preview}...")
    else:
        print(f"  ❌ {artifact:25} not found")

# Final stats
print("\n📊 Archivist Stats:")
print(f"  Artifacts generated: {arch.stats['artifacts_generated']}")
print(f"  Traces logged: {arch.stats['traces_logged']}")

print("\n" + "="*60)
print("✅ Archivist test complete!")
print("="*60)

# Optional: Show full trace log
print("\n📋 Trace Log Preview:")
print("-" * 40)
for trace in arch.trace_log[-3:]:  # Show last 3 traces
    print(f"  {trace['timestamp'][:19]} - {trace['agent']}: {trace['action']}")