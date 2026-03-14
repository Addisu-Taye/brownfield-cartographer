"""Test full pipeline with all agents."""

import json
import time
from pathlib import Path
from src.orchestrator import Orchestrator

print("="*60)
print("🚀 Testing Full Pipeline (All 4 Agents)")
print("="*60)

# Initialize
repo_path = "jaffle_shop"
orch = Orchestrator(repo_path)

# Clean start - remove old cache
cache_dir = Path(repo_path) / ".cartography"
if cache_dir.exists():
    import shutil
    shutil.rmtree(cache_dir)
    print(f"🧹 Cleaned cache directory: {cache_dir}")
cache_dir.mkdir(parents=True, exist_ok=True)

start_time = time.time()

# Run all phases
print("\n📊 Running all phases sequentially...")
results = orch.run_full_analysis()

elapsed = time.time() - start_time
print(f"\n⏱️  Total execution time: {elapsed:.2f} seconds")

# Print summary
print("\n📊 Results Summary:")
print("-" * 40)
for phase, success in results.items():
    status = "✅" if success else "❌"
    print(f"  {status} {phase}: {success}")

# Get final status
status = orch.get_status()

# Check artifacts
print("\n📁 Generated Artifacts:")
print("-" * 40)
artifacts = [
    "module_graph.json",
    "lineage_graph.json", 
    "semantic_index.json",
    "CODEBASE.md",
    "onboarding_brief.md",
    "cartography_trace.jsonl",
    "dead_code_candidates.md"
]

artifact_stats = {}
for artifact in artifacts:
    path = cache_dir / artifact
    if path.exists():
        size = path.stat().st_size
        artifact_stats[artifact] = size
        print(f"  ✅ {artifact:25} {size:8} bytes")
    else:
        print(f"  ❌ {artifact:25} not found")

# Validate artifact contents
print("\n🔍 Validating Artifact Contents:")
print("-" * 40)

# Check module graph
if (cache_dir / "module_graph.json").exists():
    with open(cache_dir / "module_graph.json") as f:
        module_data = json.load(f)
    nodes = module_data.get('nodes', {})
    print(f"  📊 Module Graph: {len(nodes)} nodes")
    print(f"     Python files: {sum(1 for n in nodes.values() if n.get('language') == 'python')}")
    print(f"     SQL files: {sum(1 for n in nodes.values() if n.get('language') == 'sql')}")

# Check lineage graph
if (cache_dir / "lineage_graph.json").exists():
    with open(cache_dir / "lineage_graph.json") as f:
        lineage_data = json.load(f)
    datasets = lineage_data.get('datasets', {})
    print(f"\n  🔄 Lineage Graph: {len(datasets)} datasets")
    print(f"     Sources: {lineage_data.get('sources', [])}")
    print(f"     Sinks: {lineage_data.get('sinks', [])}")

# Check semantic index
if (cache_dir / "semantic_index.json").exists():
    with open(cache_dir / "semantic_index.json") as f:
        semantic_data = json.load(f)
    purposes = semantic_data.get('purpose_statements', {})
    domains = semantic_data.get('domain_clusters', {})
    print(f"\n  🧠 Semantic Index: {len(purposes)} purpose statements")
    print(f"     Domains: {len(set(domains.values()))} unique domains")
    if purposes:
        sample = list(purposes.items())[0]
        print(f"     Sample: {sample[0]} -> {sample[1][:50]}...")

# Check CODEBASE.md
if (cache_dir / "CODEBASE.md").exists():
    with open(cache_dir / "CODEBASE.md", 'r', encoding='utf-8') as f:
        codebase = f.read()
    lines = len(codebase.split('\n'))
    print(f"\n  📄 CODEBASE.md: {lines} lines")
    # Check for key sections
    sections = ["Architecture Overview", "Data Lineage", "Semantic Understanding", 
                "Documentation Health", "Change Velocity", "Known Technical Debt"]
    found = [s for s in sections if s in codebase]
    print(f"     Sections found: {len(found)}/{len(sections)}")

# Check onboarding brief
if (cache_dir / "onboarding_brief.md").exists():
    with open(cache_dir / "onboarding_brief.md", 'r', encoding='utf-8') as f:
        brief = f.read()
    lines = len(brief.split('\n'))
    print(f"\n  📋 Onboarding Brief: {lines} lines")
    # Check for Day-One questions
    questions = ["Primary Data Ingestion", "Critical Output Datasets", 
                 "Blast Radius", "Business Logic", "Change Velocity"]
    found = [q for q in questions if q in brief]
    print(f"     Questions answered: {len(found)}/{len(questions)}")

# Check trace log
if (cache_dir / "cartography_trace.jsonl").exists():
    with open(cache_dir / "cartography_trace.jsonl") as f:
        traces = [json.loads(line) for line in f]
    print(f"\n  📝 Trace Log: {len(traces)} entries")
    agents = set(t.get('agent', 'unknown') for t in traces)
    print(f"     Agents: {', '.join(agents)}")

# Phase completion
print("\n📊 Phases Completed:")
print("-" * 40)
for phase in status.get('phases_completed', []):
    print(f"  ✅ {phase}")

# LLM Cost (if any)
if 'semanticist' in status and status['semanticist'].get('cost', 0) > 0:
    print(f"\n💰 LLM Cost: ${status['semanticist']['cost']:.4f}")

# Summary
print("\n" + "="*60)
print("✅ FULL PIPELINE TEST COMPLETE")
print("="*60)

# Success criteria
success_criteria = {
    "module_graph": (cache_dir / "module_graph.json").exists(),
    "lineage_graph": (cache_dir / "lineage_graph.json").exists(),
    "semantic_index": (cache_dir / "semantic_index.json").exists(),
    "codebase_md": (cache_dir / "CODEBASE.md").exists(),
    "onboarding_brief": (cache_dir / "onboarding_brief.md").exists(),
    "trace_log": (cache_dir / "cartography_trace.jsonl").exists(),
    "all_phases": len(status.get('phases_completed', [])) == 4
}

print("\n📋 Final Verification:")
print("-" * 40)
for criterion, met in success_criteria.items():
    status_icon = "✅" if met else "❌"
    print(f"  {status_icon} {criterion.replace('_', ' ').title()}")

if all(success_criteria.values()):
    print("\n🎉 ALL SYSTEMS GO! Full pipeline is working perfectly!")
else:
    print("\n⚠️ Some components need attention. Check above.")

print("="*60)