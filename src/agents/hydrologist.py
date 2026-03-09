import sqlglot
from src.models.nodes import DatasetNode, TransformationNode

class Hydrologist:
    def __init__(self):
        self.lineage_graph = nx.DiGraph()

    def parse_sql_lineage(self, sql_content: str, source_file: str):
        """Extract table dependencies using sqlglot."""
        try:
            parsed = sqlglot.parse_one(sql_content)
            # Extract tables from FROM and JOIN clauses
            tables = [table.name for table in parsed.find_all(sqlglot.exp.Table)]
            return tables
        except Exception as e:
            print(f"Failed to parse {source_file}: {e}")
            return []

    def build_lineage_graph(self, repo_path: Path):
        """Walk repo for .sql files and build lineage."""
        for file in repo_path.rglob("*.sql"):
            with open(file, 'r') as f:
                content = f.read()
            deps = self.parse_sql_lineage(content, str(file))
            # TODO: Add nodes (datasets) and edges (dependencies) to self.lineage_graph
        return self.lineage_graph