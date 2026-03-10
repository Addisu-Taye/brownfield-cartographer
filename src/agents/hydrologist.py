"""Agent 2: The Hydrologist - Data Flow & Lineage Analyst

Constructs the data lineage DAG by analyzing data sources, transformations, 
and sinks across all languages in the repo.
"""

import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import json
from datetime import datetime
import logging
import re

# Try to import sqlglot, but don't fail if not installed
try:
    import sqlglot
    from sqlglot import parse_one, exp
    from sqlglot.optimizer import qualify_tables
    SQLGLOT_AVAILABLE = True
except ImportError:
    SQLGLOT_AVAILABLE = False
    logging.warning("sqlglot not installed. SQL parsing will use fallback regex mode.")

# Import models
from src.models.nodes import DatasetNode, TransformationNode, EdgeType, KnowledgeGraph

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DbtSQLPreProcessor:
    """Pre-process dbt SQL files to replace ref() and source() with actual table names."""
    
    def pre_process(self, content: str) -> str:
        """Replace dbt ref() and source() calls with table names for parsing."""
        
        # Replace {{ ref('model_name') }} with the model name
        def replace_ref(match):
            ref_name = match.group(1)
            return ref_name
        
        # Replace {{ source('source_name', 'table_name') }} with source_table
        def replace_source(match):
            source_name = match.group(1)
            table_name = match.group(2)
            return f"{source_name}_{table_name}"
        
        # Handle {{ ref('name') }} with double curly braces
        content = re.sub(
            r"\{\{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}", 
            replace_ref, 
            content, 
            flags=re.IGNORECASE
        )
        
        # Handle {{ source('source', 'table') }} with double curly braces
        content = re.sub(
            r"\{\{\s*source\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}", 
            replace_source, 
            content, 
            flags=re.IGNORECASE
        )
        
        # Also handle cases with comments inside (like in stg_customers.sql)
        content = re.sub(
            r"\{\#.*?\#\}", 
            "", 
            content, 
            flags=re.IGNORECASE | re.DOTALL
        )
        
        return content


class PythonDataFlowAnalyzer:
    """Analyzes Python files for data operations (pandas, spark, SQLAlchemy)."""
    
    def __init__(self):
        self.data_patterns = {
            'pandas_read': ['read_csv', 'read_sql', 'read_parquet', 'read_json', 'read_excel'],
            'pandas_write': ['to_csv', 'to_sql', 'to_parquet', 'to_json', 'to_excel'],
            'spark_read': ['spark.read.csv', 'spark.read.parquet', 'spark.read.json', 'spark.read.table', 'spark.read.jdbc'],
            'spark_write': ['write.csv', 'write.parquet', 'write.json', 'write.table', 'write.jdbc'],
            'sqlalchemy': ['create_engine', 'session.execute', 'pd.read_sql'],
            'airflow': ['SQLExecuteQueryOperator', 'BigQueryOperator', 'PythonOperator']
        }
    
    def analyze_file(self, file_path: Path, content: str) -> List[Dict[str, Any]]:
        """Extract data flow operations from Python file."""
        operations = []
        
        try:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # Check for pandas read operations
                for pattern in self.data_patterns['pandas_read']:
                    if pattern in line_lower:
                        operations.append({
                            'type': 'read',
                            'framework': 'pandas',
                            'operation': pattern,
                            'line': i + 1,
                            'source': self._extract_dataset_name(line, pattern),
                            'file': str(file_path)
                        })
                
                # Check for pandas write operations
                for pattern in self.data_patterns['pandas_write']:
                    if pattern in line_lower:
                        operations.append({
                            'type': 'write',
                            'framework': 'pandas',
                            'operation': pattern,
                            'line': i + 1,
                            'target': self._extract_dataset_name(line, pattern),
                            'file': str(file_path)
                        })
                
                # Check for spark operations
                for pattern in self.data_patterns['spark_read']:
                    if pattern in line_lower:
                        operations.append({
                            'type': 'read',
                            'framework': 'spark',
                            'operation': pattern,
                            'line': i + 1,
                            'source': self._extract_dataset_name(line, pattern),
                            'file': str(file_path)
                        })
                
                for pattern in self.data_patterns['spark_write']:
                    if pattern in line_lower:
                        operations.append({
                            'type': 'write',
                            'framework': 'spark',
                            'operation': pattern,
                            'line': i + 1,
                            'target': self._extract_dataset_name(line, pattern),
                            'file': str(file_path)
                        })
        
        except Exception as e:
            logger.error(f"Error analyzing Python file {file_path}: {e}")
        
        return operations
    
    def _extract_dataset_name(self, line: str, pattern: str) -> str:
        """Extract dataset name from a line of code (simple heuristic)."""
        try:
            # Look for string literals in parentheses
            if '(' in line and ')' in line:
                content = line[line.find('(')+1:line.rfind(')')]
                # Look for quoted strings
                quotes = re.findall(r'[\'"]([^\'"]*)[\'"]', content)
                if quotes:
                    return quotes[0]
        except:
            pass
        return "unknown"


