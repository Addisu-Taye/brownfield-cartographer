import tree_sitter_python as tspython
import tree_sitter_sql as tssql
import tree_sitter_yaml as tsyaml
from tree_sitter import Language, Parser, Node
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from src.models.nodes import ModuleNode
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TreeSitterAnalyzer:
    """Multi-language AST parser using individual tree-sitter grammars.
    
    Compatible with tree-sitter>=0.23.0 API.
    Enhanced with better error handling, caching, and deeper AST traversal.
    """
    
    # Class-level cache to avoid re-parsing files
    _ast_cache: Dict[Path, Tuple[Node, bytes]] = {}
    
    def __init__(self, cache_size: int = 100):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}
        self.cache_size = cache_size
        
        # Initialize languages and parsers
        self._init_language("python", tspython)
        self._init_language("sql", tssql)
        self._init_language("yaml", tsyaml)
        
        # Compile queries once
        self._compile_queries()
    
    def _init_language(self, name: str, grammar_module):
        """Initialize parser and language for a given grammar.
        
        tree-sitter>=0.23.0 API: parser.language = Language(...)
        """
        try:
            self.languages[name] = Language(grammar_module.language())
            self.parsers[name] = Parser()
            self.parsers[name].language = self.languages[name]
            logger.debug(f"Initialized {name} parser")
        except Exception as e:
            logger.error(f"Failed to initialize {name} parser: {e}")
            self.parsers[name] = None
    
    def _compile_queries(self):
        """Pre-compile tree-sitter queries for efficiency.
        
        Note: SQL lineage is handled by sqlglot in the Hydrologist agent (Phase 2).
        This analyzer focuses on Python module structure for the Surveyor (Phase 1).
        """
        # Python queries - Enhanced for deeper analysis
        if "python" in self.languages:
            # Import statements with aliases
            self.python_import_query = self.languages["python"].query("""
                (import_statement
                    (dotted_name) @import)
                (import_from_statement
                    module_name: (dotted_name) @module
                    name: (dotted_name) @import_name)
                (aliased_import
                    (dotted_name) @original_name
                    (identifier) @alias)
            """)
            
            # Function definitions with decorators and docstrings
            self.python_function_query = self.languages["python"].query("""
                (function_definition
                    name: (identifier) @name
                    parameters: (parameters) @params
                    body: (block) @body)
                (decorated_definition
                    (decorator) @decorator
                    (function_definition) @decorated_func)
            """)
            
            # Class definitions with inheritance
            self.python_class_query = self.languages["python"].query("""
                (class_definition
                    name: (identifier) @name
                    superclasses: (argument_list) @bases)
            """)
            
            # Call expressions for function calls
            self.python_call_query = self.languages["python"].query("""
                (call
                    function: (attribute) @method_call
                    arguments: (argument_list) @args)
                (call
                    function: (identifier) @function_call)
            """)
            
            # String literals (for detecting pandas read_csv, etc.)
            self.python_string_query = self.languages["python"].query("""
                (string) @string
            """)
        
        # SQL queries - Temporarily simplified for Phase 1
        # Full SQL lineage will be handled by sqlglot in Hydrologist agent (Phase 2)
        self.sql_table_query = None
        
        # YAML queries - Basic structure
        if "yaml" in self.languages:
            self.yaml_block_query = self.languages["yaml"].query("""
                (block_mapping_pair
                    key: (flow_node) @key
                    value: (flow_node) @value)
            """)
    
    def get_language_for_file(self, file_path: Path) -> str:
        """Determine language from file extension."""
        suffix = file_path.suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.sql': 'sql',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.ipynb': 'jupyter',  # Will need special handling
            '.md': 'markdown',
            '.csv': 'csv',
            '.json': 'json'
        }
        
        return language_map.get(suffix, 'unknown')
    
    def parse_file(self, file_path: Path) -> Optional[Node]:
        """Parse a file and return the AST root node with caching."""
        # Check cache
        if file_path in self._ast_cache:
            return self._ast_cache[file_path][0]
        
        language = self.get_language_for_file(file_path)
        if language not in self.parsers or self.parsers[language] is None:
            logger.warning(f"No parser available for {language}")
            return None
        
        parser = self.parsers[language]
        
        try:
            with open(file_path, "rb") as f:
                source_code = f.read()
            
            tree = parser.parse(source_code)
            
            # Manage cache size
            if len(self._ast_cache) >= self.cache_size:
                # Remove oldest item
                oldest = next(iter(self._ast_cache))
                del self._ast_cache[oldest]
            
            self._ast_cache[file_path] = (tree.root_node, source_code)
            return tree.root_node
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None
    
    def analyze_file(self, file_path: Path) -> ModuleNode:
        """Extract structural metadata from a file based on its language."""
        language = self.get_language_for_file(file_path)
        
        # Route to appropriate analyzer
        analyzers = {
            "python": self.analyze_python_file,
            "sql": self.analyze_sql_file,
            "yaml": self.analyze_yaml_file,
            "jupyter": self.analyze_jupyter_file
        }
        
        analyzer = analyzers.get(language, self.analyze_unknown_file)
        
        try:
            return analyzer(file_path)
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return ModuleNode(
                path=str(file_path),
                language=language,
                imports=[],
                public_functions=[],
                classes=[],
                complexity_score=0,
                purpose_statement=f"Error during analysis: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def analyze_python_file(self, file_path: Path) -> ModuleNode:
        """Extract structural metadata from a Python file."""
        root_node = self.parse_file(file_path)
        if not root_node:
            return ModuleNode(path=str(file_path), language="python")
        
        with open(file_path, "rb") as f:
            source_code = f.read()
        
        # Extract imports
        imports = self._extract_python_imports(root_node)
        
        # Extract public functions with signatures
        functions = self._extract_python_functions(root_node)
        
        # Extract classes
        classes = self._extract_python_classes(root_node)
        
        # Detect data engineering patterns (pandas, spark, etc.)
        data_patterns = self._detect_data_patterns(root_node, source_code)
        
        # Calculate complexity
        complexity = self._calculate_complexity(root_node, source_code)
        
        # Extract docstring if present
        docstring = self._extract_docstring(root_node, source_code)
        
        # Count lines
        lines = len(source_code.decode('utf8').splitlines())
        
        return ModuleNode(
            path=str(file_path),
            language="python",
            imports=list(set(imports)),
            public_functions=functions,
            classes=classes,
            complexity_score=complexity,
            purpose_statement="",  # Will be filled by Semanticist
            docstring=docstring,
            metadata={
                "data_patterns": data_patterns,
                "line_count": lines
            }
        )
    
    def _extract_python_imports(self, root_node: Node) -> List[str]:
        """Extract all imports from Python AST."""
        imports = []
        
        try:
            captures = self.python_import_query.captures(root_node)
            for capture, capture_name in captures:
                if capture_name == "import":
                    imports.append(capture.text.decode('utf8'))
                elif capture_name == "module":
                    # Handle from X import Y
                    module = capture.text.decode('utf8')
                    imports.append(module)
                elif capture_name == "original_name":
                    original = capture.text.decode('utf8')
                    imports.append(original)
        except Exception as e:
            logger.debug(f"Error extracting imports: {e}")
        
        return imports
    
    def _extract_python_functions(self, root_node: Node) -> List[str]:
        """Extract public function names."""
        functions = []
        
        try:
            captures = self.python_function_query.captures(root_node)
            for capture, capture_name in captures:
                if capture_name == "name":
                    func_name = capture.text.decode('utf8')
                    if not func_name.startswith("_"):
                        functions.append(func_name)
        except Exception as e:
            logger.debug(f"Error extracting functions: {e}")
        
        return functions
    
    def _extract_python_classes(self, root_node: Node) -> List[str]:
        """Extract class names."""
        classes = []
        
        try:
            captures = self.python_class_query.captures(root_node)
            for capture, capture_name in captures:
                if capture_name == "name":
                    classes.append(capture.text.decode('utf8'))
        except Exception as e:
            logger.debug(f"Error extracting classes: {e}")
        
        return classes
    
    def _detect_data_patterns(self, root_node: Node, source_code: bytes) -> Dict[str, bool]:
        """Detect data engineering patterns in Python code."""
        patterns = {
            "pandas": False,
            "spark": False,
            "sqlalchemy": False,
            "airflow": False,
            "dbt": False,
            "read_csv": False,
            "read_sql": False,
            "write_csv": False,
            "write_parquet": False
        }
        
        try:
            # Check for pandas operations
            source_str = source_code.decode('utf8').lower()
            
            if 'pandas' in source_str or 'pd.' in source_str:
                patterns["pandas"] = True
            
            if 'spark' in source_str or 'pyspark' in source_str:
                patterns["spark"] = True
            
            if 'sqlalchemy' in source_str or 'create_engine' in source_str:
                patterns["sqlalchemy"] = True
            
            if 'airflow' in source_str or 'dag' in source_str:
                patterns["airflow"] = True
            
            # Check for specific operations
            patterns["read_csv"] = 'read_csv' in source_str
            patterns["read_sql"] = 'read_sql' in source_str
            patterns["write_csv"] = 'to_csv' in source_str
            patterns["write_parquet"] = 'write.parquet' in source_str or 'to_parquet' in source_str
        except Exception as e:
            logger.debug(f"Error detecting data patterns: {e}")
        
        return patterns
    
    def _calculate_complexity(self, root_node: Node, source_code: bytes) -> float:
        """Calculate a simple complexity score."""
        # Start with line count as base
        lines = len(source_code.decode('utf8').splitlines())
        
        # Add points for control structures
        control_structures = 0
        
        def count_control_structures(node: Node):
            nonlocal control_structures
            try:
                node_type = node.type.decode('utf8') if isinstance(node.type, bytes) else node.type
                
                if 'if_statement' in node_type:
                    control_structures += 1
                elif 'for_statement' in node_type:
                    control_structures += 1
                elif 'while_statement' in node_type:
                    control_structures += 1
                elif 'try_statement' in node_type:
                    control_structures += 1
                
                for child in node.children:
                    count_control_structures(child)
            except:
                pass
        
        count_control_structures(root_node)
        
        # Complexity formula: lines/20 + control_structures (adjusted to be more reasonable)
        return (lines / 20) + control_structures
    
    def _extract_docstring(self, root_node: Node, source_code: bytes) -> Optional[str]:
        """Extract module-level docstring if present."""
        try:
            # Look for string at module level
            for child in root_node.children:
                if child.type == 'expression_statement':
                    expr = child.children[0] if child.children else None
                    if expr and expr.type == 'string':
                        return expr.text.decode('utf8').strip('"\'')
        except:
            pass
        
        return None
    
    def analyze_sql_file(self, file_path: Path) -> ModuleNode:
        """Extract basic structure from SQL file.
        
        Note: Full SQL lineage analysis will be handled by the Hydrologist agent
        in Phase 2 using sqlglot. This is just a placeholder for Phase 1.
        """
        try:
            with open(file_path, "rb") as f:
                source_code = f.read()
            
            lines = len(source_code.decode('utf8').splitlines())
            
            return ModuleNode(
                path=str(file_path),
                language="sql",
                imports=[],
                public_functions=[],
                classes=[],
                complexity_score=lines / 20,
                purpose_statement="",
                metadata={
                    "line_count": lines,
                    "note": "SQL analysis deferred to Hydrologist agent (Phase 2)"
                }
            )
        except Exception as e:
            logger.error(f"Error analyzing SQL file {file_path}: {e}")
            return ModuleNode(
                path=str(file_path),
                language="sql",
                metadata={"error": str(e)}
            )
    
    def analyze_yaml_file(self, file_path: Path) -> ModuleNode:
        """Extract basic structure from YAML file."""
        try:
            with open(file_path, "rb") as f:
                source_code = f.read()
            
            lines = len(source_code.decode('utf8').splitlines())
            
            # Check if it's a dbt schema file
            is_dbt_schema = "schema.yml" in str(file_path) or "dbt_project.yml" in str(file_path)
            
            return ModuleNode(
                path=str(file_path),
                language="yaml",
                imports=[],
                public_functions=[],
                classes=[],
                complexity_score=lines / 20,
                purpose_statement="",
                metadata={
                    "is_dbt_schema": is_dbt_schema,
                    "line_count": lines
                }
            )
        except Exception as e:
            logger.error(f"Error analyzing YAML file {file_path}: {e}")
            return ModuleNode(
                path=str(file_path),
                language="yaml",
                metadata={"error": str(e)}
            )
    
    def analyze_jupyter_file(self, file_path: Path) -> ModuleNode:
        """Placeholder for Jupyter notebook analysis."""
        return ModuleNode(
            path=str(file_path),
            language="jupyter",
            imports=[],
            public_functions=[],
            classes=[],
            complexity_score=0,
            purpose_statement="Jupyter notebook analysis coming in Phase 2",
            metadata={"note": "Jupyter analysis deferred to Phase 2"}
        )
    
    def analyze_unknown_file(self, file_path: Path) -> ModuleNode:
        """Handle unknown file types."""
        return ModuleNode(
            path=str(file_path),
            language="unknown",
            imports=[],
            public_functions=[],
            classes=[],
            complexity_score=0,
            metadata={"note": "Unknown file type"}
        )
    
    def clear_cache(self):
        """Clear the AST cache."""
        self._ast_cache.clear()
        logger.info("AST cache cleared")