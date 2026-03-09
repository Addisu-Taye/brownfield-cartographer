"""Orchestrator - Wires Surveyor + Hydrologist agents."""

from pathlib import Path
from src.agents.surveyor import Surveyor
from src.agents.hydrologist import Hydrologist

class CartographyOrchestrator:
    """Coordinates multi-agent codebase analysis pipeline."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.output_dir = Path(".cartography")
        self.surveyor = Surveyor(repo_path)
        self.hydrologist = Hydrologist(repo_path)
    
    def run_full_pipeline(self):
        """Run Surveyor + Hydrologist in sequence."""
        print("=" * 60)
        print("🗺️  BROWNFIELD CARTOGRAPHER - Full Analysis Pipeline")
        print("=" * 60)
        
        # Phase 1: Surveyor (Module Structure)
        print("\n📋  PHASE 1: Surveyor Agent (Static Structure)")
        print("-" * 60)
        module_graph = self.surveyor.run()
        self.surveyor.save_graph(self.output_dir / "module_graph.json")
        
        # Phase 2: Hydrologist (Data Lineage)
        print("\n💧  PHASE 2: Hydrologist Agent (Data Lineage)")
        print("-" * 60)
        lineage_graph = self.hydrologist.run()
        self.hydrologist.save_graph(self.output_dir / "lineage_graph.json")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅  ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"📁  Output directory: {self.output_dir.absolute()}")
        print(f"📊  Module graph: {self.output_dir / 'module_graph.json'}")
        print(f"🔗  Lineage graph: {self.output_dir / 'lineage_graph.json'}")
        
        return {
            "module_graph": module_graph,
            "lineage_graph": lineage_graph
        }

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python src/orchestrator.py <repo_path>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    orchestrator = CartographyOrchestrator(repo_path)
    orchestrator.run_full_pipeline()

if __name__ == "__main__":
    main()