class SQLLineageAnalyzer:
    """Analyzes SQL files for table dependencies using sqlglot."""
    
    def __init__(self, dialect: str = "postgres"):
        self.dialect = dialect
        self.supported_dialects = [
            "postgres", "mysql", "sqlite", "bigquery", "snowflake", 
            "redshift", "spark", "duckdb", "clickhouse"
        ]
        self.pre_processor = DbtSQLPreProcessor()
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract table lineage from SQL file."""
        result = {
            'file': str(file_path),
            'tables_read': [],
            'tables_written': [],
            'ctes': [],
            'dialect': self.dialect,
            'queries': []
        }
        
        # First, extract CTE names from the original content
        cte_names = self._extract_cte_names(content)
        result['ctes'] = [{'name': cte, 'tables': []} for cte in cte_names]
        
        # Pre-process dbt content - replace {{ ref('...') }} with actual table names
        processed_content = self.pre_processor.pre_process(content)
        
        if not SQLGLOT_AVAILABLE:
            # Use fallback if sqlglot not installed
            self._fallback_extraction(processed_content, result, cte_names)
            return result
        
        try:
            # Try to parse SQL with the pre-processed content
            parsed = parse_one(processed_content, dialect=self.dialect)
            
            # Find all tables in the query, excluding CTEs
            for table in parsed.find_all(exp.Table):
                if table.name and not table.name.startswith('_'):
                    # Check if this is a CTE
                    if table.name in cte_names:
                        continue  # Skip CTEs
                    
                    # Get the full table name
                    table_name = table.name
                    if table.db:
                        table_name = f"{table.db}.{table_name}"
                    if table.catalog:
                        table_name = f"{table.catalog}.{table_name}"
                    
                    # Clean up any remaining quotes
                    table_name = table_name.strip('"').strip("'").strip('`')
                    
                    # Determine if this is a read or write
                    # Check if this table is being created
                    parent = table.parent
                    is_write = False
                    while parent:
                        if isinstance(parent, exp.Create) or isinstance(parent, exp.Insert):
                            is_write = True
                            break
                        parent = parent.parent
                    
                    if is_write:
                        if table_name not in result['tables_written']:
                            result['tables_written'].append(table_name)
                    else:
                        if table_name not in result['tables_read']:
                            result['tables_read'].append(table_name)
            
            # Also look for table references in CREATE statements
            for create in parsed.find_all(exp.Create):
                # This is a write operation
                if create.this and hasattr(create.this, 'name'):
                    table_name = create.this.name
                    if table_name and table_name not in result['tables_written']:
                        result['tables_written'].append(table_name)
            
            # Look for INSERT statements
            for insert in parsed.find_all(exp.Insert):
                if insert.this and hasattr(insert.this, 'name'):
                    table_name = insert.this.name
                    if table_name and table_name not in result['tables_written']:
                        result['tables_written'].append(table_name)
            
            # Log what we found for debugging
            if result['tables_read'] or result['tables_written']:
                logger.debug(f"Found tables in {file_path.name}: read={result['tables_read']}, write={result['tables_written']}")
            
        except Exception as e:
            logger.debug(f"sqlglot parsing failed for {file_path}: {e}")
            # Fallback to simple regex-based extraction
            self._fallback_extraction(processed_content, result, cte_names)
        
        return result
    
    def _extract_cte_names(self, content: str) -> List[str]:
        """Extract CTE names from SQL content."""
        cte_names = []
        
        # Look for WITH clause CTEs
        with_pattern = r"with\s+(\w+)\s+as\s*\("
        with_matches = re.findall(with_pattern, content, re.IGNORECASE)
        cte_names.extend(with_matches)
        
        # Look for comma-separated CTEs
        cte_pattern = r",\s*(\w+)\s+as\s*\("
        cte_matches = re.findall(cte_pattern, content, re.IGNORECASE)
        cte_names.extend(cte_matches)
        
        return list(set(cte_names))
    
    def _fallback_extraction(self, content: str, result: Dict, cte_names: List[str]):
        """Fallback method using regex when sqlglot fails."""
        
        # First, remove CTE definitions to avoid confusion
        content_without_ctes = content
        for cte in cte_names:
            # Remove the CTE definition
            pattern = rf"{cte}\s+as\s*\(.*?\)"
            content_without_ctes = re.sub(pattern, "", content_without_ctes, flags=re.IGNORECASE | re.DOTALL)
        
        # Look for CREATE TABLE statements
        create_pattern = r"create\s+table\s+(?:if\s+not\s+exists\s+)?([`'\"\[]?[\w.]+[`'\"\]]?)"
        create_matches = re.findall(create_pattern, content, re.IGNORECASE)
        for match in create_matches:
            clean_name = match.strip('`').strip("'").strip('"').strip('[]')
            if clean_name not in result['tables_written'] and clean_name not in cte_names:
                result['tables_written'].append(clean_name)
        
        # Look for INSERT INTO statements
        insert_pattern = r"insert\s+into\s+([`'\"\[]?[\w.]+[`'\"\]]?)"
        insert_matches = re.findall(insert_pattern, content, re.IGNORECASE)
        for match in insert_matches:
            clean_name = match.strip('`').strip("'").strip('"').strip('[]')
            if clean_name not in result['tables_written'] and clean_name not in cte_names:
                result['tables_written'].append(clean_name)
        
        # Look for FROM clauses (excluding CTEs)
        from_pattern = r"from\s+([`'\"\[]?[\w.]+[`'\"\]]?)"
        from_matches = re.findall(from_pattern, content_without_ctes, re.IGNORECASE)
        for match in from_matches:
            clean_name = match.strip('`').strip("'").strip('"').strip('[]')
            if (clean_name not in result['tables_read'] and 
                clean_name not in result['tables_written'] and 
                clean_name not in cte_names):
                result['tables_read'].append(clean_name)
        
        # Look for JOIN clauses (excluding CTEs)
        join_pattern = r"join\s+([`'\"\[]?[\w.]+[`'\"\]]?)"
        join_matches = re.findall(join_pattern, content_without_ctes, re.IGNORECASE)
        for match in join_matches:
            clean_name = match.strip('`').strip("'").strip('"').strip('[]')
            if (clean_name not in result['tables_read'] and 
                clean_name not in result['tables_written'] and 
                clean_name not in cte_names):
                result['tables_read'].append(clean_name)
        
        # Remove duplicates
        result['tables_read'] = list(set(result['tables_read']))
        result['tables_written'] = list(set(result['tables_written']))


class DAGConfigAnalyzer:
    """Analyzes YAML config files for dbt and Airflow DAG definitions."""
    
    def __init__(self):
        self.dbt_patterns = ['sources.yml', 'schema.yml', 'dbt_project.yml']
        self.airflow_patterns = ['dag', 'DAG', 'airflow']
    
    def analyze_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract DAG structure from YAML config files."""
        result = {
            'file': str(file_path),
            'type': 'unknown',
            'sources': [],
            'models': [],
            'tests': [],
            'dependencies': []
        }
        
        try:
            import yaml
            data = yaml.safe_load(content)
            
            if not data:
                return result
            
            filename = file_path.name.lower()
            
            # dbt sources.yml
            if 'sources.yml' in filename and 'sources' in data:
                result['type'] = 'dbt_sources'
                for source in data.get('sources', []):
                    source_name = source.get('name', '')
                    for table in source.get('tables', []):
                        result['sources'].append({
                            'source': source_name,
                            'table': table.get('name', ''),
                            'columns': table.get('columns', [])
                        })
            
            # dbt schema.yml
            elif 'schema.yml' in filename and 'models' in data:
                result['type'] = 'dbt_schema'
                for model in data.get('models', []):
                    model_name = model.get('name', '')
                    result['models'].append({
                        'name': model_name,
                        'description': model.get('description', ''),
                        'columns': model.get('columns', [])
                    })
                    # Add tests
                    for column in model.get('columns', []):
                        if 'tests' in column:
                            result['tests'].extend(column['tests'])
            
            # dbt_project.yml
            elif 'dbt_project.yml' in filename:
                result['type'] = 'dbt_project'
                result['models'] = data.get('models', {})
                result['seeds'] = data.get('seeds', {})
                result['vars'] = data.get('vars', {})
            
        except Exception as e:
            logger.debug(f"YAML parsing failed for {file_path}: {e}")
        
        return result


