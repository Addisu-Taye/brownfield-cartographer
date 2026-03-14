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
    """Agent 1: Static Structure Analyst"""
    
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
            if language == "python":
                self.stats["python_files"] += 1
                self._analyze_python_file(file_path)
            elif language == "sql":
                self.stats["sql_files"] += 1
                self._analyze_sql_file(file_path)
            elif language == "yaml":
                self.stats["yaml_files"] += 1
                self._analyze_yaml_file(file_path)
            elif language == "jupyter":
                self.stats["jupyter_files"] += 1
            else:
                self.stats["other_files"] += 1
        
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
    
    def _analyze_sql_file(self, file_path: Path):
        """Analyze a SQL file and add to graph."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            from src.models.nodes import NodeType
            
            node = ModuleNode(
                path=str(file_path.relative_to(self.repo_path)),
                language="sql",
                type=NodeType.MODULE,  # Add this line
                complexity_score=len(lines) / 20,
                metadata={"line_count": len(lines)}
            )
            
            # Add git velocity data
            velocity = self.extract_git_velocity(file_path)
            node.change_velocity_30d = velocity["30d"]
            node.change_velocity_90d = velocity["90d"]
            node.total_commits = velocity["total"]
            
            # Add relative path
            rel_path = str(file_path.relative_to(self.repo_path))
            node.path = rel_path
            
            # Store node
            self.nodes[rel_path] = node
            self.graph.add_node(
                rel_path,
                **{k: v for k, v in node.model_dump().items() if v is not None}
            )
        except Exception as e:
            logger.error(f"Error analyzing SQL file {file_path}: {e}")

    def _analyze_yaml_file(self, file_path: Path):
        """Analyze a YAML file and add to graph."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            from src.models.nodes import NodeType
            
            node = ModuleNode(
                path=str(file_path.relative_to(self.repo_path)),
                language="yaml",
                type=NodeType.MODULE,  # Add this line
                complexity_score=len(lines) / 20,
                metadata={"line_count": len(lines)}
            )
            
            # Add git velocity data
            velocity = self.extract_git_velocity(file_path)
            node.change_velocity_30d = velocity["30d"]
            node.change_velocity_90d = velocity["90d"]
            node.total_commits = velocity["total"]
            
            # Add relative path
            rel_path = str(file_path.relative_to(self.repo_path))
            node.path = rel_path
            
            # Store node
            self.nodes[rel_path] = node
            self.graph.add_node(
                rel_path,
                **{k: v for k, v in node.model_dump().items() if v is not None}
            )
        except Exception as e:
            logger.error(f"Error analyzing YAML file {file_path}: {e}")
    
    
    def build_import_graph(self):
        """Build import graph (only for Python files)."""
        logger.info("🔗 Building import graph...")
        # This method is only relevant for Python files
        pass
    
    def identify_critical_path(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """Identify critical modules (not applicable for SQL-only repos)."""
        return []
    
    def identify_dead_code(self) -> List[Tuple[str, Dict]]:
        """Identify dead code candidates."""
        dead_candidates = []
        
        for node_path, node in self.nodes.items():
            # Skip entry points and test files
            if node.is_entry_point or node.is_test:
                continue
            
            signals = {
                "in_degree": self.graph.in_degree(node_path),
                "out_degree": self.graph.out_degree(node_path),
                "recent_changes": node.change_velocity_30d,
                "total_changes": node.total_commits,
                "import_count": node.import_count
            }
            
            # Dead code signals for SQL/YAML files
            if signals["recent_changes"] == 0 and signals["total_changes"] < 3:
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
            "avg_changes_per_file": sum(velocities) / len(velocities) if velocities else 0,
            "max_changes": max(velocities) if velocities else 0,
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
                    f.write(f"- Changes (30d): {signals['recent_changes']}\n")
                    f.write(f"- Total commits: {signals['total_changes']}\n\n")
        
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
        
        velocity = self.get_change_velocity_summary()
        if velocity:
            logger.info(f"\nChange velocity (30d):")
            logger.info(f"  ├─ Total changes: {velocity.get('total_changes_30d', 0)}")
            logger.info(f"  ├─ Active files:  {velocity.get('files_with_changes', 0)}")
            logger.info(f"  └─ Stale files:   {velocity.get('stale_files', 0)}")
        
        logger.info("="*50 + "\n")
    
    def run(self) -> nx.DiGraph:
        """Execute the full surveyor pipeline.
        
        This method is called by the orchestrator to run Phase 1.
        It scans the repository and returns the module graph.
        """
        logger.info("🚀 Running Surveyor agent...")
        try:
            # Call the existing scan_repository method
            self.scan_repository()
            logger.info(f"✅ Surveyor complete. Found {len(self.nodes)} modules")
            return self.graph
        except Exception as e:
            logger.error(f"❌ Surveyor failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return self.graph