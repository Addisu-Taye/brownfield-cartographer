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
from src.models.nodes import KnowledgeGraph


@click.group()
def cli():
    """Brownfield Cartographer - Codebase Intelligence System"""
    pass


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--output', '-o', default=None, help='Output directory for cartography artifacts')
@click.option('--no-git', is_flag=True, help='Skip git analysis')
def analyze(repo_path, output, no_git):
    """Analyze a codebase and generate cartography artifacts."""
    start_time = time.time()
    
    repo_path = Path(repo_path).resolve()
    click.echo(f"🔍 Analyzing codebase: {repo_path}")
    
    # Set up output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = repo_path / ".cartography"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run Surveyor
    click.echo("\n📐 Phase 1: Surveyor Agent (Static Structure Analysis)")
    surveyor = Surveyor(str(repo_path))
    graph = surveyor.run()
    
    # Save Surveyor outputs
    surveyor.save_graph(output_dir / "module_graph.json")
    
    if surveyor.nodes:
        surveyor.save_dead_code_report(output_dir / "dead_code_candidates.md")
    
    # Print summary
    elapsed = time.time() - start_time
    click.echo(f"\n✅ Analysis complete in {elapsed:.2f} seconds")
    click.echo(f"📁 Artifacts saved to: {output_dir}")
    
    # Show next steps
    click.echo("\n🔜 Next Steps:")
    click.echo("  Phase 2: Hydrologist Agent (Data Lineage) - Coming soon")
    click.echo("  Phase 3: Semanticist Agent (LLM Analysis) - Coming soon")
    click.echo("  Phase 4: Archivist Agent (Living Context) - Coming soon")


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
        "lineage_graph.json": "Lineage Graph (Phase 2)",
        "CODEBASE.md": "Living Context (Phase 4)",
        "onboarding_brief.md": "Onboarding Brief (Phase 4)"
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
            
            click.echo("\n📈 Summary:")
            metadata = data.get("metadata", {})
            stats = metadata.get("stats", {})
            
            if stats.get("python_files", 0) > 0:
                click.echo(f"  Python modules: {stats['python_files']}")
                click.echo(f"  Import relationships: {stats.get('edges_added', 0)}")
                click.echo(f"  Dead code candidates: {stats.get('dead_code_candidates', 0)}")
            else:
                click.echo(f"  Total files scanned: {stats.get('files_scanned', 0)}")
                click.echo(f"  Python files: {stats.get('python_files', 0)}")
                click.echo(f"  SQL files: {stats.get('sql_files', 0)}")
                click.echo(f"  YAML files: {stats.get('yaml_files', 0)}")
        except:
            pass


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.argument('module_path')
def explain(repo_path, module_path):
    """Explain what a specific module does (basic version)."""
    repo_path = Path(repo_path).resolve()
    module_file = repo_path / module_path
    
    if not module_file.exists():
        click.echo(f"❌ Module not found: {module_file}")
        return
    
    click.echo(f"📖 Explaining: {module_path}")
    click.echo("-" * 50)
    
    # Check if we have cartography data
    cartography_dir = repo_path / ".cartography"
    module_graph = cartography_dir / "module_graph.json"
    
    if module_graph.exists():
        try:
            with open(module_graph) as f:
                data = json.load(f)
            
            nodes = data.get("nodes", {})
            if module_path in nodes:
                node = nodes[module_path]
                click.echo(f"Language: {node.get('language', 'unknown')}")
                click.echo(f"Functions: {len(node.get('public_functions', []))}")
                click.echo(f"Classes: {len(node.get('classes', []))}")
                click.echo(f"Complexity: {node.get('complexity_score', 0):.2f}")
                
                if node.get('docstring'):
                    click.echo(f"\nDocstring:\n{node['docstring']}")
                
                velocity = node.get('change_velocity_30d', 0)
                click.echo(f"\nChanges (30d): {velocity}")
            else:
                click.echo("Module not found in cartography data.")
        except:
            click.echo("Error loading cartography data.")
    else:
        click.echo("No cartography data found. Run 'analyze' first.")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
def graph(repo_path):
    """Generate a simple text representation of the module graph."""
    repo_path = Path(repo_path).resolve()
    cartography_dir = repo_path / ".cartography"
    module_graph = cartography_dir / "module_graph.json"
    
    if not module_graph.exists():
        click.echo("❌ No module graph found. Run 'analyze' first.")
        return
    
    try:
        with open(module_graph) as f:
            data = json.load(f)
        
        graph_data = data.get("graph", {})
        nodes = graph_data.get("nodes", [])
        links = graph_data.get("links", [])
        
        click.echo(f"📊 Module Graph: {len(nodes)} nodes, {len(links)} edges")
        click.echo("-" * 50)
        
        # Group by directory
        directories = {}
        for node in nodes:
            path = node.get('id', '')
            dir_name = '/'.join(path.split('/')[:-1]) or '.'
            if dir_name not in directories:
                directories[dir_name] = []
            directories[dir_name].append(path)
        
        for dir_name, files in sorted(directories.items()):
            click.echo(f"\n📁 {dir_name}/")
            for file in sorted(files):
                # Find incoming/outgoing edges
                in_degree = sum(1 for link in links if link.get('target') == file)
                out_degree = sum(1 for link in links if link.get('source') == file)
                
                # Get node metadata
                node_data = next((n for n in nodes if n.get('id') == file), {})
                velocity = node_data.get('change_velocity_30d', 0)
                
                # Choose icon based on activity
                if velocity > 0:
                    icon = "🔄"  # Active
                elif in_degree == 0 and out_degree == 0:
                    icon = "💤"  # Isolated
                else:
                    icon = "📄"  # Normal
                
                click.echo(f"  {icon} {file.split('/')[-1]} (↑{in_degree} ↓{out_degree})")
        
    except Exception as e:
        click.echo(f"Error generating graph: {e}")


if __name__ == "__main__":
    cli()