class Hydrologist:
    """Agent 2: Data Flow & Lineage Analyst
    
    Constructs the data lineage DAG by analyzing data sources, transformations,
    and sinks across all languages.
    """
    
    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize analyzers
        self.python_analyzer = PythonDataFlowAnalyzer()
        self.sql_analyzer = SQLLineageAnalyzer(dialect="postgres")  # Will auto-detect
        self.config_analyzer = DAGConfigAnalyzer()
        
        # Graph for lineage
        self.lineage_graph = nx.DiGraph()
        
        # Node storage
        self.datasets: Dict[str, Dict] = {}
        self.transformations: Dict[str, Dict] = {}
        
        # Statistics
        self.stats = {
            "files_analyzed": 0,
            "sql_files": 0,
            "python_files": 0,
            "yaml_files": 0,
            "datasets_found": 0,
            "transformations_found": 0,
            "edges_added": 0
        }
    
    def detect_sql_dialect(self, file_path: Path) -> str:
        """Attempt to detect SQL dialect from file content or path."""
        path_str = str(file_path).lower()
        
        dialect_map = {
            'bigquery': 'bigquery',
            'bq': 'bigquery',
            'snowflake': 'snowflake',
            'redshift': 'redshift',
            'spark': 'spark',
            'postgres': 'postgres',
            'mysql': 'mysql',
            'duckdb': 'duckdb'
        }
        
        for key, dialect in dialect_map.items():
            if key in path_str:
                return dialect
        
        return 'postgres'  # Default
    
    def scan_for_lineage(self) -> nx.DiGraph:
        """Scan the repository and build lineage graph."""
        logger.info("💧 Hydrologist: Scanning for data lineage...")
        
        # Track all files by language
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Skip unwanted directories
            if any(part in str(file_path) for part in [".venv", ".git", "__pycache__", ".cartography"]):
                continue
            
            suffix = file_path.suffix.lower()
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Route to appropriate analyzer
                if suffix == '.sql':
                    self._analyze_sql_file(file_path, content)
                    self.stats["sql_files"] += 1
                    self.stats["files_analyzed"] += 1
                
                elif suffix == '.py':
                    self._analyze_python_file(file_path, content)
                    self.stats["python_files"] += 1
                    self.stats["files_analyzed"] += 1
                
                elif suffix in ('.yml', '.yaml'):
                    self._analyze_yaml_file(file_path, content)
                    self.stats["yaml_files"] += 1
                    self.stats["files_analyzed"] += 1
                
            except Exception as e:
                logger.debug(f"Error reading {file_path}: {e}")
                continue
        
        # Build graph from collected data
        self._build_lineage_graph()
        
        # Print summary
        self._print_summary()
        
        return self.lineage_graph
    
    def _analyze_sql_file(self, file_path: Path, content: str):
        """Analyze SQL file for lineage."""
        # Detect dialect
        dialect = self.detect_sql_dialect(file_path)
        self.sql_analyzer.dialect = dialect
        
        # Analyze
        result = self.sql_analyzer.analyze_file(file_path, content)
        
        # Create transformation node
        rel_path = file_path.relative_to(self.repo_path)
        trans_id = f"sql:{rel_path}"
        
        # Store in transformations dict for later graph building
        self.transformations[trans_id] = {
            'id': trans_id,
            'type': 'sql',
            'file': str(rel_path),
            'reads': result['tables_read'],
            'writes': result['tables_written'],
            'ctes': result['ctes']
        }
        
        # Create dataset nodes for tables
        for table in result['tables_read'] + result['tables_written']:
            if table and table not in self.datasets:
                self.datasets[table] = {
                    'name': table,
                    'type': 'table',
                    'files': []
                }
            if table and str(file_path) not in self.datasets[table]['files']:
                self.datasets[table]['files'].append(str(file_path))
    
    def _analyze_python_file(self, file_path: Path, content: str):
        """Analyze Python file for data operations."""
        operations = self.python_analyzer.analyze_file(file_path, content)
        
        if not operations:
            return
        
        trans_id = f"python:{file_path.relative_to(self.repo_path)}"
        reads = []
        writes = []
        
        for op in operations:
            if op['type'] == 'read' and 'source' in op:
                reads.append(op['source'])
                # Create dataset if not exists
                if op['source'] not in self.datasets:
                    self.datasets[op['source']] = {
                        'name': op['source'],
                        'type': 'file',
                        'files': [str(file_path)]
                    }
            elif op['type'] == 'write' and 'target' in op:
                writes.append(op['target'])
                if op['target'] not in self.datasets:
                    self.datasets[op['target']] = {
                        'name': op['target'],
                        'type': 'file',
                        'files': [str(file_path)]
                    }
        
        if reads or writes:
            self.transformations[trans_id] = {
                'id': trans_id,
                'type': 'python',
                'file': str(file_path.relative_to(self.repo_path)),
                'reads': reads,
                'writes': writes,
                'operations': operations
            }
    
    def _analyze_yaml_file(self, file_path: Path, content: str):
        """Analyze YAML config file for DAG structure."""
        result = self.config_analyzer.analyze_file(file_path, content)
        
        if result['type'] == 'unknown' or not (result['sources'] or result['models']):
            return
        
        config_id = f"config:{file_path.relative_to(self.repo_path)}"
        
        # Extract sources (datasets)
        for source in result.get('sources', []):
            table_name = f"{source['source']}.{source['table']}"
            if table_name not in self.datasets:
                self.datasets[table_name] = {
                    'name': table_name,
                    'type': 'source',
                    'files': [str(file_path)],
                    'metadata': source
                }
        
        # Extract models (transformations)
        for model in result.get('models', []):
            model_name = model['name']
            if model_name not in self.transformations:
                self.transformations[model_name] = {
                    'id': model_name,
                    'type': 'dbt_model',
                    'file': str(file_path.relative_to(self.repo_path)),
                    'reads': [],  # Will be filled from SQL analysis
                    'writes': [model_name],
                    'metadata': model
                }
    
    def _build_lineage_graph(self):
        """Build the lineage graph from collected data."""
        logger.info("🔗 Building lineage graph...")
        
        # Add dataset nodes
        for dataset_name, dataset_info in self.datasets.items():
            node_id = f"dataset:{dataset_name}"
            self.lineage_graph.add_node(
                node_id,
                type='dataset',
                name=dataset_name,
                dataset_type=dataset_info.get('type', 'unknown'),
                files=dataset_info.get('files', [])
            )
            self.stats["datasets_found"] += 1
        
        # Add transformation nodes and edges
        for trans_id, trans_info in self.transformations.items():
            node_id = f"trans:{trans_id}"
            self.lineage_graph.add_node(
                node_id,
                type='transformation',
                name=trans_id,
                trans_type=trans_info['type'],
                file=trans_info['file']
            )
            self.stats["transformations_found"] += 1
            
            # Add edges from datasets to transformation (CONSUMES)
            for read in trans_info.get('reads', []):
                if read in self.datasets:
                    self.lineage_graph.add_edge(
                        f"dataset:{read}",
                        node_id,
                        type=EdgeType.CONSUMES
                    )
                    self.stats["edges_added"] += 1
            
            # Add edges from transformation to datasets (PRODUCES)
            for write in trans_info.get('writes', []):
                if write in self.datasets:
                    self.lineage_graph.add_edge(
                        node_id,
                        f"dataset:{write}",
                        type=EdgeType.PRODUCES
                    )
                    self.stats["edges_added"] += 1
    
    def trace_lineage(self, dataset_name: str, direction: str = "upstream") -> List[str]:
        """Trace lineage upstream or downstream from a dataset."""
        node_id = f"dataset:{dataset_name}"
        
        if node_id not in self.lineage_graph:
            return []
        
        if direction == "upstream":
            # Find all nodes that eventually feed into this dataset
            ancestors = nx.ancestors(self.lineage_graph, node_id)
            return [n for n in ancestors if n.startswith("dataset:")]
        else:
            # Find all nodes that depend on this dataset
            descendants = nx.descendants(self.lineage_graph, node_id)
            return [n for n in descendants if n.startswith("dataset:")]
    
    def blast_radius(self, dataset_name: str) -> Dict[str, List[str]]:
        """Calculate blast radius if a dataset changes."""
        node_id = f"dataset:{dataset_name}"
        
        if node_id not in self.lineage_graph:
            return {"upstream": [], "downstream": []}
        
        # Upstream: what feeds into this (would break if they change)
        upstream = [n for n in nx.ancestors(self.lineage_graph, node_id) 
                   if n.startswith("dataset:")]
        
        # Downstream: what depends on this (would break if this changes)
        downstream = [n for n in nx.descendants(self.lineage_graph, node_id) 
                     if n.startswith("dataset:")]
        
        return {
            "upstream": upstream,
            "downstream": downstream
        }
    
    def find_sources(self) -> List[str]:
        """Find source datasets (in-degree = 0 in lineage graph)."""
        sources = []
        for node in self.lineage_graph.nodes():
            if node.startswith("dataset:"):
                if self.lineage_graph.in_degree(node) == 0:
                    sources.append(node.replace("dataset:", ""))
        return sources
    
    def find_sinks(self) -> List[str]:
        """Find sink datasets (out-degree = 0 in lineage graph)."""
        sinks = []
        for node in self.lineage_graph.nodes():
            if node.startswith("dataset:"):
                if self.lineage_graph.out_degree(node) == 0:
                    sinks.append(node.replace("dataset:", ""))
        return sinks
    
    def save_lineage_graph(self, output_path: Optional[Path] = None):
        """Save lineage graph to JSON."""
        if output_path is None:
            output_path = self.cache_dir / "lineage_graph.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert NetworkX graph to serializable format
        graph_data = nx.node_link_data(self.lineage_graph)
        
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "repo_path": str(self.repo_path),
                "stats": self.stats
            },
            "graph": graph_data,
            "datasets": self.datasets,
            "transformations": self.transformations
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        logger.info(f"💾 Lineage graph saved to {output_path}")
    
    def _print_summary(self):
        """Print analysis summary."""
        logger.info("\n" + "="*50)
        logger.info("💧 Hydrologist Scan Complete")
        logger.info("="*50)
        logger.info(f"Files analyzed: {self.stats['files_analyzed']}")
        logger.info(f"  ├─ SQL:    {self.stats['sql_files']}")
        logger.info(f"  ├─ Python: {self.stats['python_files']}")
        logger.info(f"  └─ YAML:   {self.stats['yaml_files']}")
        logger.info(f"\nDatasets found: {self.stats['datasets_found']}")
        logger.info(f"Transformations: {self.stats['transformations_found']}")
        logger.info(f"Lineage edges: {self.stats['edges_added']}")
        
        # Show sources and sinks
        sources = self.find_sources()
        sinks = self.find_sinks()
        if sources:
            logger.info(f"\n📤 Source datasets (ingestion points):")
            for s in sources[:5]:  # Show first 5
                logger.info(f"  └─ {s}")
        if sinks:
            logger.info(f"\n📥 Sink datasets (outputs):")
            for s in sinks[:5]:  # Show first 5
                logger.info(f"  └─ {s}")
        
        logger.info("="*50 + "\n")
    
    def run(self) -> nx.DiGraph:
        """Execute the full hydrologist pipeline."""
        return self.scan_for_lineage()