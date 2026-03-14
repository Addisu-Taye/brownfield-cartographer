"""Orchestrator for the Brownfield Cartographer agents.

This module coordinates the four analysis agents:
- Surveyor (static structure analysis)
- Hydrologist (data lineage analysis)
- Semanticist (LLM-powered analysis)
- Archivist (living context maintenance)
- Navigator (query interface)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Import agents
from src.agents.surveyor import Surveyor
from src.agents.hydrologist import Hydrologist
from src.agents.semanticist import Semanticist
from src.agents.archivist import Archivist
from src.agents.navigator import Navigator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrates the four analysis agents.
    
    This class coordinates the execution of all agents in the correct order,
    manages shared state, and ensures artifacts are properly generated.
    """
    
    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        """Initialize the orchestrator.
        
        Args:
            repo_path: Path to the git repository to analyze
            cache_dir: Directory to store cartography artifacts (default: repo_path/.cartography)
        """
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize agents (lazy loading - only create when needed)
        self._surveyor = None
        self._hydrologist = None
        self._semanticist = None
        self._archivist = None
        self._navigator = None
        
        # Track state
        self.phases_completed = []
        self.start_time = None
        self.end_time = None
    
    @property
    def surveyor(self) -> Surveyor:
        """Lazy-load Surveyor agent."""
        if self._surveyor is None:
            self._surveyor = Surveyor(str(self.repo_path), self.cache_dir)
        return self._surveyor
    
    @property
    def hydrologist(self) -> Hydrologist:
        """Lazy-load Hydrologist agent."""
        if self._hydrologist is None:
            self._hydrologist = Hydrologist(str(self.repo_path), self.cache_dir)
        return self._hydrologist
    
    @property
    def semanticist(self) -> Semanticist:
        """Lazy-load Semanticist agent."""
        if self._semanticist is None:
            self._semanticist = Semanticist(str(self.repo_path), self.cache_dir)
        return self._semanticist
    
    @property
    def archivist(self) -> Archivist:
        """Lazy-load Archivist agent."""
        if self._archivist is None:
            self._archivist = Archivist(str(self.repo_path), self.cache_dir)
        return self._archivist
    
    @property
    def navigator(self) -> Navigator:
        """Lazy-load Navigator agent."""
        if self._navigator is None:
            self._navigator = Navigator(str(self.repo_path), self.cache_dir)
        return self._navigator
    
    def run_phase1(self) -> bool:
        """Run Surveyor agent (static structure analysis).
        
        Returns:
            bool: True if phase completed successfully
        """
        logger.info("="*60)
        logger.info("PHASE 1: Surveyor Agent - Static Structure Analysis")
        logger.info("="*60)
        
        try:
            # Run surveyor
            self.surveyor.run()
            
            # Save artifacts
            self.surveyor.save_graph(self.cache_dir / "module_graph.json")
            self.surveyor.save_dead_code_report(self.cache_dir / "dead_code_candidates.md")
            
            # Log trace
            self.archivist.log_trace("phase_complete", "surveyor", {
                "stats": self.surveyor.stats,
                "nodes": len(self.surveyor.nodes)
            })
            
            self.phases_completed.append("phase1")
            logger.info("✅ Phase 1 complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 1 failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def run_phase2(self) -> bool:
        """Run Hydrologist agent (data lineage analysis).
        
        Returns:
            bool: True if phase completed successfully
        """
        logger.info("="*60)
        logger.info("PHASE 2: Hydrologist Agent - Data Lineage Analysis")
        logger.info("="*60)
        
        try:
            # Run hydrologist
            self.hydrologist.run()
            
            # Save artifacts
            self.hydrologist.save_lineage_graph(self.cache_dir / "lineage_graph.json")
            
            # Log trace
            self.archivist.log_trace("phase_complete", "hydrologist", {
                "stats": self.hydrologist.stats,
                "datasets": len(self.hydrologist.datasets),
                "transformations": len(self.hydrologist.transformations)
            })
            
            self.phases_completed.append("phase2")
            logger.info("✅ Phase 2 complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 2 failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def run_phase3(self) -> bool:
        """Run Semanticist agent (LLM-powered analysis).
        
        Returns:
            bool: True if phase completed successfully
        """
        logger.info("="*60)
        logger.info("PHASE 3: Semanticist Agent - LLM-Powered Analysis")
        logger.info("="*60)
        
        try:
            # Load data from previous phases
            surveyor_data = {}
            lineage_data = {}
            
            module_path = self.cache_dir / "module_graph.json"
            if module_path.exists():
                with open(module_path) as f:
                    surveyor_data = json.load(f)
            
            lineage_path = self.cache_dir / "lineage_graph.json"
            if lineage_path.exists():
                with open(lineage_path) as f:
                    lineage_data = json.load(f)
            
            # Run semanticist
            semantic_results = self.semanticist.run(surveyor_data, lineage_data)
            
            # Log trace
            self.archivist.log_trace("phase_complete", "semanticist", {
                "stats": self.semanticist.stats,
                "purpose_statements": len(self.semanticist.purpose_statements),
                "doc_drift": len(self.semanticist.doc_drift_flags),
                "cost": self.semanticist.budget.total_cost
            })
            
            self.phases_completed.append("phase3")
            logger.info("✅ Phase 3 complete")
            logger.info(f"💰 Total LLM cost: ${self.semanticist.budget.total_cost:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 3 failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def run_phase4(self) -> bool:
        """Run Archivist agent (living context maintenance).
        
        Returns:
            bool: True if phase completed successfully
        """
        logger.info("="*60)
        logger.info("PHASE 4: Archivist Agent - Living Context Maintenance")
        logger.info("="*60)
        
        try:
            # Load data from all phases
            surveyor_data = {}
            lineage_data = {}
            semantic_data = {}
            
            module_path = self.cache_dir / "module_graph.json"
            if module_path.exists():
                with open(module_path) as f:
                    surveyor_data = json.load(f)
            
            lineage_path = self.cache_dir / "lineage_graph.json"
            if lineage_path.exists():
                with open(lineage_path) as f:
                    lineage_data = json.load(f)
            
            semantic_path = self.cache_dir / "semantic_index.json"
            if semantic_path.exists():
                with open(semantic_path) as f:
                    semantic_data = json.load(f)
            
            # Run archivist
            self.archivist.run(surveyor_data, lineage_data, semantic_data)
            
            # Initialize navigator (loads graphs for querying)
            self.navigator._load_graphs()
            
            # Save final trace log
            self.archivist.save_trace_log()
            
            self.phases_completed.append("phase4")
            logger.info("✅ Phase 4 complete")
            logger.info(f"📄 Generated {self.archivist.stats['artifacts_generated']} artifacts")
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 4 failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def run_full_analysis(self) -> Dict[str, bool]:
        """Run all available phases in sequence.
        
        Returns:
            Dict mapping phase names to success status
        """
        self.start_time = datetime.now()
        logger.info(f"🚀 Starting full analysis of {self.repo_path}")
        logger.info(f"📁 Artifacts will be saved to: {self.cache_dir}")
        
        results = {}
        
        # Phase 1
        results["phase1"] = self.run_phase1()
        
        # Phase 2
        results["phase2"] = self.run_phase2()
        
        # Phase 3
        results["phase3"] = self.run_phase3()
        
        # Phase 4
        results["phase4"] = self.run_phase4()
        
        self.end_time = datetime.now()
        elapsed = (self.end_time - self.start_time).total_seconds()
        
        logger.info("="*60)
        logger.info(f"✅ Full analysis complete in {elapsed:.2f} seconds")
        logger.info(f"📁 Artifacts saved to: {self.cache_dir}")
        logger.info(f"📊 Phases completed: {', '.join(self.phases_completed)}")
        logger.info("="*60)
        
        return results
    
    def query(self, question: str) -> Dict[str, Any]:
        """Query the knowledge graph using natural language.
        
        Args:
            question: Natural language question about the codebase
            
        Returns:
            Dict with query results
        """
        logger.info(f"🔍 Query: {question}")
        result = self.navigator.query(question)
        
        # Log query
        self.archivist.log_trace("query", "navigator", {
            "question": question,
            "tool": result.get("tool", "unknown")
        })
        
        return result
    
    def interactive(self):
        """Start interactive query mode."""
        logger.info("🗺️ Starting interactive Navigator mode")
        print("\n" + "="*60)
        print("🗺️  Brownfield Cartographer - Navigator")
        print("="*60)
        print("\nType 'help' for commands, 'quit' to exit")
        print("-"*60)
        
        self.navigator.interactive_mode()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of analysis.
        
        Returns:
            Dict with status information
        """
        status = {
            "repo_path": str(self.repo_path),
            "cache_dir": str(self.cache_dir),
            "phases_completed": self.phases_completed,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
        
        # Add agent stats if available
        if self._surveyor:
            status["surveyor"] = {
                "stats": self._surveyor.stats,
                "nodes_count": len(self._surveyor.nodes)
            }
        
        if self._hydrologist:
            status["hydrologist"] = {
                "stats": self._hydrologist.stats,
                "datasets_count": len(self._hydrologist.datasets),
                "transformations_count": len(self._hydrologist.transformations),
                "sources": self._hydrologist.find_sources(),
                "sinks": self._hydrologist.find_sinks()
            }
        
        if self._semanticist:
            status["semanticist"] = {
                "stats": self._semanticist.stats,
                "purpose_statements": len(self._semanticist.purpose_statements),
                "doc_drift_count": self._semanticist.stats["doc_drift_detected"],
                "domains": len(self._semanticist.domain_clusters),
                "cost": self._semanticist.budget.total_cost
            }
        
        if self._archivist:
            status["archivist"] = {
                "stats": self._archivist.stats,
                "artifacts": self._archivist.stats["artifacts_generated"],
                "traces": self._archivist.stats["traces_logged"]
            }
        
        # Check which artifacts exist
        artifacts = {}
        for filename in ["module_graph.json", "lineage_graph.json", "semantic_index.json", 
                        "CODEBASE.md", "onboarding_brief.md", "cartography_trace.jsonl"]:
            path = self.cache_dir / filename
            artifacts[filename] = path.exists()
        
        status["artifacts"] = artifacts
        
        return status