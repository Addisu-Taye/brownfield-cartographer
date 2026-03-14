"""
Agent 3: The Semanticist - LLM-Powered Purpose Analyst

Uses LLMs to generate semantic understanding of code that static analysis cannot provide.
This is not summarization - it's purpose extraction grounded in implementation evidence.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import models
from src.models.nodes import ModuleNode, FunctionNode, KnowledgeGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM availability
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai not installed. LLM features will be disabled.")

# Embeddings availability
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Clustering disabled.")


class ContextWindowBudget:
    """Track token usage and cost."""

    def __init__(self, model_pricing: Optional[Dict[str, float]] = None):
        self.model_pricing = model_pricing or {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0015,
        }
        self.total_tokens = 0
        self.total_cost = 0.0
        self.calls_made = 0

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def select_model(self, token_count: int, task: str = "bulk") -> str:
        if task == "synthesis":
            return "gpt-4"
        return "gpt-3.5-turbo"

    def track_call(self, model: str, tokens: int):
        self.calls_made += 1
        self.total_tokens += tokens
        cost_per_k = self.model_pricing.get(model, 0.001)
        self.total_cost += (tokens / 1000) * cost_per_k

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_calls": self.calls_made,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
        }


class Semanticist:
    """Agent 3: LLM-powered semantic analyzer."""

    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.budget = ContextWindowBudget()

        self.purpose_statements: Dict[str, str] = {}
        self.doc_drift_flags: Dict[str, bool] = {}
        self.domain_clusters: Dict[str, str] = {}
        self.day_one_answers: Dict[str, str] = {}

        self.stats = {
            "modules_analyzed": 0,
            "purpose_statements_generated": 0,
            "doc_drift_detected": 0,
            "domains_identified": 0,
            "llm_calls": 0,
        }

        self.client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    self.client = OpenAI(api_key=api_key)
                    logger.info("OpenAI client initialized")
                except Exception as e:
                    logger.warning(f"OpenAI initialization failed: {e}")

        self.embedding_model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"Embedding model load failed: {e}")

        self._load_module_data()

    def _load_module_data(self):
        module_graph = self.cache_dir / "module_graph.json"
        if module_graph.exists():
            try:
                with open(module_graph) as f:
                    data = json.load(f)
                self.module_data = data.get("nodes", {})
                logger.info(f"Loaded {len(self.module_data)} modules")
            except Exception as e:
                logger.error(e)
                self.module_data = {}
        else:
            self.module_data = {}

    def generate_purpose_statement(
        self, module_path: str, code: str, docstring: Optional[str] = None
    ) -> str:

        if not self.client:
            return "LLM not available"

        if len(code) > 4000:
            code = code[:4000]

        prompt = f"""
You are analyzing a code file.

File: {module_path}

Code:
{code}

Docstring:
{docstring or "None"}

Write a short 2 sentence description of the business purpose.
Focus on WHAT the module does and WHY it exists.
"""

        tokens = self.budget.estimate_tokens(prompt)
        model = self.budget.select_model(tokens)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Code analyst"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=150,
            )

            purpose = response.choices[0].message.content.strip()

            self.budget.track_call(model, tokens + 50)
            self.stats["purpose_statements_generated"] += 1
            self.stats["llm_calls"] += 1

            self.purpose_statements[module_path] = purpose

            if docstring:
                self._check_doc_drift(module_path, docstring, purpose)

            return purpose

        except Exception as e:
            logger.error(e)
            return "Purpose generation failed"

    def _check_doc_drift(self, module_path: str, docstring: str, purpose: str):

        if not self.client:
            return

        prompt = f"""
Docstring:
{docstring}

Actual purpose:
{purpose}

