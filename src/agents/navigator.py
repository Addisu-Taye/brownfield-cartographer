"""Navigator Agent - Query Interface for Knowledge Graph

A LangGraph agent with tools for querying the codebase knowledge graph.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import networkx as nx
from networkx.readwrite import json_graph

logger = logging.getLogger(__name__)

# Try to import LangGraph if available
try:
    from langgraph.graph import StateGraph, MessageGraph
    from langgraph.prebuilt import ToolExecutor
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("langgraph not installed. Navigator will run in basic mode.")


class Navigator:
    """Navigator Agent - Query Interface
    
    Provides tools for querying the knowledge graph:
    - find_implementation: Semantic search for code
    - trace_lineage: Graph traversal for data lineage
    - blast_radius: Impact analysis
    - explain_module: Generative explanations
    """
    
    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        
        # Load graph data
        self.module_graph = None
        self.lineage_graph = None
        self.semantic_index = None
        
        self._load_graphs()
        
        self.stats = {
            "queries_executed": 0,
            "tools_used": {}
        }
    
    def _load_graphs(self):
        """Load graphs from cache."""
        # Load module graph
        module_path = self.cache_dir / "module_graph.json"
        if module_path.exists():
            with open(module_path) as f:
                data = json.load(f)
                if "graph" in data:
                    self.module_graph = json_graph.node_link_graph(data["graph"])
                logger.info(f"Loaded module graph with {len(self.module_graph.nodes)} nodes")
        
        # Load lineage graph
        lineage_path = self.cache_dir / "lineage_graph.json"
        if lineage_path.exists():
            with open(lineage_path) as f:
                data = json.load(f)
                if "graph" in data:
                    self.lineage_graph = json_graph.node_link_graph(data["graph"])
                self.datasets = data.get("datasets", {})
                self.transformations = data.get("transformations", {})
                logger.info(f"Loaded lineage graph with {len(self.lineage_graph.nodes)} nodes")
        
        # Load semantic index
        semantic_path = self.cache_dir / "semantic_index.json"
        if semantic_path.exists():
            with open(semantic_path) as f:
                self.semantic_index = json.load(f)
                logger.info(f"Loaded semantic index")
    
    def find_implementation(self, concept: str) -> List[Dict[str, Any]]:
        """Find implementation of a concept using semantic search."""
        self.stats["queries_executed"] += 1
        self.stats["tools_used"]["find_implementation"] = self.stats["tools_used"].get("find_implementation", 0) + 1
        
        results = []
        
        # Simple keyword search (in production, use embeddings)
        if self.semantic_index:
            purposes = self.semantic_index.get("purpose_statements", {})
            for module, purpose in purposes.items():
                if concept.lower() in purpose.lower() or concept.lower() in module.lower():
                    results.append({
                        "module": module,
                        "purpose": purpose,
                        "confidence": 0.8,
                        "evidence": f"Semantic match in purpose statement"
                    })
        
        # Also search in datasets
        if hasattr(self, 'datasets'):
            for dataset in self.datasets:
                if concept.lower() in dataset.lower():
                    results.append({
                        "dataset": dataset,
                        "type": "dataset",
                        "evidence": f"Dataset name match"
                    })
        
        return results[:10]  # Return top 10
    
    def trace_lineage(self, dataset: str, direction: str = "upstream") -> Dict[str, Any]:
        """Trace lineage upstream or downstream from a dataset."""
        self.stats["queries_executed"] += 1
        self.stats["tools_used"]["trace_lineage"] = self.stats["tools_used"].get("trace_lineage", 0) + 1
        
        if not self.lineage_graph:
            return {"error": "Lineage graph not loaded"}
        
        node_id = f"dataset:{dataset}"
        if node_id not in self.lineage_graph:
            return {"error": f"Dataset '{dataset}' not found"}
        
        result = {
            "dataset": dataset,
            "direction": direction,
            "path": [],
            "files": []
        }
        
        if direction == "upstream":
            # Find ancestors (what feeds into this)
            ancestors = nx.ancestors(self.lineage_graph, node_id)
            for anc in ancestors:
                if anc.startswith("dataset:"):
                    result["path"].append(anc.replace("dataset:", ""))
                elif anc.startswith("trans:"):
                    # Find the file for this transformation
                    trans_id = anc.replace("trans:", "")
                    if trans_id in self.transformations:
                        result["files"].append({
                            "file": self.transformations[trans_id].get("file"),
                            "type": "transformation"
                        })
        else:
            # Find descendants (what depends on this)
            descendants = nx.descendants(self.lineage_graph, node_id)
            for desc in descendants:
                if desc.startswith("dataset:"):
                    result["path"].append(desc.replace("dataset:", ""))
                elif desc.startswith("trans:"):
                    trans_id = desc.replace("trans:", "")
                    if trans_id in self.transformations:
                        result["files"].append({
                            "file": self.transformations[trans_id].get("file"),
                            "type": "transformation"
                        })
        
        return result
    
    def blast_radius(self, module_path: str) -> Dict[str, Any]:
        """Calculate blast radius if a module changes."""
        self.stats["queries_executed"] += 1
        self.stats["tools_used"]["blast_radius"] = self.stats["tools_used"].get("blast_radius", 0) + 1
        
        if not self.module_graph:
            return {"error": "Module graph not loaded"}
        
        if module_path not in self.module_graph:
            return {"error": f"Module '{module_path}' not found"}
        
        # Find all downstream dependents (modules that import this)
        dependents = []
        for node in nx.descendants(self.module_graph, module_path):
            # Check if this node imports our module
            if self.module_graph.has_edge(node, module_path):
                dependents.append(node)
        
        # Also check lineage impact if available
        dataset_impact = []
        if self.lineage_graph and hasattr(self, 'datasets'):
            # Find datasets that might be affected
            for dataset in self.datasets:
                if module_path in self.datasets[dataset].get("files", []):
                    dataset_impact.append(dataset)
        
        return {
            "module": module_path,
            "direct_dependents": len(dependents),
            "dependents": dependents[:10],
            "datasets_affected": dataset_impact[:10],
            "total_impact": len(dependents) + len(dataset_impact)
        }
    
    def explain_module(self, module_path: str) -> Dict[str, Any]:
        """Explain what a module does using semantic data."""
        self.stats["queries_executed"] += 1
        self.stats["tools_used"]["explain_module"] = self.stats["tools_used"].get("explain_module", 0) + 1
        
        explanation = {
            "module": module_path,
            "purpose": "No semantic data available",
            "dependencies": [],
            "dependents": [],
            "datasets": []
        }
        
        # Get purpose from semantic index
        if self.semantic_index:
            purposes = self.semantic_index.get("purpose_statements", {})
            if module_path in purposes:
                explanation["purpose"] = purposes[module_path]
            
            # Check for documentation drift
            drift = self.semantic_index.get("doc_drift_flags", {})
            if module_path in drift:
                explanation["doc_drift"] = drift[module_path]
            
            # Get domain cluster
            domains = self.semantic_index.get("domain_clusters", {})
            if module_path in domains:
                explanation["domain"] = domains[module_path]
        
        # Get dependencies from module graph
        if self.module_graph and module_path in self.module_graph:
            # What this module imports
            deps = list(self.module_graph.successors(module_path))
            explanation["dependencies"] = deps[:10]
            
            # What imports this module
            dependents = list(self.module_graph.predecessors(module_path))
            explanation["dependents"] = dependents[:10]
        
        # Get datasets this module affects
        if hasattr(self, 'datasets'):
            for dataset, info in self.datasets.items():
                if module_path in info.get("files", []):
                    explanation["datasets"].append(dataset)
        
        return explanation
    
    def query(self, question: str) -> Dict[str, Any]:
        """Natural language query interface."""
        self.stats["queries_executed"] += 1
        
        question_lower = question.lower()
        
        # Route to appropriate tool based on keywords
        if "find" in question_lower or "where is" in question_lower or "implementation" in question_lower:
            # Extract concept (simple heuristic)
            words = question.split()
            concept = words[-1] if words else ""
            return {
                "tool": "find_implementation",
                "result": self.find_implementation(concept)
            }
        
        elif "lineage" in question_lower or "trace" in question_lower or "upstream" in question_lower:
            # Extract dataset name
            words = question.split()
            for i, word in enumerate(words):
                if word in ["of", "for", "trace", "lineage"] and i+1 < len(words):
                    dataset = words[i+1].strip('?.')
                    direction = "upstream" if "upstream" in question_lower else "downstream"
                    return {
                        "tool": "trace_lineage",
                        "result": self.trace_lineage(dataset, direction)
                    }
        
        elif "blast" in question_lower or "radius" in question_lower or "impact" in question_lower:
            # Extract module path
            words = question.split()
            for i, word in enumerate(words):
                if word in ["of", "if", "module"] and i+1 < len(words):
                    module = words[i+1].strip('?.')
                    return {
                        "tool": "blast_radius",
                        "result": self.blast_radius(module)
                    }
        
        elif "explain" in question_lower or "what does" in question_lower:
            # Extract module path
            words = question.split()
            for i, word in enumerate(words):
                if word in ["explain", "module"] and i+1 < len(words):
                    module = words[i+1].strip('?.')
                    return {
                        "tool": "explain_module",
                        "result": self.explain_module(module)
                    }
        
        return {
            "tool": "unknown",
            "result": "I couldn't understand the query. Try: find X, trace lineage of Y, blast radius of Z, explain module M"
        }
    
    def interactive_mode(self):
        """Run in interactive query mode."""
        print("\n" + "="*60)
        print("🗺️  Brownfield Cartographer - Navigator")
        print("="*60)
        print("\nAvailable commands:")
        print("  find <concept>           - Find implementation of concept")
        print("  lineage <dataset>        - Trace lineage of dataset")
        print("  blast <module>            - Calculate blast radius")
        print("  explain <module>          - Explain module purpose")
        print("  quit                      - Exit")
        print("-"*60)
        
        while True:
            try:
                query = input("\n🔍 Query> ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not query:
                    continue
                
                result = self.query(query)
                print("\n📊 Result:")
                print(json.dumps(result, indent=2))
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("\n👋 Goodbye!")