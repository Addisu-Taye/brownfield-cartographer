#!/usr/bin/env python
import click
from pathlib import Path
import sys
import time
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.surveyor import Surveyor
from src.agents.hydrologist import Hydrologist
from src.orchestrator import Orchestrator


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
@click.option('--phase', '-p', default='all', help='Phase to run: 1, 2, or all')
@click.option('--output', '-o', default=None, help='Output directory for cartography artifacts')
@click.option('--no-git', is_flag=True, help='Skip git analysis')
def analyze(repo_path, phase, output, no_git):
    """Analyze a codebase and generate cartography artifacts.
    
    REPO_PATH: Path to the local git repository to analyze
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
    
    # Run requested phases
    if phase == '1':
        click.echo("\n📐 Phase 1: Surveyor Agent (Static Structure Analysis)")
        surveyor = Surveyor(str(repo_path), output_dir)
        surveyor.run()
        surveyor.save_graph(output_dir / "module_graph.json")
        if surveyor.nodes:
            surveyor.save_dead_code_report(output_dir / "dead_code_candidates.md")
    
    elif phase == '2':
        click.echo("\n💧 Phase 2: Hydrologist Agent (Data Lineage Analysis)")
        hydrologist = Hydrologist(str(repo_path), output_dir)
        hydrologist.run()
        hydrologist.save_lineage_graph(output_dir / "lineage_graph.json")
        
        # Print lineage summary
        sources = hydrologist.find_sources()
        sinks = hydrologist.find_sinks()
        
        click.echo("\n📊 Lineage Summary:")
        click.echo(f"  📤 Sources (ingestion points): {len(sources)}")
        for source in sources[:5]:  # Show first 5
            click.echo(f"     └─ {source}")
        click.echo(f"  📥 Sinks (output datasets): {len(sinks)}")
        for sink in sinks[:5]:
            click.echo(f"     └─ {sink}")
    
    else:
        click.echo("\n🚀 Running full analysis pipeline...")
        orchestrator = Orchestrator(str(repo_path), output_dir)
        orchestrator.run_full_analysis()
    
    elapsed = time.time() - start_time
    click.echo(f"\n✅ Analysis complete in {elapsed:.2f} seconds")
    click.echo(f"📁 Artifacts saved to: {output_dir}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def status(repo_path):
    """Show analysis status for a codebase."""
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    
    if not cartography_dir.exists():
        click.echo(f"❌ No cartography data found for {repo_path}")
        click.echo("   Run 'analyze' first to generate artifacts.")
        return
    
    click.echo(f"📊 Cartography Status: {repo_path}")
    click.echo("-" * 50)
    
    # Check for artifacts
    artifacts = {
        "module_graph.json": "Module Graph",
        "dead_code_candidates.md": "Dead Code Report",
        "lineage_graph.json": "Lineage Graph",
        "CODEBASE.md": "Living Context (Phase 3)",
        "onboarding_brief.md": "Onboarding Brief (Phase 3)"
    }
    
    for filename, description in artifacts.items():
        path = cartography_dir / filename
        if path.exists():
            size = path.stat().st_size
            modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            click.echo(f"✅ {description:30} {size:8} bytes  ({modified})")
        else:
            click.echo(f"⏳ {description:30} Not yet generated")
    
    # Try to load and show summary
    module_graph = cartography_dir / "module_graph.json"
    if module_graph.exists():
        try:
            with open(module_graph) as f:
                data = json.load(f)
            
            click.echo("\n📈 Module Summary:")
            metadata = data.get("metadata", {})
            stats = metadata.get("stats", {})
            
            if stats.get("python_files", 0) > 0:
                click.echo(f"  Python modules: {stats['python_files']}")
                click.echo(f"  Import relationships: {stats.get('edges_added', 0)}")
                click.echo(f"  Dead code candidates: {stats.get('dead_code_candidates', 0)}")
        except:
            pass
    
    # Show lineage summary if available
    lineage_graph = cartography_dir / "lineage_graph.json"
    if lineage_graph.exists():
        try:
            with open(lineage_graph) as f:
                data = json.load(f)
            
            click.echo("\n📊 Lineage Summary:")
            stats = data.get("metadata", {}).get("stats", {})
            click.echo(f"  Datasets found: {stats.get('datasets_found', 0)}")
            click.echo(f"  Transformations: {stats.get('transformations_found', 0)}")
            click.echo(f"  Lineage edges: {stats.get('edges_added', 0)}")
        except:
            pass


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('dataset_name')
def lineage(repo_path, dataset_name):
    """Trace lineage for a specific dataset.
    
    DATASET_NAME: Name of the dataset to trace (e.g., 'customers', 'raw_orders')
    """
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    lineage_file = cartography_dir / "lineage_graph.json"
    
    if not lineage_file.exists():
        click.echo("❌ No lineage graph found. Run 'analyze --phase 2' first.")
        return
    
    try:
        with open(lineage_file) as f:
            data = json.load(f)
        
        # Load graph
        import networkx as nx
        from networkx.readwrite import json_graph
        graph = json_graph.node_link_graph(data["graph"])
        
        # Find dataset node
        dataset_node = f"dataset:{dataset_name}"
        if dataset_node not in graph:
            click.echo(f"❌ Dataset '{dataset_name}' not found in lineage graph.")
            return
        
        # Find upstream (what feeds into it)
        upstream = []
        for node in nx.ancestors(graph, dataset_node):
            if node.startswith("dataset:"):
                upstream.append(node.replace("dataset:", ""))
        
        # Find downstream (what depends on it)
        downstream = []
        for node in nx.descendants(graph, dataset_node):
            if node.startswith("dataset:"):
                downstream.append(node.replace("dataset:", ""))
        
        click.echo(f"\n📊 Lineage for: {dataset_name}")
        click.echo("-" * 50)
        
        click.echo("\n⬆️  Upstream sources (what feeds this):")
        if upstream:
            for source in sorted(upstream):
                click.echo(f"  └─ {source}")
        else:
            click.echo("  (none - this is a source dataset)")
        
        click.echo("\n⬇️  Downstream dependents (what uses this):")
        if downstream:
            for dep in sorted(downstream):
                click.echo(f"  └─ {dep}")
        else:
            click.echo("  (none - this is a sink dataset)")
        
    except Exception as e:
        click.echo(f"Error tracing lineage: {e}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('dataset_name')
def blast(repo_path, dataset_name):
    """Calculate blast radius if a dataset changes.
    
    DATASET_NAME: Name of the dataset to analyze
    """
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    lineage_file = cartography_dir / "lineage_graph.json"
    
    if not lineage_file.exists():
        click.echo("❌ No lineage graph found. Run 'analyze --phase 2' first.")
        return
    
    try:
        with open(lineage_file) as f:
            data = json.load(f)
        
        import networkx as nx
        from networkx.readwrite import json_graph
        graph = json_graph.node_link_graph(data["graph"])
        
        # Find dataset node
        dataset_node = f"dataset:{dataset_name}"
        if dataset_node not in graph:
            click.echo(f"❌ Dataset '{dataset_name}' not found.")
            return
        
        # Find all downstream dependents (including transformations)
        downstream = nx.descendants(graph, dataset_node)
        
        # Separate datasets and transformations
        downstream_datasets = [n.replace("dataset:", "") for n in downstream if n.startswith("dataset:")]
        downstream_transforms = [n for n in downstream if n.startswith("trans:")]
        
        click.echo(f"\n💥 Blast Radius Analysis: {dataset_name}")
        click.echo("-" * 50)
        
        click.echo(f"\n📊 If '{dataset_name}' changes or fails:")
        click.echo(f"  • {len(downstream_datasets)} datasets would be affected")
        click.echo(f"  • {len(downstream_transforms)} transformations would need to be re-run")
        
        if downstream_datasets:
            click.echo("\n📉 Affected datasets:")
            for ds in sorted(downstream_datasets)[:10]:  # Show first 10
                click.echo(f"  └─ {ds}")
            if len(downstream_datasets) > 10:
                click.echo(f"  ... and {len(downstream_datasets) - 10} more")
        
    except Exception as e:
        click.echo(f"Error calculating blast radius: {e}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def graph(repo_path):
    """Generate a simple text representation of the lineage graph."""
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    lineage_file = cartography_dir / "lineage_graph.json"
    
    if not lineage_file.exists():
        click.echo("❌ No lineage graph found. Run 'analyze --phase 2' first.")
        return
    
    try:
        with open(lineage_file) as f:
            data = json.load(f)
        
        import networkx as nx
        from networkx.readwrite import json_graph
        graph = json_graph.node_link_graph(data["graph"])
        
        click.echo(f"\n📊 Data Lineage Graph")
        click.echo("-" * 50)
        
        # Find sources (no incoming edges)
        sources = []
        for node in graph.nodes():
            if node.startswith("dataset:") and graph.in_degree(node) == 0:
                sources.append(node.replace("dataset:", ""))
        
        # Find sinks (no outgoing edges)
        sinks = []
        for node in graph.nodes():
            if node.startswith("dataset:") and graph.out_degree(node) == 0:
                sinks.append(node.replace("dataset:", ""))
        
        click.echo(f"\n📤 Source datasets (ingestion points):")
        for source in sorted(sources):
            click.echo(f"  └─ {source}")
        
        click.echo(f"\n📥 Sink datasets (final outputs):")
        for sink in sorted(sinks):
            click.echo(f"  └─ {sink}")
        
        # Show a simple DAG visualization
        click.echo(f"\n📈 Lineage DAG:")
        
        def print_dag(node, prefix="", seen=None):
            if seen is None:
                seen = set()
            if node in seen:
                return
            seen.add(node)
            
            node_name = node.replace("dataset:", "").replace("trans:", "🔄 ")
            click.echo(f"{prefix}└─ {node_name}")
            
            children = list(graph.successors(node))
            for i, child in enumerate(sorted(children)):
                is_last = (i == len(children) - 1)
                new_prefix = prefix + ("    " if is_last else "   │")
                print_dag(child, new_prefix + ("    " if is_last else "   │"), seen)
        
        # Start from sources
        for source in sorted(sources):
            print_dag(f"dataset:{source}")
        
    except Exception as e:
        click.echo(f"Error generating graph: {e}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def sources(repo_path):
    """List all source datasets (ingestion points)."""
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    lineage_file = cartography_dir / "lineage_graph.json"
    
    if not lineage_file.exists():
        click.echo("❌ No lineage graph found. Run 'analyze --phase 2' first.")
        return
    
    try:
        with open(lineage_file) as f:
            data = json.load(f)
        
        import networkx as nx
        from networkx.readwrite import json_graph
        graph = json_graph.node_link_graph(data["graph"])
        
        sources = []
        for node in graph.nodes():
            if node.startswith("dataset:") and graph.in_degree(node) == 0:
                sources.append(node.replace("dataset:", ""))
        
        click.echo(f"\n📤 Source Datasets (Ingestion Points):")
        click.echo("-" * 50)
        for source in sorted(sources):
            # Find what transformations read from this source
            consumers = []
            for trans in graph.successors(f"dataset:{source}"):
                if trans.startswith("trans:"):
                    consumers.append(trans)
            
            click.echo(f"📄 {source}")
            if consumers:
                click.echo(f"   └─ Consumed by: {len(consumers)} transformations")
        
        click.echo(f"\nTotal sources: {len(sources)}")
        
    except Exception as e:
        click.echo(f"Error listing sources: {e}")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def sinks(repo_path):
    """List all sink datasets (final outputs)."""
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    lineage_file = cartography_dir / "lineage_graph.json"
    
    if not lineage_file.exists():
        click.echo("❌ No lineage graph found. Run 'analyze --phase 2' first.")
        return
    
    try:
        with open(lineage_file) as f:
            data = json.load(f)
        
        import networkx as nx
        from networkx.readwrite import json_graph
        graph = json_graph.node_link_graph(data["graph"])
        
        sinks = []
        for node in graph.nodes():
            if node.startswith("dataset:") and graph.out_degree(node) == 0:
                sinks.append(node.replace("dataset:", ""))
        
        click.echo(f"\n📥 Sink Datasets (Final Outputs):")
        click.echo("-" * 50)
        for sink in sorted(sinks):
            # Find what transformations produce this sink
            producers = []
            for trans in graph.predecessors(f"dataset:{sink}"):
                if trans.startswith("trans:"):
                    producers.append(trans)
            
            click.echo(f"📄 {sink}")
            if producers:
                click.echo(f"   └─ Produced by: {len(producers)} transformations")
        
        click.echo(f"\nTotal sinks: {len(sinks)}")
        
    except Exception as e:
        click.echo(f"Error listing sinks: {e}")


if __name__ == "__main__":
    cli()