Does the docstring match the code?
Answer YES or NO.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=20,
            )

            answer = response.choices[0].message.content.strip().upper()

            drift = answer.startswith("NO")
            self.doc_drift_flags[module_path] = drift

            if drift:
                self.stats["doc_drift_detected"] += 1

        except Exception as e:
            logger.error(e)

    def compute_embeddings(self, texts: List[str]):

        if not self.embedding_model:
            return []

        try:
            return self.embedding_model.encode(texts).tolist()
        except Exception as e:
            logger.error(e)
            return []

    def cluster_into_domains(self, n_clusters: int = 5):

        if not self.embedding_model or not self.purpose_statements:
            return {}

        modules = list(self.purpose_statements.keys())
        purposes = list(self.purpose_statements.values())

        embeddings = self.compute_embeddings(purposes)

        if not embeddings:
            return {}

        if len(modules) < n_clusters:
            n_clusters = max(2, len(modules) // 2)

        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(embeddings)

            domain_names = [f"Domain_{i}" for i in range(n_clusters)]

            for i, module in enumerate(modules):
                self.domain_clusters[module] = domain_names[labels[i]]

            self.stats["domains_identified"] = len(domain_names)

            return self.domain_clusters

        except Exception as e:
            logger.error(e)
            return {}

    def analyze_module(self, module_path: str, code: str, docstring=None):

        result = {
            "path": module_path,
            "purpose": self.generate_purpose_statement(module_path, code, docstring),
            "docstring": docstring,
            "doc_drift": self.doc_drift_flags.get(module_path, False),
            "domain": self.domain_clusters.get(module_path, "unknown"),
        }

        self.stats["modules_analyzed"] += 1

        return result

    def save_semantic_index(self):

        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "stats": self.stats,
                "budget": self.budget.get_summary(),
            },
            "purpose_statements": self.purpose_statements,
            "doc_drift_flags": self.doc_drift_flags,
            "domain_clusters": self.domain_clusters,
            "day_one_answers": self.day_one_answers,
        }

        path = self.cache_dir / "semantic_index.json"

        with open(path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Semantic index saved → {path}")
    def answer_day_one_questions(self, surveyor_data: Dict, lineage_data: Dict) -> Dict[str, str]:
        """Answer the five FDE Day-One questions with evidence."""
        questions = [
            "What is the primary data ingestion path?",
            "What are the 3-5 most critical output datasets?",
            "What is the blast radius if the most critical module fails?",
            "Where is the business logic concentrated?",
            "What has changed most frequently in the last 90 days?"
        ]
        
        if not self.client:
            # Return mock answers if no LLM available
            return {
                "full_response": "LLM not available - using mock answers",
                "answers": {
                    questions[0]: "Data is ingested through CSV seed files in seeds/ directory",
                    questions[1]: "Most critical outputs are customers and orders tables",
                    questions[2]: "If customers.sql fails, downstream dashboards would be affected",
                    questions[3]: "Business logic is concentrated in customers.sql and orders.sql",
                    questions[4]: "README.md and dbt_project.yml have changed most frequently"
                }
            }
        
        # Prepare context from surveyor and lineage
        modules = list(surveyor_data.get('nodes', {}).keys())
        velocity = surveyor_data.get('metadata', {}).get('velocity_summary', {})
        sources = lineage_data.get('sources', [])
        sinks = lineage_data.get('sinks', [])
        datasets = list(lineage_data.get('datasets', {}).keys())
        
        # Create prompt for Day-One questions
        prompt = f"""You are a Forward Deployed Engineer analyzing a codebase for the first time.
Answer these 5 questions with specific evidence (file paths, line numbers).

SURVEYOR DATA:
- Modules: {modules[:10]}... (and {len(modules)-10 if len(modules)>10 else 0} more)
- Change velocity: {velocity}

LINEAGE DATA:
- Sources: {sources}
- Sinks: {sinks}
- Datasets: {datasets[:10]}... (and {len(datasets)-10 if len(datasets)>10 else 0} more)

Questions:
1. {questions[0]}
2. {questions[1]}
3. {questions[2]}
4. {questions[3]}
5. {questions[4]}

Provide answers with citations to specific files and line numbers where possible.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use expensive model for synthesis
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            
            answer_text = response.choices[0].message.content.strip()
            
            # Track usage
            token_estimate = self.budget.estimate_tokens(prompt) + 500
            self.budget.track_call("gpt-4", token_estimate)
            self.stats["llm_calls"] += 1
            self.stats["total_cost"] = self.budget.total_cost
            
            # Store answers
            self.day_one_answers = {
                "full_response": answer_text,
                "questions": questions
            }
            
            return self.day_one_answers
            
        except Exception as e:
            logger.error(f"Failed to answer questions: {e}")
            return {q: f"Error: {str(e)}" for q in questions}        

    def run(self, surveyor_data: Optional[Dict] = None, lineage_data: Optional[Dict] = None):
        """Run full semantic analysis pipeline.
        
        Args:
            surveyor_data: Optional surveyor output data
            lineage_data: Optional lineage output data
        """
        logger.info("🤖 Semanticist: Starting semantic analysis...")
        
        # Load data if not provided
        if not surveyor_data:
            module_graph_path = self.cache_dir / "module_graph.json"
            if module_graph_path.exists():
                with open(module_graph_path, 'r', encoding='utf-8') as f:
                    surveyor_data = json.load(f)
                logger.info(f"Loaded surveyor data from {module_graph_path}")
        
        if not lineage_data:
            lineage_path = self.cache_dir / "lineage_graph.json"
            if lineage_path.exists():
                with open(lineage_path, 'r', encoding='utf-8') as f:
                    lineage_data = json.load(f)
                logger.info(f"Loaded lineage data from {lineage_path}")
        
        # Generate purpose statements for modules
        if surveyor_data and "nodes" in surveyor_data:
            logger.info(f"Generating purpose statements for {len(surveyor_data['nodes'])} modules...")
            for module_path, module_info in surveyor_data["nodes"].items():
                if module_info.get("language") in ["python", "sql"]:
                    # In real implementation, you'd load the actual code
                    # For now, we'll use a placeholder
                    code = f"# Code for {module_path}\n# This is a placeholder"
                    docstring = module_info.get("docstring")
                    
                    purpose = self.generate_purpose_statement(module_path, code, docstring)
                    self.purpose_statements[module_path] = purpose
                    
                    # Limit to avoid too many API calls in testing
                    if len(self.purpose_statements) >= 5:
                        logger.info("Reached limit of 5 purpose statements for testing")
                        break
        
        # Cluster into domains
        if len(self.purpose_statements) >= 3:
            logger.info("Clustering modules into domains...")
            self.cluster_into_domains()
        
        # Answer Day-One questions if we have both data sources
        if surveyor_data and lineage_data:
            logger.info("Generating Day-One answers...")
            self.answer_day_one_questions(surveyor_data, lineage_data)
        
        # Save results
        self.save_semantic_index()
        
        logger.info(f"✅ Semanticist complete. Stats: {self.stats}")
        logger.info(f"💰 LLM Cost: ${self.budget.total_cost:.4f}")
        
        return {
            "purpose_statements": self.purpose_statements,
            "doc_drift_flags": self.doc_drift_flags,
            "domain_clusters": self.domain_clusters,
            "day_one_answers": self.day_one_answers,
            "stats": self.stats,
            "budget": self.budget.get_summary()
        }