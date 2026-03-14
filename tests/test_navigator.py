"""Test Navigator agent with existing data."""

import json
from pathlib import Path
from src.agents.navigator import Navigator

print("="*60)
print("🧪 Testing Navigator Agent")
print("="*60)

# Initialize
nav = Navigator("jaffle_shop")

# Check if graphs were loaded
print("\n📂 Checking loaded data:")
if nav.module_graph:
    print(f"  ✅ Module graph loaded: {len(nav.module_graph.nodes)} nodes")
else:
    print("  ⚠️ Module graph not loaded")

if nav.lineage_graph:
    print(f"  ✅ Lineage graph loaded: {len(nav.lineage_graph.nodes)} nodes")
    if hasattr(nav, 'datasets'):
        print(f"  📊 Datasets available: {len(nav.datasets)}")
else:
    print("  ⚠️ Lineage graph not loaded")

if nav.semantic_index:
    purposes = nav.semantic_index.get('purpose_statements', {})
    print(f"  ✅ Semantic index loaded: {len(purposes)} purpose statements")
else:
    print("  ⚠️ Semantic index not loaded")

# Test 1: find_implementation
print("\n🔍 Test 1: find_implementation")
print("-" * 40)

test_concepts = ["customer", "order", "payment", "lifetime value"]
for concept in test_concepts:
    print(f"\n  Searching for '{concept}':")
    results = nav.find_implementation(concept)
    if results:
        for r in results[:3]:
            if "module" in r:
                print(f"    📄 {r['module']}")
                print(f"       Purpose: {r.get('purpose', 'N/A')[:50]}...")
            elif "dataset" in r:
                print(f"    📊 Dataset: {r['dataset']}")
    else:
        print("    No results found")

# Test 2: trace_lineage
print("\n🔄 Test 2: trace_lineage")
print("-" * 40)

test_datasets = ["customers", "orders", "raw_customers", "stg_orders"]
for dataset in test_datasets:
    print(f"\n  Tracing lineage for '{dataset}':")
    
    # Upstream
    upstream = nav.trace_lineage(dataset, "upstream")
    if "error" in upstream:
        print(f"    ⚠️ {upstream['error']}")
    else:
        print(f"    ⬆️ Upstream: {upstream.get('path', [])}")
    
    # Downstream
    downstream = nav.trace_lineage(dataset, "downstream")
    if "error" not in downstream:
        print(f"    ⬇️ Downstream: {downstream.get('path', [])}")

# Test 3: blast_radius
print("\n💥 Test 3: blast_radius")
print("-" * 40)

test_modules = [
    "models/customers.sql",
    "models/orders.sql",
    "models/staging/stg_customers.sql"
]

for module in test_modules:
    print(f"\n  Calculating blast radius for '{module}':")
    result = nav.blast_radius(module)
    if "error" in result:
        print(f"    ⚠️ {result['error']}")
    else:
        print(f"    📊 Direct dependents: {result.get('direct_dependents', 0)}")
        print(f"    📉 Affected datasets: {len(result.get('datasets_affected', []))}")
        print(f"    📈 Total impact: {result.get('total_impact', 0)}")

# Test 4: explain_module
print("\n📖 Test 4: explain_module")
print("-" * 40)

for module in test_modules[:2]:  # Test first 2 modules
    print(f"\n  Explaining '{module}':")
    explanation = nav.explain_module(module)
    if "error" in explanation:
        print(f"    ⚠️ {explanation['error']}")
    else:
        print(f"    🎯 Purpose: {explanation.get('purpose', 'N/A')[:80]}...")
        if explanation.get('dependencies'):
            print(f"    📥 Dependencies: {explanation['dependencies'][:3]}")
        if explanation.get('datasets'):
            print(f"    💾 Datasets: {explanation['datasets']}")

# Test 5: natural language query
print("\n💬 Test 5: Natural Language Queries")
print("-" * 40)

test_queries = [
    "find customer logic",
    "trace lineage of customers",
    "blast radius of models/customers.sql",
    "explain models/orders.sql",
    "where is payment processing code"
]

for query in test_queries:
    print(f"\n  Query: '{query}'")
    result = nav.query(query)
    print(f"  Tool: {result.get('tool', 'unknown')}")
    if result.get('result'):
        if isinstance(result['result'], list):
            print(f"  Results: {len(result['result'])} items")
            if result['result']:
                print(f"  First result: {str(result['result'][0])[:80]}...")
        else:
            print(f"  Result: {str(result['result'])[:80]}...")

# Test 6: interactive mode simulation
print("\n🎮 Test 6: Interactive Mode Simulation")
print("-" * 40)

# Simulate a few interactive commands
commands = [
    "find customer",
    "lineage customers",
    "blast models/customers.sql",
    "explain models/orders.sql"
]

for cmd in commands:
    print(f"\n  > {cmd}")
    result = nav.query(cmd)
    print(f"  Response: {result.get('tool', 'unknown')}")

# Statistics
print("\n📊 Navigator Statistics:")
print(f"  Total queries executed: {nav.stats['queries_executed']}")
print(f"  Tools used: {nav.stats['tools_used']}")

print("\n" + "="*60)
print("✅ Navigator test complete!")
print("="*60)