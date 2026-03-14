#!/usr/bin/env python
"""Brownfield Cartographer - CLI Interface

A multi-agent system that ingests any GitHub repository and produces
a living, queryable knowledge graph of the system's architecture,
data flows, and semantic structure.
"""

import click
from pathlib import Path
import sys
import time
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import Orchestrator
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from project root
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"📄 Loaded environment from {env_path}")

@click.group()
def cli():
    """Brownfield Cartographer - Codebase Intelligence System
    
    A multi-agent system that ingests any GitHub repository and produces
    a living, queryable knowledge graph of the system's architecture,
    data flows, and semantic structure.
    """
    pass


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--phase', '-p', default='all', 
              type=click.Choice(['1', '2', '3', '4', 'all'], case_sensitive=False),
              help='Phase to run: 1 (Surveyor), 2 (Hydrologist), 3 (Semanticist), 4 (Archivist), or all')
@click.option('--output', '-o', default=None, help='Output directory for cartography artifacts')
@click.option('--no-git', is_flag=True, help='Skip git analysis')
@click.option('--api-key', envvar='OPENAI_API_KEY', help='OpenAI API key (or set OPENAI_API_KEY env var)')
def analyze(repo_path, phase, output, no_git, api_key):
    """Analyze a codebase and generate cartography artifacts.
    
    REPO_PATH: Path to the local git repository to analyze
    
    Examples:
        analyze jaffle_shop
        analyze ../airflow --phase 2
        analyze ./my-repo --output ./custom-output
    """
    start_time = time.time()
    
    repo_path = Path(repo_path).resolve()
    click.echo(f"🔍 Analyzing codebase: {repo_path}")
    
    # Set up output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = repo_path / ".cartography"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize orchestrator
    orchestrator = Orchestrator(str(repo_path), output_dir)
    
    # Run requested phases
    if phase == '1':
        click.echo("\n📐 Phase 1: Surveyor Agent (Static Structure Analysis)")
        orchestrator.run_phase1()
    
    elif phase == '2':
        click.echo("\n💧 Phase 2: Hydrologist Agent (Data Lineage Analysis)")
        orchestrator.run_phase2()
        
        # Show lineage summary
        status = orchestrator.get_status()
        hydrologist = status.get('hydrologist', {})
        
        click.echo("\n📊 Lineage Summary:")
        click.echo(f"  📤 Sources: {len(hydrologist.get('sources', []))}")
        for source in hydrologist.get('sources', [])[:5]:
            click.echo(f"     └─ {source}")
        click.echo(f"  📥 Sinks: {len(hydrologist.get('sinks', []))}")
        for sink in hydrologist.get('sinks', [])[:5]:
            click.echo(f"     └─ {sink}")
    
    elif phase == '3':
        click.echo("\n🤖 Phase 3: Semanticist Agent (LLM-Powered Analysis)")
        if not api_key:
            click.echo("⚠️  No API key found. Set OPENAI_API_KEY environment variable or --api-key option.")
        orchestrator.run_phase3()
        
        # Show semantic summary
        status = orchestrator.get_status()
        semantic = status.get('semanticist', {})
        
        click.echo("\n🧠 Semantic Summary:")
        click.echo(f"  Purpose statements: {semantic.get('purpose_statements', 0)}")
        click.echo(f"  Doc drift detected: {semantic.get('doc_drift_count', 0)}")
        click.echo(f"  Domains identified: {semantic.get('domains', 0)}")
        click.echo(f"  Total cost: ${semantic.get('cost', 0):.4f}")
    
    elif phase == '4':
        click.echo("\n📚 Phase 4: Archivist Agent (Living Context Maintenance)")
        orchestrator.run_phase4()
        
        # Show artifacts
        status = orchestrator.get_status()
        artifacts = status.get('artifacts', {})
        
        click.echo("\n📄 Generated Artifacts:")
        for artifact, exists in artifacts.items():
            if exists:
                click.echo(f"  ✅ {artifact}")
    
    else:
        click.echo("\n🚀 Running full analysis pipeline (Phases 1-4)...")
        orchestrator.run_full_analysis()
        
        # Show final status
        status = orchestrator.get_status()
        
        click.echo("\n📊 Final Status:")
        click.echo(f"  Phases completed: {', '.join(status.get('phases_completed', []))}")
        
        if 'semanticist' in status:
            click.echo(f"  LLM cost: ${status['semanticist'].get('cost', 0):.4f}")
        
        artifacts = [f for f, exists in status.get('artifacts', {}).items() if exists]
        click.echo(f"  Artifacts generated: {len(artifacts)}")
    
    elapsed = time.time() - start_time
    click.echo(f"\n✅ Analysis complete in {elapsed:.2f} seconds")
    click.echo(f"📁 Artifacts saved to: {output_dir}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def status(repo_path):
    """Show analysis status for a codebase."""
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    status = orchestrator.get_status()
    
    click.echo(f"\n📊 Cartography Status: {repo_path}")
    click.echo("-" * 60)
    
    # Phases completed
    phases = status.get('phases_completed', [])
    all_phases = ['phase1', 'phase2', 'phase3', 'phase4']
    for phase in all_phases:
        if phase in phases:
            click.echo(f"✅ {phase.upper():10} Completed")
        else:
            click.echo(f"⏳ {phase.upper():10} Pending")
    
    # Artifacts
    click.echo("\n📁 Artifacts:")
    artifacts = status.get('artifacts', {})
    for artifact, exists in artifacts.items():
        if exists:
            path = orchestrator.cache_dir / artifact
            size = path.stat().st_size
            modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            click.echo(f"  ✅ {artifact:25} {size:8} bytes  ({modified})")
        else:
            click.echo(f"  ⏳ {artifact:25} Not yet generated")
    
    # Statistics
    click.echo("\n📊 Statistics:")
    
    if 'surveyor' in status:
        s = status['surveyor']
        click.echo(f"  Surveyor: {s.get('nodes_count', 0)} modules, {s.get('stats', {}).get('edges_added', 0)} imports")
    
    if 'hydrologist' in status:
        h = status['hydrologist']
        click.echo(f"  Hydrologist: {h.get('datasets_count', 0)} datasets, {h.get('transformations_count', 0)} transformations")
        click.echo(f"    Sources: {', '.join(h.get('sources', [])[:3])}")
        click.echo(f"    Sinks: {', '.join(h.get('sinks', [])[:3])}")
    
    if 'semanticist' in status:
        sem = status['semanticist']
        click.echo(f"  Semanticist: {sem.get('purpose_statements', 0)} purpose statements")
        click.echo(f"    Doc drift: {sem.get('doc_drift_count', 0)} modules")
        click.echo(f"    Cost: ${sem.get('cost', 0):.4f}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def interactive(repo_path):
    """Start interactive query mode."""
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    orchestrator.interactive()


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('question')
def query(repo_path, question):
    """Ask a natural language question about the codebase.
    
    Examples:
        query jaffle_shop "find customer lifetime value calculation"
        query jaffle_shop "trace lineage of customers"
        query jaffle_shop "blast radius of stg_orders"
        query jaffle_shop "explain models/customers.sql"
    """
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    
    click.echo(f"🔍 Question: {question}")
    click.echo("-" * 60)
    
    result = orchestrator.query(question)
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('dataset_name')
def lineage(repo_path, dataset_name):
    """Trace lineage for a specific dataset.
    
    DATASET_NAME: Name of the dataset to trace (e.g., 'customers', 'raw_orders')
    """
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    
    result = orchestrator.query(f"trace lineage of {dataset_name}")
    
    if "error" in result.get("result", {}):
        click.echo(f"❌ {result['result']['error']}")
        return
    
    lineage_result = result.get("result", {})
    
    click.echo(f"\n📊 Lineage for: {dataset_name}")
    click.echo("-" * 60)
    
    click.echo("\n⬆️  Upstream sources (what feeds this):")
    upstream = [p for p in lineage_result.get("path", []) if p != dataset_name]
    if upstream:
        for source in upstream[:10]:
            click.echo(f"  └─ {source}")
    else:
        click.echo("  (none - this is a source dataset)")
    
    click.echo("\n⬇️  Downstream dependents (what uses this):")
    downstream = [p for p in lineage_result.get("path", []) if p != dataset_name]
    if downstream:
        for dep in downstream[:10]:
            click.echo(f"  └─ {dep}")
    else:
        click.echo("  (none - this is a sink dataset)")
    
    if lineage_result.get("files"):
        click.echo("\n📄 Transformations:")
        for f in lineage_result["files"][:5]:
            click.echo(f"  └─ {f.get('file')}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('module_path')
def blast(repo_path, module_path):
    """Calculate blast radius if a module changes.
    
    MODULE_PATH: Path to the module (e.g., 'models/customers.sql')
    """
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    
    result = orchestrator.query(f"blast radius of {module_path}")
    
    if "error" in result.get("result", {}):
        click.echo(f"❌ {result['result']['error']}")
        return
    
    blast_result = result.get("result", {})
    
    click.echo(f"\n💥 Blast Radius Analysis: {module_path}")
    click.echo("-" * 60)
    
    click.echo(f"\n📊 If '{module_path}' changes or fails:")
    click.echo(f"  • {blast_result.get('direct_dependents', 0)} direct dependents")
    click.echo(f"  • {len(blast_result.get('datasets_affected', []))} datasets affected")
    click.echo(f"  • Total impact: {blast_result.get('total_impact', 0)} items")
    
    if blast_result.get('dependents'):
        click.echo("\n📉 Affected modules:")
        for dep in blast_result['dependents'][:10]:
            click.echo(f"  └─ {dep}")
    
    if blast_result.get('datasets_affected'):
        click.echo("\n📉 Affected datasets:")
        for ds in blast_result['datasets_affected'][:10]:
            click.echo(f"  └─ {ds}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('concept')
def find(repo_path, concept):
    """Find implementation of a concept using semantic search.
    
    CONCEPT: What to search for (e.g., 'customer lifetime value')
    """
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    
    result = orchestrator.query(f"find {concept}")
    find_result = result.get("result", [])
    
    click.echo(f"\n🔍 Search results for: '{concept}'")
    click.echo("-" * 60)
    
    if not find_result:
        click.echo("No results found.")
        return
    
    for item in find_result[:10]:
        if "module" in item:
            click.echo(f"\n📄 {item['module']}")
            click.echo(f"   Purpose: {item.get('purpose', 'N/A')}")
            click.echo(f"   Confidence: {item.get('confidence', 0)}")
        elif "dataset" in item:
            click.echo(f"\n📊 Dataset: {item['dataset']}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('module_path')
def explain(repo_path, module_path):
    """Explain what a module does.
    
    MODULE_PATH: Path to the module (e.g., 'models/customers.sql')
    """
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    
    result = orchestrator.query(f"explain {module_path}")
    explanation = result.get("result", {})
    
    click.echo(f"\n📖 Module Explanation: {module_path}")
    click.echo("-" * 60)
    
    click.echo(f"\n🎯 Purpose:")
    click.echo(f"  {explanation.get('purpose', 'No purpose statement available')}")
    
    if explanation.get('domain'):
        click.echo(f"\n🏷️ Domain: {explanation['domain']}")
    
    if explanation.get('doc_drift'):
        click.echo(f"\n⚠️ Documentation drift detected!")
    
    if explanation.get('dependencies'):
        click.echo(f"\n📥 Dependencies ({len(explanation['dependencies'])}):")
        for dep in explanation['dependencies'][:10]:
            click.echo(f"  └─ {dep}")
    
    if explanation.get('dependents'):
        click.echo(f"\n📤 Dependents ({len(explanation['dependents'])}):")
        for dep in explanation['dependents'][:10]:
            click.echo(f"  └─ {dep}")
    
    if explanation.get('datasets'):
        click.echo(f"\n💾 Datasets: {', '.join(explanation['datasets'])}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def sources(repo_path):
    """List all source datasets (ingestion points)."""
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    status = orchestrator.get_status()
    
    sources = status.get('hydrologist', {}).get('sources', [])
    
    click.echo(f"\n📤 Source Datasets (Ingestion Points):")
    click.echo("-" * 60)
    
    if not sources:
        click.echo("No sources found. Run phase 2 analysis first.")
        return
    
    for source in sources:
        click.echo(f"  └─ {source}")
    
    click.echo(f"\nTotal sources: {len(sources)}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def sinks(repo_path):
    """List all sink datasets (final outputs)."""
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    status = orchestrator.get_status()
    
    sinks = status.get('hydrologist', {}).get('sinks', [])
    
    click.echo(f"\n📥 Sink Datasets (Final Outputs):")
    click.echo("-" * 60)
    
    if not sinks:
        click.echo("No sinks found. Run phase 2 analysis first.")
        return
    
    for sink in sinks:
        click.echo(f"  └─ {sink}")
    
    click.echo(f"\nTotal sinks: {len(sinks)}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def artifacts(repo_path):
    """List all generated artifacts."""
    repo_path = Path(repo_path).resolve()
    orchestrator = Orchestrator(str(repo_path))
    status = orchestrator.get_status()
    
    artifacts = status.get('artifacts', {})
    
    click.echo(f"\n📁 Generated Artifacts:")
    click.echo("-" * 60)
    
    found = False
    for artifact, exists in artifacts.items():
        if exists:
            path = orchestrator.cache_dir / artifact
            size = path.stat().st_size
            modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            click.echo(f"✅ {artifact:25} {size:8} bytes  ({modified})")
            found = True
    
    if not found:
        click.echo("No artifacts found. Run analysis first.")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def clean(repo_path):
    """Remove all generated artifacts."""
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    
    if not cartography_dir.exists():
        click.echo("No artifacts to clean.")
        return
    
    import shutil
    shutil.rmtree(cartography_dir)
    click.echo(f"🧹 Removed {cartography_dir}")


if __name__ == "__main__":
    cli()