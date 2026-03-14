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
        self.datasets = {}
        self.transformations = {}
        
        self._load_graphs()
        
        self.stats = {
            "queries_executed": 0,
            "tools_used": {
                "find_implementation": 0,
                "trace_lineage": 0,
                "blast_radius": 0,
                "explain_module": 0
            }
        }
    
    def _load_graphs(self):
        """Load graphs from cache."""
        # Load module graph
        module_path = self.cache_dir / "module_graph.json"
        if module_path.exists():
            try:
                with open(module_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "graph" in data:
                        self.module_graph = json_graph.node_link_graph(data["graph"])
                    self.module_nodes = data.get("nodes", {})
                logger.info(f"Loaded module graph with {len(self.module_graph.nodes) if self.module_graph else 0} nodes")
            except Exception as e:
                logger.error(f"Error loading module graph: {e}")
        
        # Load lineage graph
        lineage_path = self.cache_dir / "lineage_graph.json"
        if lineage_path.exists():
            try:
                with open(lineage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "graph" in data:
                        self.lineage_graph = json_graph.node_link_graph(data["graph"])
                    self.datasets = data.get("datasets", {})
                    self.transformations = data.get("transformations", {})
                    self.sources = data.get("sources", [])
                    self.sinks = data.get("sinks", [])
                logger.info(f"Loaded lineage graph with {len(self.lineage_graph.nodes) if self.lineage_graph else 0} nodes")
            except Exception as e:
                logger.error(f"Error loading lineage graph: {e}")
        
        # Load semantic index
        semantic_path = self.cache_dir / "semantic_index.json"
        if semantic_path.exists():
            try:
                with open(semantic_path, 'r', encoding='utf-8') as f:
                    self.semantic_index = json.load(f)
                logger.info(f"Loaded semantic index with {len(self.semantic_index.get('purpose_statements', {}))} statements")
            except Exception as e:
                logger.error(f"Error loading semantic index: {e}")
    
    def find_implementation(self, concept: str) -> List[Dict[str, Any]]:
        """Find implementation of a concept using semantic search."""
        self.stats["queries_executed"] += 1
        self.stats["tools_used"]["find_implementation"] += 1
        
        results = []
        
        # Search in semantic index
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
        
        # Search in datasets
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
        self.stats["tools_used"]["trace_lineage"] += 1
        
        if not self.lineage_graph:
            return {"error": "Lineage graph not loaded"}
        
        # Find the dataset node (case-insensitive)
        node_id = None
        for node in self.lineage_graph.nodes():
            if node.startswith("dataset:") and node[8:].lower() == dataset.lower():
                node_id = node
                break
        
        if not node_id:
            return {"error": f"Dataset '{dataset}' not found"}
        
        result = {
            "dataset": dataset,
            "direction": direction,
            "upstream": [],
            "downstream": [],
            "files": []
        }
        
        try:
            if direction == "upstream" or direction == "both":
                # Find ancestors (what feeds into this)
                ancestors = nx.ancestors(self.lineage_graph, node_id)
                for anc in ancestors:
                    if anc.startswith("dataset:"):
                        result["upstream"].append(anc.replace("dataset:", ""))
                    elif anc.startswith("trans:"):
                        trans_id = anc.replace("trans:", "")
                        if trans_id in self.transformations:
                            result["files"].append({
                                "file": self.transformations[trans_id].get("file"),
                                "type": "transformation",
                                "relation": "upstream"
                            })
            
            if direction == "downstream" or direction == "both":
                # Find descendants (what depends on this)
                descendants = nx.descendants(self.lineage_graph, node_id)
                for desc in descendants:
                    if desc.startswith("dataset:"):
                        result["downstream"].append(desc.replace("dataset:", ""))
                    elif desc.startswith("trans:"):
                        trans_id = desc.replace("trans:", "")
                        if trans_id in self.transformations:
                            result["files"].append({
                                "file": self.transformations[trans_id].get("file"),
                                "type": "transformation",
                                "relation": "downstream"
                            })
        except Exception as e:
            logger.error(f"Error traversing graph: {e}")
        
        return result
        
    def blast_radius(self, module_path: str) -> Dict[str, Any]:
        """Calculate blast radius if a module changes."""
        self.stats["queries_executed"] += 1
        self.stats["tools_used"]["blast_radius"] += 1
        
        result = {
            "module": module_path,
            "direct_dependents": 0,
            "dependents": [],
            "datasets_affected": [],
            "transformations_affected": [],
            "total_impact": 0
        }
        
        # Extract module name for matching
        module_name = Path(module_path).name
        module_stem = Path(module_path).stem
        
        logger.info(f"Calculating blast radius for {module_path}")
        
        # Find all transformations that involve this module
        affected_transformations = set()
        starting_datasets = set()
        
        for trans_id, trans_info in self.transformations.items():
            trans_file = trans_info.get('file', '')
            
            # Check if this transformation is the module itself or uses it
            if (module_path in trans_file or 
                module_name in trans_file or 
                module_stem in trans_file):
                affected_transformations.add(trans_id)
                
                # Add datasets this transformation produces
                for write_dataset in trans_info.get('writes', []):
                    starting_datasets.add(write_dataset)
                    logger.info(f"Starting dataset: {write_dataset}")
                
                # Also consider that this transformation might produce a dataset
                # with the same name as the stem
                if module_stem.startswith('stg_'):
                    starting_datasets.add(module_stem)
        
        result["transformations_affected"] = list(affected_transformations)
        
        # Find all downstream datasets using BFS
        all_affected_datasets = set(starting_datasets)
        
        if self.lineage_graph:
            # Do a BFS from each starting dataset to find all downstream datasets
            from collections import deque
            
            for start_dataset in starting_datasets:
                node_id = f"dataset:{start_dataset}"
                if node_id not in self.lineage_graph:
                    continue
                
                # BFS to find all downstream datasets
                visited = set()
                queue = deque([node_id])
                
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    
                    # Add to affected datasets if it's a dataset node
                    if current.startswith("dataset:") and current != node_id:
                        all_affected_datasets.add(current.replace("dataset:", ""))
                    
                    # Follow all outgoing edges (downstream)
                    for successor in self.lineage_graph.successors(current):
                        if successor not in visited:
                            queue.append(successor)
        
        # Also check transformations that read from our datasets
        # This is a fallback in case the graph edges are missing
        for trans_id, trans_info in self.transformations.items():
            for read_dataset in trans_info.get('reads', []):
                if read_dataset in starting_datasets:
                    # This transformation reads from our dataset
                    for write_dataset in trans_info.get('writes', []):
                        all_affected_datasets.add(write_dataset)
                        logger.info(f"Found via transformation read: {read_dataset} -> {write_dataset}")
        
        result["datasets_affected"] = list(all_affected_datasets)
        
        # Find code dependents from module graph
        if self.module_graph:
            for node in self.module_graph.nodes():
                if module_path in node or module_name in node or module_stem in node:
                    try:
                        dependents = list(self.module_graph.predecessors(node))
                        result["dependents"] = dependents[:10]
                        result["direct_dependents"] = len(dependents)
                    except Exception as e:
                        logger.error(f"Error finding dependents: {e}")
                    break
        
        # Calculate total impact
        all_affected = set(result["dependents"]) | set(result["datasets_affected"]) | set(result["transformations_affected"])
        result["total_impact"] = len(all_affected)
        
        return result
            
        def explain_module(self, module_path: str) -> Dict[str, Any]:
            """Explain what a module does using semantic data."""
            self.stats["queries_executed"] += 1
            self.stats["tools_used"]["explain_module"] += 1
            
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
                
                # Try exact match
                if module_path in purposes:
                    explanation["purpose"] = purposes[module_path]
                else:
                    # Try partial match
                    for path, purpose in purposes.items():
                        if module_path in path or path in module_path:
                            explanation["purpose"] = purpose
                            explanation["matched_path"] = path
                            break
                
                # Check for documentation drift
                drift = self.semantic_index.get("doc_drift_flags", {})
                for path, drifted in drift.items():
                    if module_path in path or path in module_path:
                        explanation["doc_drift"] = drifted
                        break
                
                # Get domain cluster
                domains = self.semantic_index.get("domain_clusters", {})
                for path, domain in domains.items():
                    if module_path in path or path in module_path:
                        explanation["domain"] = domain
                        break
            
            # Get dependencies from module graph
            if self.module_graph:
                # Find the module in the graph
                found_module = None
                for node in self.module_graph.nodes():
                    if module_path in node or node in module_path:
                        found_module = node
                        break
                
                if found_module:
                    # What this module imports (successors)
                    deps = list(self.module_graph.successors(found_module))
                    explanation["dependencies"] = deps[:10]
                    
                    # What imports this module (predecessors)
                    dependents = list(self.module_graph.predecessors(found_module))
                    explanation["dependents"] = dependents[:10]
            
            # Get datasets this module affects
            for dataset, info in self.datasets.items():
                files = info.get("files", [])
                for f in files:
                    if module_path in f or (found_module and found_module in f):
                        explanation["datasets"].append(dataset)
                        break
            
            return explanation
    
    def query(self, question: str) -> Dict[str, Any]:
        """Natural language query interface."""
        self.stats["queries_executed"] += 1
        
        question_lower = question.lower()
        
        # Parse lineage queries
        if "lineage" in question_lower or "trace" in question_lower:
            import re
            
            # Pattern 1: "trace lineage of customers"
            match = re.search(r"(?:trace\s+)?lineage\s+(?:of\s+)?['\"]?(\w+)['\"]?", question_lower)
            if match:
                dataset = match.group(1)
                direction = "downstream" if "downstream" in question_lower else "upstream"
                return {
                    "tool": "trace_lineage",
                    "result": self.trace_lineage(dataset, direction)
                }
            
            # Pattern 2: "lineage customers"
            match = re.search(r"lineage\s+(\w+)", question_lower)
            if match:
                dataset = match.group(1)
                return {
                    "tool": "trace_lineage",
                    "result": self.trace_lineage(dataset)
                }
        
        # Parse find queries
        elif "find" in question_lower or "where is" in question_lower or "search" in question_lower:
            import re
            match = re.search(r"(?:find|where is|search for?)\s+['\"]?(.+)['\"]?", question_lower)
            if match:
                concept = match.group(1)
                return {
                    "tool": "find_implementation",
                    "result": self.find_implementation(concept)
                }
        
        # Parse blast radius queries
        elif "blast" in question_lower or "radius" in question_lower or "impact" in question_lower:
            import re
            match = re.search(r"(?:blast|impact)(?:\s+radius)?\s+(?:of\s+)?['\"]?(.+)['\"]?", question_lower)
            if match:
                module = match.group(1)
                return {
                    "tool": "blast_radius",
                    "result": self.blast_radius(module)
                }
        
        # Parse explain queries
        elif "explain" in question_lower or "what does" in question_lower or "describe" in question_lower:
            import re
            match = re.search(r"(?:explain|what does|describe)\s+['\"]?(.+)['\"]?", question_lower)
            if match:
                module = match.group(1)
                return {
                    "tool": "explain_module",
                    "result": self.explain_module(module)
                }
        
        return {
            "tool": "unknown",
            "result": "I couldn't understand the query. Try:\n- find customer logic\n- trace lineage of customers\n- blast radius of stg_orders\n- explain models/customers.sql"
        }
    
    def interactive_mode(self):
        """Run in interactive query mode."""
        print("\n" + "="*60)
        print("🗺️  Brownfield Cartographer - Navigator")
        print("="*60)
        print("\nAvailable commands:")
        print("  find <concept>           - Find implementation of concept")
        print("  lineage <dataset>        - Trace lineage of dataset")
        print("  blast <module>           - Calculate blast radius")
        print("  explain <module>         - Explain module purpose")
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