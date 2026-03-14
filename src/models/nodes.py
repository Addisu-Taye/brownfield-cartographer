from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime


class EdgeType(str, Enum):
    """Types of relationships between nodes in the knowledge graph."""
    IMPORTS = "imports"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    CALLS = "calls"
    CONFIGURES = "configures"
    EXTENDS = "extends"
    CONTAINS = "contains"


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""
    MODULE = "module"
    DATASET = "dataset"
    FUNCTION = "function"
    CLASS = "class"
    TRANSFORMATION = "transformation"
    CONFIG = "config"
    TEST = "test"


class BaseNode(BaseModel):
    """Base model for all graph nodes."""
    type: NodeType
    id: Optional[str] = None  # Will be generated from path/name


class ModuleNode(BaseNode):
    """Represents a code file/module in the repository."""
    
    # Required fields
    path: str
    language: str = "unknown"
    type: NodeType = NodeType.MODULE  # Add this line
    
    # Optional fields with defaults
    imports: List[str] = Field(default_factory=list)
    public_functions: List[str] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    complexity_score: float = 0.0
    purpose_statement: str = ""
    domain_cluster: Optional[str] = None
    
    # Git/change tracking
    change_velocity_30d: int = 0
    change_velocity_90d: int = 0
    total_commits: int = 0
    last_modified: Optional[datetime] = None
    
    # Analysis flags
    is_dead_code_candidate: bool = False
    is_entry_point: bool = False
    is_test: bool = False
    import_count: int = 0
    pagerank_score: float = 0.0
    in_circular_dependency: bool = False
    
    # Documentation
    docstring: Optional[str] = None
    has_docstring: bool = False
    docstring_drift: bool = False
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = NodeType.MODULE
        if not self.id:
            self.id = f"module:{self.path}"
        self.has_docstring = bool(self.docstring)

class FunctionNode(BaseNode):
    """Represents a function or method in the codebase."""
    
    # Required fields
    qualified_name: str  # module.function_name or class.method_name
    parent_module: str  # Path to containing module
    
    # Optional fields
    signature: str = ""
    parameters: List[str] = Field(default_factory=list)
    return_type: Optional[str] = None
    purpose_statement: str = ""
    docstring: Optional[str] = None
    has_docstring: bool = False
    line_start: int = 0
    line_end: int = 0
    
    # Analysis
    call_count_within_repo: int = 0
    complexity: float = 0.0
    is_public_api: bool = True  # Not starting with _
    
    # Decorators
    decorators: List[str] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = NodeType.FUNCTION
        if not self.id:
            self.id = f"function:{self.qualified_name}"
        self.has_docstring = bool(self.docstring)
        self.is_public_api = not self.qualified_name.split('.')[-1].startswith('_')


class ClassNode(BaseNode):
    """Represents a class in the codebase."""
    
    # Required fields
    qualified_name: str  # module.ClassName
    parent_module: str
    
    # Optional fields
    docstring: Optional[str] = None
    has_docstring: bool = False
    methods: List[str] = Field(default_factory=list)
    class_variables: List[str] = Field(default_factory=list)
    base_classes: List[str] = Field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = NodeType.CLASS
        if not self.id:
            self.id = f"class:{self.qualified_name}"
        self.has_docstring = bool(self.docstring)


class DatasetNode(BaseNode):
    """Represents a dataset (table, file, stream) in the data lineage."""
    
    # Required fields
    name: str
    storage_type: str  # table, file, stream, api, view
    
    # Optional fields
    schema_snapshot: Dict[str, str] = Field(default_factory=dict)  # column_name -> type
    freshness_sla: Optional[str] = None  # e.g., "1h", "daily"
    owner: Optional[str] = None
    is_source_of_truth: bool = False
    description: Optional[str] = None
    
    # Lineage metadata
    source_files: List[str] = Field(default_factory=list)  # Files that produce/consume this
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = NodeType.DATASET
        if not self.id:
            self.id = f"dataset:{self.name}"


class TransformationNode(BaseNode):
    """Represents a data transformation operation."""
    
    # Required fields
    source_datasets: List[str] = Field(default_factory=list)
    target_datasets: List[str] = Field(default_factory=list)
    transformation_type: str  # sql, python_script, dbt_model, spark_job, etc.
    
    # Location
    source_file: str
    line_start: int = 0
    line_end: int = 0
    
    # Optional fields
    sql_query: Optional[str] = None
    transformation_logic: Optional[str] = None  # For non-SQL transformations
    description: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = NodeType.TRANSFORMATION
        if not self.id:
            # Generate ID from source file and line numbers
            self.id = f"transform:{self.source_file}:{self.line_start}-{self.line_end}"


class ConfigNode(BaseNode):
    """Represents a configuration file or entry."""
    
    # Required fields
    path: str
    config_type: str  # yaml, json, env, dbt_schema, airflow_dag
    
    # Optional fields
    config_keys: List[str] = Field(default_factory=list)
    references_modules: List[str] = Field(default_factory=list)
    references_datasets: List[str] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = NodeType.CONFIG
        if not self.id:
            self.id = f"config:{self.path}"


class TestNode(BaseNode):
    """Represents a test file or test case."""
    
    # Required fields
    path: str
    test_type: str  # unit, integration, data_quality, schema
    change_velocity_90d: int = 0
    total_commits: int = 0
    is_entry_point: bool = False
    is_test: bool = False
    import_count: int = 0
    pagerank_score: float = 0.0
    in_circular_dependency: bool = False
    
    # Optional fields
    tests_what: List[str] = Field(default_factory=list)  # What modules/datasets this tests
    assertion_count: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = NodeType.TEST
        if not self.id:
            self.id = f"test:{self.path}"
            
    


# Edge model for graph relationships
class Edge(BaseModel):
    """Represents a relationship between two nodes."""
    
    source: str  # Node ID
    target: str  # Node ID
    type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Knowledge Graph container
class KnowledgeGraph(BaseModel):
    """Container for the entire knowledge graph."""
    
    nodes: Dict[str, Union[ModuleNode, FunctionNode, ClassNode, DatasetNode, 
                          TransformationNode, ConfigNode, TestNode]] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)
    repo_path: str = ""
    version: str = "1.0.0"
    
    def add_node(self, node: BaseNode):
        """Add a node to the graph."""
        self.nodes[node.id] = node
    
    def add_edge(self, source_id: str, target_id: str, edge_type: EdgeType, **metadata):
        """Add an edge to the graph."""
        edge = Edge(
            source=source_id,
            target=target_id,
            type=edge_type,
            metadata=metadata
        )
        self.edges.append(edge)
    
    def get_node(self, node_id: str) -> Optional[BaseNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[str]:
        """Get all neighbors of a node, optionally filtered by edge type."""
        neighbors = []
        for edge in self.edges:
            if edge.source == node_id:
                if edge_type is None or edge.type == edge_type:
                    neighbors.append(edge.target)
            elif edge.target == node_id:
                if edge_type is None or edge.type == edge_type:
                    neighbors.append(edge.source)
        return neighbors