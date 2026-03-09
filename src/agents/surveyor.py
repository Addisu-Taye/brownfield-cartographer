import networkx as nx
from pathlib import Path
import git
from src.analyzers.tree_sitter_analyzer import TreeSitterAnalyzer
from src.models.nodes import ModuleNode, EdgeType
from typing import Dict, List, Optional, Tuple, Set
import json
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Surveyor:
    """Agent 1: Static Structure Analyst
    
    Performs deep static analysis of the codebase:
    - Module graph construction
    - Git change velocity analysis
    - Dead code candidate detection
    - Critical path identification via PageRank
    """
    
    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve()
        self.analyzer = TreeSitterAnalyzer()
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, ModuleNode] = {}
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git Repo for Velocity
        self._init_git_repo()
        
        # Track statistics
        self.stats = {
            "files_scanned": 0,
            "python_files": 0,
            "sql_files": 0,
            "yaml_files": 0,
            "jupyter_files": 0,
            "other_files": 0,
            "edges_added": 0,
            "dead_code_candidates": 0
        }
        
        # Track change velocity window
        self.velocity_window_days = 30
        
        # Known entry point patterns
        self.entry_point_patterns = [
            "main.py", "cli.py", "__init__.py", "__main__.py",
            "app.py", "run.py", "server.py", "wsgi.py", "manage.py"
        ]
        
        # Known test patterns
        self.test_patterns = [
            "test_", "_test", "tests/", "test/", "conftest.py"
        ]
    
    def _init_git_repo(self):
        """Initialize Git repository with better error handling."""
        try:
            self.git_repo = git.Repo(self.repo_path)
            # Get the first commit date for context
            first_commit = list(self.git_repo.iter_commits(max_count=1))[-1]
            self.repo_age_days = (datetime.now() - datetime.fromtimestamp(first_commit.committed_date)).days
            logger.info(f"Git repository initialized. Age: {self.repo_age_days} days")
        except (git.InvalidGitRepositoryError, git.NoSuchPathError, IndexError):
            self.git_repo = None
            self.repo_age_days = 0
            logger.warning("No valid Git repository found. Change velocity will be unavailable.")
    
    def extract_git_velocity(self, file_path: Path, days: Optional[int] = None) -> Dict[str, int]:
        """Enhanced git velocity extraction with multiple time windows.
        
        Returns:
            Dict with commit counts for different time windows
        """
        days = days or self.velocity_window_days
        
        if not self.git_repo or not file_path.exists():
            return {"30d": 0, "90d": 0, "total": 0}
        
        try:
            rel_path = str(file_path.relative_to(self.repo_path))
            
            # Total commits (all time)
            total_commits = len(list(self.git_repo.iter_commits(paths=[rel_path])))
            
            # Recent commits (30 days)
            since_30 = datetime.now() - timedelta(days=30)
            recent_30 = len(list(self.git_repo.iter_commits(
                paths=[rel_path],
                since=since_30.isoformat()
            )))
            
            # Recent commits (90 days)
            since_90 = datetime.now() - timedelta(days=90)
            recent_90 = len(list(self.git_repo.iter_commits(
                paths=[rel_path],
                since=since_90.isoformat()
            )))
            
            return {
                "30d": recent_30,
                "90d": recent_90,
                "total": total_commits
            }
            
        except Exception as e:
            logger.debug(f"Failed to extract git velocity for {file_path}: {e}")
            return {"30d": 0, "90d": 0, "total": 0}
    
    def scan_repository(self) -> nx.DiGraph:
        """Walk the repo and analyze all supported files."""
        logger.info(f"🔍 Surveying {self.repo_path}...")
        
        # Reset stats
        self.stats = {k: 0 for k in self.stats.keys()}
        
        # Track files by language
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Skip virtual environments, hidden dirs, and cache
            if any(part in str(file_path) for part in [".venv", ".git", "__pycache__", ".pytest_cache", ".cartography"]):
                continue
            
            self.stats["files_scanned"] += 1
            language = self.analyzer.get_language_for_file(file_path)
            
            # Update statistics
            if language in self.stats:
                self.stats[f"{language}_files"] = self.stats.get(f"{language}_files", 0) + 1
            else:
                self.stats["other_files"] += 1
            
            # Analyze based on language
            if language == "python":
                self._analyze_python_file(file_path)
            elif language in ("sql", "yaml", "jupyter"):
                # Track for Hydrologist, but don't build full graph yet
                self.stats[f"{language}_files"] = self.stats.get(f"{language}_files", 0) + 1
            else:
                pass  # Skip unknown files
        
        # Print summary
        self._print_scan_summary()
        
        return self.graph
    
    def _analyze_python_file(self, file_path: Path):
        """Analyze a Python file and add to graph."""
        node = self.analyzer.analyze_file(file_path)
        
        # Add git velocity data
        velocity = self.extract_git_velocity(file_path)
        node.change_velocity_30d = velocity["30d"]
        node.change_velocity_90d = velocity["90d"]
        node.total_commits = velocity["total"]
        
        # Add relative path
        rel_path = str(file_path.relative_to(self.repo_path))
        node.path = rel_path
        
        # Detect if this is a test file
        node.is_test = any(pattern in rel_path for pattern in self.test_patterns)
        
        # Detect if this is an entry point
        node.is_entry_point = any(pattern in rel_path for pattern in self.entry_point_patterns)
        
        # Store node
        self.nodes[rel_path] = node
        self.graph.add_node(
            rel_path,
            **{k: v for k, v in node.model_dump().items() if v is not None}
        )
        self.stats["python_files"] += 1
    
    def build_import_graph(self, use_jedi: bool = False):
        """Enhanced import graph builder with better resolution."""
        logger.info("🔗 Building import graph...")
        
        edges_added = 0
        unresolved_imports = []
        
        for path, node in self.nodes.items():
            for imp in node.imports:
                # Try multiple resolution strategies
                target = self._resolve_import(path, imp)
                
                if target and target != path:
                    # Add edge with metadata
                    self.graph.add_edge(
                        path,
                        target,
                        type=EdgeType.IMPORTS,
                        import_name=imp,
                        resolved=True
                    )
                    edges_added += 1
                    
                    # Update import count in target node
                    if target in self.nodes:
                        self.nodes[target].import_count += 1
                else:
                    unresolved_imports.append((path, imp))
        
        self.stats["edges_added"] = edges_added
        
        # Log summary
        logger.info(f"✅ Mapped {edges_added} import relationships.")
        if unresolved_imports:
            logger.debug(f"Unresolved imports: {len(unresolved_imports)}")
        
        # Run graph analysis
        self._analyze_graph()
    
    def _resolve_import(self, source_path: str, import_name: str) -> Optional[str]:
        """Resolve an import to a module path with multiple strategies."""
        source_dir = Path(source_path).parent
        
        # Strategy 1: Direct match (import x matches x.py)
        direct = f"{import_name.replace('.', '/')}.py"
        if direct in self.nodes:
            return direct
        
        # Strategy 2: Module in same directory
        same_dir = str(source_dir / f"{import_name.split('.')[-1]}.py")
        if same_dir in self.nodes:
            return same_dir
        
        # Strategy 3: Package import (import x.y matches x/y.py)
        package_path = import_name.replace('.', '/') + '.py'
        if package_path in self.nodes:
            return package_path
        
        # Strategy 4: Look for __init__.py in package
        init_path = import_name.replace('.', '/') + '/__init__.py'
        if init_path in self.nodes:
            return init_path
        
        # Strategy 5: Fuzzy match (for common patterns)
        for candidate in self.nodes.keys():
            if import_name in candidate or candidate in import_name:
                return candidate
        
        return None
    
    def _analyze_graph(self):
        """Run graph analysis algorithms."""
        if len(self.graph) == 0:
            return
        
        # PageRank for critical nodes
        try:
            pagerank = nx.pagerank(self.graph)
            for node, score in pagerank.items():
                if node in self.nodes:
                    self.nodes[node].pagerank_score = score
        except Exception as e:
            logger.warning(f"PageRank failed: {e}")
        
        # Detect circular dependencies (strongly connected components)
        try:
            sccs = list(nx.strongly_connected_components(self.graph))
            circular_deps = [scc for scc in sccs if len(scc) > 1]
            self.stats["circular_dependencies"] = len(circular_deps)
            
            # Tag nodes in circular dependencies
            for scc in circular_deps:
                for node in scc:
                    if node in self.nodes:
                        self.nodes[node].in_circular_dependency = True
        except Exception as e:
            logger.warning(f"SCC detection failed: {e}")
    
    def identify_critical_path(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """Use PageRank to find architectural hubs."""
        if len(self.graph) == 0:
            return []
        
        # Get nodes with PageRank scores
        nodes_with_scores = [
            (node, self.nodes[node].pagerank_score)
            for node in self.graph.nodes()
            if node in self.nodes and self.nodes[node].pagerank_score > 0
        ]
        
        # Sort by score
        sorted_nodes = sorted(nodes_with_scores, key=lambda x: x[1], reverse=True)
        
        return sorted_nodes[:top_n]
    
    def identify_dead_code(self) -> List[Tuple[str, Dict]]:
        """Enhanced dead code detection with multiple signals."""
        dead_candidates = []
        
        for node_path, node in self.nodes.items():
            # Skip entry points and test files
            if node.is_entry_point or node.is_test:
                continue
            
            # Skip __init__.py files (they're special)
            if "__init__.py" in node_path:
                continue
            
            signals = {
                "in_degree": self.graph.in_degree(node_path),
                "out_degree": self.graph.out_degree(node_path),
                "recent_changes": node.change_velocity_30d,
                "total_changes": node.total_commits,
                "import_count": node.import_count
            }
            
            # Dead code signals:
            # 1. No one imports it (in_degree = 0)
            # 2. It doesn't import anything (out_degree = 0) - isolated
            # 3. No recent changes (low velocity)
            # 4. Low total commit count
            
            if signals["in_degree"] == 0:
                # Check other signals
                if signals["recent_changes"] == 0:
                    dead_candidates.append((node_path, signals))
                elif signals["total_changes"] < 3:
                    dead_candidates.append((node_path, signals))
        
        self.stats["dead_code_candidates"] = len(dead_candidates)
        
        return dead_candidates
    
    def get_change_velocity_summary(self) -> Dict:
        """Summarize change velocity across the codebase."""
        if not self.nodes:
            return {}
        
        velocities = [node.change_velocity_30d for node in self.nodes.values()]
        
        return {
            "total_changes_30d": sum(velocities),
            "avg_changes_per_file": sum(velocities) / len(velocities),
            "max_changes": max(velocities),
            "files_with_changes": sum(1 for v in velocities if v > 0),
            "stale_files": sum(1 for v in velocities if v == 0)
        }
    
    def save_graph(self, output_path: Optional[Path] = None):
        """Serialize NetworkX graph to JSON with metadata."""
        if output_path is None:
            output_path = self.cache_dir / "module_graph.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use node_link_data for serialization
        graph_data = nx.node_link_data(self.graph)
        
        # Add metadata
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "repo_path": str(self.repo_path),
                "stats": self.stats,
                "velocity_summary": self.get_change_velocity_summary()
            },
            "graph": graph_data,
            "nodes": {
                path: node.model_dump() 
                for path, node in self.nodes.items()
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        logger.info(f"💾 Graph saved to {output_path}")
    
    def save_dead_code_report(self, output_path: Optional[Path] = None):
        """Generate a detailed dead code report."""
        if output_path is None:
            output_path = self.cache_dir / "dead_code_candidates.md"
        
        dead_candidates = self.identify_dead_code()
        
        with open(output_path, 'w') as f:
            f.write("# Dead Code Analysis Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("## Summary\n")
            f.write(f"- Total modules analyzed: {len(self.nodes)}\n")
            f.write(f"- Dead code candidates: {len(dead_candidates)}\n\n")
            
            if dead_candidates:
                f.write("## Candidates\n\n")
                for path, signals in dead_candidates:
                    f.write(f"### {path}\n")
                    f.write(f"- In-degree (imported by): {signals['in_degree']}\n")
                    f.write(f"- Out-degree (imports): {signals['out_degree']}\n")
                    f.write(f"- Changes (30d): {signals['recent_changes']}\n")
                    f.write(f"- Total commits: {signals['total_changes']}\n")
                    f.write("\n")
        
        logger.info(f"💾 Dead code report saved to {output_path}")
    
    def _print_scan_summary(self):
        """Print a formatted summary of the scan."""
        logger.info("\n" + "="*50)
        logger.info("📊 Surveyor Scan Complete")
        logger.info("="*50)
        logger.info(f"Files scanned: {self.stats['files_scanned']}")
        logger.info(f"  ├─ Python: {self.stats['python_files']}")
        logger.info(f"  ├─ SQL:    {self.stats['sql_files']}")
        logger.info(f"  ├─ YAML:   {self.stats['yaml_files']}")
        logger.info(f"  ├─ Jupyter: {self.stats['jupyter_files']}")
        logger.info(f"  └─ Other:  {self.stats['other_files']}")
        
        if self.stats['python_files'] > 0:
            logger.info(f"\nPython modules in graph: {len(self.graph.nodes())}")
            logger.info(f"Import relationships: {self.stats['edges_added']}")
        
        velocity = self.get_change_velocity_summary()
        if velocity:
            logger.info(f"\nChange velocity (30d):")
            logger.info(f"  ├─ Total changes: {velocity.get('total_changes_30d', 0)}")
            logger.info(f"  ├─ Active files:  {velocity.get('files_with_changes', 0)}")
            logger.info(f"  └─ Stale files:   {velocity.get('stale_files', 0)}")
        
        logger.info("="*50 + "\n")
    
    def run(self) -> nx.DiGraph:
        """Execute the full surveyor pipeline."""
        self.scan_repository()
        
        if len(self.nodes) == 0:
            logger.warning("⚠️ No Python modules found. This is normal for dbt/SQL-heavy projects.")
            logger.warning("   The Hydrologist agent (Phase 2) will analyze SQL files for lineage.")
        else:
            self.build_import_graph()
            
            # Generate insights
            critical = self.identify_critical_path()
            dead = self.identify_dead_code()
            
            logger.info(f"\n🔍 Key Insights:")
            logger.info(f"  ├─ Critical modules (top {len(critical)}):")
            for node, score in critical[:3]:  # Show top 3
                logger.info(f"  │   └─ {node} (PageRank: {score:.3f})")
            
            if dead:
                logger.info(f"  └─ Dead code candidates: {len(dead)}")
        
        return self.graph