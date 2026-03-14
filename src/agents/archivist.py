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
        """Save trace log to JSONL file with UTF-8 encoding."""
        if output_path is None:
            output_path = self.cache_dir / "cartography_trace.jsonl"
        
        with open(output_path, 'w', encoding='utf-8') as f:
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
        
        # Safely handle graph data
        if surveyor_data and surveyor_data.get("graph"):
            try:
                from networkx.readwrite import json_graph
                G = json_graph.node_link_graph(surveyor_data["graph"])
                pagerank = nx.pagerank(G)
                top_modules = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:5]
                for module, score in top_modules:
                    content.append(f"- `{module}` (importance: {score:.3f})")
            except:
                content.append("- PageRank analysis unavailable")
        else:
            content.append("- No module graph available")
        
        # Module counts
        content.append("\n### Module Counts:")
        nodes = surveyor_data.get("nodes", {}) if surveyor_data else {}
        python_count = sum(1 for n in nodes.values() if n.get("language") == "python")
        sql_count = sum(1 for n in nodes.values() if n.get("language") == "sql")
        yaml_count = sum(1 for n in nodes.values() if n.get("language") == "yaml")
        
        content.append(f"- Python modules: {python_count}")
        content.append(f"- SQL files: {sql_count}")
        content.append(f"- YAML configs: {yaml_count}")
        content.append(f"- Total files: {len(nodes)}")
        
        # 2. Data Lineage
        content.append("\n## 🔄 Data Lineage")
        content.append("\n### Source Datasets (Ingestion Points):")
        sources = lineage_data.get("sources", []) if lineage_data else []
        if sources:
            for src in sources[:10]:
                content.append(f"- `{src}`")
        else:
            content.append("- No sources identified")
        
        content.append("\n### Sink Datasets (Final Outputs):")
        sinks = lineage_data.get("sinks", []) if lineage_data else []
        if sinks:
            for sink in sinks[:10]:
                content.append(f"- `{sink}`")
        else:
            content.append("- No sinks identified")
        
        # Dataset counts
        datasets = lineage_data.get("datasets", {}) if lineage_data else {}
        content.append(f"\n### Dataset Statistics:")
        content.append(f"- Total datasets: {len(datasets)}")
        
        # 3. Semantic Understanding
        content.append("\n## 🧠 Semantic Understanding")
        content.append("\n### Domain Clusters:")
        
        domains = semantic_data.get("domain_clusters", {}) if semantic_data else {}
        if domains:
            domain_groups = {}
            for module, domain in domains.items():
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(module)
            
            for domain, modules in domain_groups.items():
                content.append(f"\n**{domain}** ({len(modules)} modules):")
                for module in modules[:3]:
                    content.append(f"- `{module}`")
                if len(modules) > 3:
                    content.append(f"  *...and {len(modules)-3} more*")
        else:
            content.append("- No domain clustering available")
        
        # 4. Documentation Health
        content.append("\n## 📝 Documentation Health")
        
        drift_flags = semantic_data.get("doc_drift_flags", {}) if semantic_data else {}
        drift_modules = [m for m, drifted in drift_flags.items() if drifted]
        
        content.append(f"\n- Modules with documentation drift: {len(drift_modules)}")
        for module in drift_modules[:5]:
            content.append(f"  - ⚠️ `{module}`")
        
        # Purpose statements
        purposes = semantic_data.get("purpose_statements", {}) if semantic_data else {}
        content.append(f"\n- Modules with purpose statements: {len(purposes)}")
        
        # 5. Change Velocity
        content.append("\n## 📈 Change Velocity (Last 30 days)")
        
        velocity = surveyor_data.get("metadata", {}).get("velocity_summary", {}) if surveyor_data else {}
        content.append(f"\n- Total changes: {velocity.get('total_changes_30d', 0)}")
        content.append(f"- Active files: {velocity.get('files_with_changes', 0)}")
        content.append(f"- Stale files: {velocity.get('stale_files', 0)}")
        
        # 6. Known Debt
        content.append("\n## ⚠️ Known Technical Debt")
        
        # Dead code candidates
        dead_code = []
        if surveyor_data:
            for node_path, node_data in surveyor_data.get("nodes", {}).items():
                if node_data.get("is_dead_code_candidate"):
                    dead_code.append(node_path)
        
        content.append(f"\n- Dead code candidates: {len(dead_code)}")
        for dc in dead_code[:5]:
            content.append(f"  - `{dc}`")
        
        # Circular dependencies
        circular = surveyor_data.get("metadata", {}).get("stats", {}).get("circular_dependencies", 0) if surveyor_data else 0
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
        
        nodes = surveyor_data.get("nodes", {}) if surveyor_data else {}
        datasets = lineage_data.get("datasets", {}) if lineage_data else {}
        sources = lineage_data.get("sources", []) if lineage_data else []
        sinks = lineage_data.get("sinks", []) if lineage_data else []
        
        content.append(f"\nThis codebase contains:")
        content.append(f"- {len(nodes)} total files")
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
                for dname, dinfo in datasets.items():
                    if dname == src:
                        files = dinfo.get("files", [])
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
                transformations = lineage_data.get("transformations", {}) if lineage_data else {}
                for trans_id, trans_info in transformations.items():
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
            transformations = lineage_data.get("transformations", {}) if lineage_data else {}
            for trans_id, trans_info in transformations.items():
                if most_critical in trans_info.get("reads", []):
                    downstream.append(trans_info.get("file", "unknown"))
            
            if downstream:
                content.append(f"\n   {len(downstream)} downstream modules would be affected:")
                for dep in downstream[:5]:
                    content.append(f"      └─ `{dep}`")
            else:
                content.append("\n   No direct downstream dependencies (terminal node).")
        else:
            content.append("\nNo critical modules identified.")
        
        # Question 4: Business logic concentration
        content.append("\n## 4. Business Logic Concentration")
        
        # Use semantic data to identify business domains
        domains = semantic_data.get("domain_clusters", {}) if semantic_data else {}
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
        
        velocity = surveyor_data.get("metadata", {}).get("velocity_summary", {}) if surveyor_data else {}
        content.append(f"\n- Total changes: {velocity.get('total_changes_30d', 0)}")
        content.append(f"- Files with changes: {velocity.get('files_with_changes', 0)}")
        content.append(f"- Stale files (no changes): {velocity.get('stale_files', 0)}")
        
        # High-velocity files
        high_velocity = []
        if surveyor_data:
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
        """Generate and save all artifacts with proper UTF-8 encoding."""
        
        # Generate CODEBASE.md
        codebase_content = self.generate_codebase_md(surveyor_data, lineage_data, semantic_data)
        codebase_path = self.cache_dir / "CODEBASE.md"
        # Use UTF-8 encoding explicitly
        with open(codebase_path, 'w', encoding='utf-8') as f:
            f.write(codebase_content)
        self.stats["artifacts_generated"] += 1
        logger.info(f"📄 CODEBASE.md generated ({codebase_path.stat().st_size} bytes)")
        
        # Generate onboarding brief
        brief_content = self.generate_onboarding_brief(surveyor_data, lineage_data, semantic_data)
        brief_path = self.cache_dir / "onboarding_brief.md"
        # Use UTF-8 encoding explicitly
        with open(brief_path, 'w', encoding='utf-8') as f:
            f.write(brief_content)
        self.stats["artifacts_generated"] += 1
        logger.info(f"📄 onboarding_brief.md generated ({brief_path.stat().st_size} bytes)")
        
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