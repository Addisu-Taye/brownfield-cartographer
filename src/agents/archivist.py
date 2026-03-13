"""Agent 4: The Archivist - Living Context Maintainer

Produces and maintains the system's outputs as living artifacts that
can be re-used and updated as the codebase evolves.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import networkx as nx

from src.models.nodes import KnowledgeGraph, EdgeType

logger = logging.getLogger(__name__)


class Archivist:
    """Agent 4: Living Context Maintainer
    
    Produces artifacts:
    - CODEBASE.md: Living context file for AI agents
    - onboarding_brief.md: Day-One Brief answering five FDE questions
    - cartography_trace.jsonl: Audit log of all actions
    """
    
    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.trace_log: List[Dict[str, Any]] = []
        self.stats = {
            "artifacts_generated": 0,
            "traces_logged": 0
        }
    
    def log_trace(self, action: str, agent: str, details: Dict[str, Any]):
        """Log an action to the trace file."""
        trace_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "agent": agent,
            "details": details
        }
        self.trace_log.append(trace_entry)
        self.stats["traces_logged"] += 1
        logger.debug(f"Trace logged: {action} by {agent}")
    
    def save_trace_log(self, output_path: Optional[Path] = None):
        """Save trace log to JSONL file."""
        if output_path is None:
            output_path = self.cache_dir / "cartography_trace.jsonl"
        
        with open(output_path, 'w') as f:
            for entry in self.trace_log:
                f.write(json.dumps(entry) + '\n')
        
        logger.info(f"💾 Trace log saved to {output_path}")
    
    def generate_codebase_md(self, 
                            surveyor_data: Dict,
                            lineage_data: Dict,
                            semantic_data: Dict) -> str:
        """Generate CODEBASE.md - living context file for AI agents."""
        
        content = []
        
        # Header
        content.append("# CODEBASE.md - Living Context")
        content.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content.append("\n---\n")
        
        # 1. Architecture Overview
        content.append("## 🏗️ Architecture Overview")
        content.append("\n### Critical Modules (PageRank):")
        
        if surveyor_data.get("graph"):
            # Extract top modules by PageRank
            import networkx as nx
            from networkx.readwrite import json_graph
            
            G = json_graph.node_link_graph(surveyor_data["graph"])
            try:
                pagerank = nx.pagerank(G)
                top_modules = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:5]
                for module, score in top_modules:
                    content.append(f"- `{module}` (importance: {score:.3f})")
            except:
                content.append("- PageRank analysis unavailable")
        
        content.append("\n### Module Counts:")
        nodes = surveyor_data.get("nodes", {})
        python_count = sum(1 for n in nodes.values() if n.get("language") == "python")
        sql_count = sum(1 for n in nodes.values() if n.get("language") == "sql")
        yaml_count = sum(1 for n in nodes.values() if n.get("language") == "yaml")
        
        content.append(f"- Python modules: {python_count}")
        content.append(f"- SQL files: {sql_count}")
        content.append(f"- YAML configs: {yaml_count}")
        
        # 2. Data Lineage
        content.append("\n## 🔄 Data Lineage")
        content.append("\n### Source Datasets (Ingestion Points):")
        sources = lineage_data.get("sources", [])
        for src in sources[:10]:
            content.append(f"- `{src}`")
        
        content.append("\n### Sink Datasets (Final Outputs):")
        sinks = lineage_data.get("sinks", [])
        for sink in sinks[:10]:
            content.append(f"- `{sink}`")
        
        # 3. Semantic Understanding
        content.append("\n## 🧠 Semantic Understanding")
        content.append("\n### Domain Clusters:")
        
        domains = semantic_data.get("domain_clusters", {})
        domain_groups = {}
        for module, domain in domains.items():
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(module)
        
        for domain, modules in domain_groups.items():
            content.append(f"\n**{domain}**:")
            for module in modules[:3]:  # Show first 3
                content.append(f"- `{module}`")
            if len(modules) > 3:
                content.append(f"  *...and {len(modules)-3} more*")
        
        # 4. Documentation Health
        content.append("\n## 📝 Documentation Health")
        
        drift_flags = semantic_data.get("doc_drift_flags", {})
        drift_modules = [m for m, drifted in drift_flags.items() if drifted]
        
        content.append(f"\n- Modules with documentation drift: {len(drift_modules)}")
        for module in drift_modules[:5]:
            content.append(f"  - ⚠️ `{module}`")
        
        # 5. Change Velocity
        content.append("\n## 📈 Change Velocity (Last 30 days)")
        
        velocity = surveyor_data.get("metadata", {}).get("velocity_summary", {})
        content.append(f"\n- Total changes: {velocity.get('total_changes_30d', 0)}")
        content.append(f"- Active files: {velocity.get('files_with_changes', 0)}")
        content.append(f"- Stale files: {velocity.get('stale_files', 0)}")
        
        # 6. Known Debt
        content.append("\n## ⚠️ Known Technical Debt")
        
        # Dead code candidates
        dead_code = []
        for node_path, node_data in surveyor_data.get("nodes", {}).items():
            if node_data.get("is_dead_code_candidate"):
                dead_code.append(node_path)
        
        content.append(f"\n- Dead code candidates: {len(dead_code)}")
        for dc in dead_code[:5]:
            content.append(f"  - `{dc}`")
        
        # Circular dependencies
        circular = surveyor_data.get("metadata", {}).get("stats", {}).get("circular_dependencies", 0)
        content.append(f"- Circular dependencies: {circular}")
        
        # Join all content
        return "\n".join(content)
    
    def generate_onboarding_brief(self, 
                                 surveyor_data: Dict,
                                 lineage_data: Dict,
                                 semantic_data: Dict) -> str:
        """Generate onboarding_brief.md with answers to five FDE questions."""
        
        content = []
        
        # Header
        content.append("# FDE Day-One Onboarding Brief")
        content.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content.append("\n---\n")
        
        # Executive Summary
        content.append("## Executive Summary")
        
        datasets = lineage_data.get("datasets", {})
        sources = lineage_data.get("sources", [])
        sinks = lineage_data.get("sinks", [])
        
        content.append(f"\nThis codebase contains:")
        content.append(f"- {len(surveyor_data.get('nodes', {}))} total files")
        content.append(f"- {len(datasets)} datasets identified")
        content.append(f"- {len(sources)} source ingestion points")
        content.append(f"- {len(sinks)} final output datasets")
        
        # Question 1: Primary ingestion path
        content.append("\n## 1. Primary Data Ingestion Path")
        if sources:
            content.append(f"\nData is ingested through {len(sources)} source tables:")
            for src in sources[:5]:
                # Find files that reference this source
                files = []
                for fname, finfo in datasets.items():
                    if fname == src:
                        files = finfo.get("files", [])
                content.append(f"\n   📥 `{src}`")
                for f in files[:2]:
                    content.append(f"      └─ Used in: `{f}`")
        else:
            content.append("\nNo ingestion sources identified.")
        
        # Question 2: Critical output datasets
        content.append("\n## 2. Critical Output Datasets")
        if sinks:
            content.append(f"\nThe {len(sinks)} most critical output datasets are:")
            for i, sink in enumerate(sinks[:5], 1):
                # Find what produces this sink
                producers = []
                for trans_id, trans_info in lineage_data.get("transformations", {}).items():
                    if sink in trans_info.get("writes", []):
                        producers.append(trans_info.get("file", "unknown"))
                content.append(f"\n   {i}. `{sink}`")
                for prod in producers[:2]:
                    content.append(f"      └─ Produced by: `{prod}`")
        else:
            content.append("\nNo sink datasets identified.")
        
        # Question 3: Blast radius
        content.append("\n## 3. Blast Radius Analysis")
        if sinks:
            most_critical = sinks[0] if sinks else "unknown"
            content.append(f"\nIf the most critical module `{most_critical}` fails:")
            
            # Find downstream dependents
            downstream = []
            for trans_id, trans_info in lineage_data.get("transformations", {}).items():
                if most_critical in trans_info.get("reads", []):
                    downstream.append(trans_info.get("file", "unknown"))
            
            if downstream:
                content.append(f"\n   {len(downstream)} downstream modules would be affected:")
                for dep in downstream[:5]:
                    content.append(f"      └─ `{dep}`")
            else:
                content.append("\n   No direct downstream dependencies (terminal node).")
        
        # Question 4: Business logic concentration
        content.append("\n## 4. Business Logic Concentration")
        
        # Use semantic data to identify business domains
        domains = semantic_data.get("domain_clusters", {})
        if domains:
            content.append("\nBusiness logic is concentrated in these domains:")
            domain_counts = {}
            for domain in domains.values():
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                content.append(f"\n   **{domain}**: {count} modules")
        else:
            content.append("\nBusiness logic distribution analysis unavailable.")
        
        # Question 5: Change velocity
        content.append("\n## 5. Change Velocity (Last 90 Days)")
        
        velocity = surveyor_data.get("metadata", {}).get("velocity_summary", {})
        content.append(f"\n- Total changes: {velocity.get('total_changes_30d', 0)}")
        content.append(f"- Files with changes: {velocity.get('files_with_changes', 0)}")
        content.append(f"- Stale files (no changes): {velocity.get('stale_files', 0)}")
        
        # High-velocity files
        high_velocity = []
        for node_path, node_data in surveyor_data.get("nodes", {}).items():
            if node_data.get("change_velocity_30d", 0) > 0:
                high_velocity.append((node_path, node_data.get("change_velocity_30d", 0)))
        
        if high_velocity:
            content.append("\n\n   Most frequently changed files:")
            for path, changes in sorted(high_velocity, key=lambda x: x[1], reverse=True)[:5]:
                content.append(f"      - `{path}` ({changes} changes)")
        
        # Recommendations
        content.append("\n---\n")
        content.append("## 🎯 Recommended Next Steps")
        content.append("\n1. **Review dead code candidates** - Clean up unused modules")
        content.append("2. **Fix documentation drift** - Update stale docstrings")
        content.append("3. **Monitor high-velocity files** - These may indicate instability")
        content.append("4. **Document blast radius** - Create runbooks for critical datasets")
        
        return "\n".join(content)
    
    def save_artifacts(self, 
                       surveyor_data: Dict,
                       lineage_data: Dict,
                       semantic_data: Dict):
        """Generate and save all artifacts."""
        
        # Generate CODEBASE.md
        codebase_content = self.generate_codebase_md(surveyor_data, lineage_data, semantic_data)
        codebase_path = self.cache_dir / "CODEBASE.md"
        with open(codebase_path, 'w') as f:
            f.write(codebase_content)
        self.stats["artifacts_generated"] += 1
        logger.info(f"📄 CODEBASE.md generated")
        
        # Generate onboarding brief
        brief_content = self.generate_onboarding_brief(surveyor_data, lineage_data, semantic_data)
        brief_path = self.cache_dir / "onboarding_brief.md"
        with open(brief_path, 'w') as f:
            f.write(brief_content)
        self.stats["artifacts_generated"] += 1
        logger.info(f"📄 onboarding_brief.md generated")
        
        # Save trace log
        self.save_trace_log()
    
    def run(self, surveyor_data: Dict, lineage_data: Dict, semantic_data: Dict):
        """Run the Archivist agent."""
        logger.info("📚 Archivist: Generating living context artifacts...")
        
        self.log_trace("start", "archivist", {"action": "Generating artifacts"})
        self.save_artifacts(surveyor_data, lineage_data, semantic_data)
        self.log_trace("complete", "archivist", {
            "artifacts": self.stats["artifacts_generated"],
            "traces": self.stats["traces_logged"]
        })
        
        logger.info(f"✅ Archivist complete. Generated {self.stats['artifacts_generated']} artifacts")
        return self.stats