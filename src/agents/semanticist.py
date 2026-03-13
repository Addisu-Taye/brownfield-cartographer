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
import hashlib

# Models
from src.models.nodes import ModuleNode, FunctionNode, KnowledgeGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Optional LLM imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not installed. LLM functionality disabled.")


# Optional embedding imports
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.cluster import KMeans
    EMBEDDINGS_AVAILABLE = True
except Exception:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("Sentence-transformers not installed. Domain clustering disabled.")


# -------------------------------------------------------------------
# Context Budget Tracker
# -------------------------------------------------------------------

class ContextWindowBudget:
    """Tracks token usage and estimated cost."""

    def __init__(self, model_pricing: Optional[Dict[str, float]] = None):
        self.model_pricing = model_pricing or {
            "gpt-4o-mini": 0.00015,
            "gpt-4": 0.03,
            "mistral": 0.0002,
        }

        self.total_tokens = 0
        self.total_cost = 0.0
        self.calls_made = 0

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def track_call(self, model: str, tokens: int):

        self.calls_made += 1
        self.total_tokens += tokens

        cost_per_k = self.model_pricing.get(model, 0.0001)
        self.total_cost += (tokens / 1000) * cost_per_k

    def get_summary(self):

        return {
            "calls": self.calls_made,
            "tokens": self.total_tokens,
            "cost_usd": round(self.total_cost, 4),
        }


# -------------------------------------------------------------------
# Agent 3 – Semanticist
# -------------------------------------------------------------------

class Semanticist:
    """
    Agent 3: LLM-Powered Purpose Analyst
    """

    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):

        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.budget = ContextWindowBudget()

        self.purpose_statements: Dict[str, str] = {}
        self.doc_drift_flags: Dict[str, bool] = {}
        self.domain_clusters: Dict[str, str] = {}
        self.embeddings: Dict[str, List[float]] = {}

        self.stats = {
            "modules_analyzed": 0,
            "purpose_statements_generated": 0,
            "doc_drift_detected": 0,
            "domains_identified": 0,
            "llm_calls": 0,
        }

        self._load_module_data()

        self.client = None
        if OPENAI_AVAILABLE:

            api_key = os.getenv("OPENAI_API_KEY")

            if api_key:
                self.client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OPENAI_API_KEY not set")

        self.embedding_model = None
        if EMBEDDINGS_AVAILABLE:

            try:
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Embedding model loaded")

            except Exception as e:
                logger.warning(f"Embedding model failed: {e}")

    # -------------------------------------------------------------------
    # Load module data
    # -------------------------------------------------------------------

    def _load_module_data(self):

        module_graph_path = self.cache_dir / "module_graph.json"

        if not module_graph_path.exists():
            logger.warning("Module graph not found. Run Surveyor first.")
            self.module_data = {}
            return

        try:

            with open(module_graph_path) as f:
                data = json.load(f)

            self.module_data = data.get("nodes", {})
            logger.info(f"Loaded {len(self.module_data)} modules")

        except Exception as e:

            logger.error(f"Module load failed: {e}")
            self.module_data = {}

    # -------------------------------------------------------------------
    # Purpose Statement
    # -------------------------------------------------------------------

    def generate_purpose_statement(
        self,
        module_path: str,
        code: str,
        docstring: Optional[str] = None,
    ) -> str:

        if not self.client:
            return "LLM unavailable"

        if len(code) > 4000:
            code = code[:4000] + "\n...truncated..."

        prompt = f"""
You are a senior software architect analyzing a production codebase.

File:
{module_path}

Code:
{code}

Original docstring:
{docstring or "None"}

Write a concise 2–3 sentence purpose statement describing:

• What business function this module performs  
• Inputs and outputs  
• Why it exists in the system

Focus on WHAT and WHY — not implementation details.
"""

        tokens = self.budget.estimate_tokens(prompt)

        try:

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Expert software architect"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            result = response.choices[0].message.content.strip()

            self.budget.track_call("gpt-4o-mini", tokens)

            self.stats["purpose_statements_generated"] += 1
            self.stats["llm_calls"] += 1

            return result

        except Exception as e:

            logger.error(f"Purpose generation failed: {e}")
            return "Purpose generation failed"

    # -------------------------------------------------------------------
    # Documentation Drift
    # -------------------------------------------------------------------

    def detect_doc_drift(self, docstring: str, purpose: str) -> bool:

        if not self.client:
            return False

        prompt = f"""
Compare the documentation with the real module purpose.

Docstring:
{docstring}

Actual purpose:
{purpose}

Does the docstring accurately describe the module?

Answer YES or NO.
"""

        tokens = self.budget.estimate_tokens(prompt)

        try:

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            answer = response.choices[0].message.content.upper()

            drift = "NO" in answer

            if drift:
                self.stats["doc_drift_detected"] += 1

            self.budget.track_call("gpt-4o-mini", tokens)

            return drift

        except Exception:

            return False

    # -------------------------------------------------------------------
    # Embedding Generation
    # -------------------------------------------------------------------

    def compute_embeddings(self):

        if not self.embedding_model:
            return

        texts = list(self.purpose_statements.values())

        if not texts:
            return

        vectors = self.embedding_model.encode(texts)

        for module, vec in zip(self.purpose_statements.keys(), vectors):
            self.embeddings[module] = vec.tolist()

    # -------------------------------------------------------------------
    # Domain Clustering
    # -------------------------------------------------------------------

    def cluster_domains(self, k: int = 5):

        if not EMBEDDINGS_AVAILABLE:
            return

        if not self.embeddings:
            return

        modules = list(self.embeddings.keys())

        vectors = np.array(list(self.embeddings.values()))

        kmeans = KMeans(n_clusters=min(k, len(vectors)))
        labels = kmeans.fit_predict(vectors)

        for module, label in zip(modules, labels):
            self.domain_clusters[module] = f"domain_{label}"

        self.stats["domains_identified"] = len(set(labels))

    # -------------------------------------------------------------------
    # FDE Questions
    # -------------------------------------------------------------------

    def generate_fde_questions(self, surveyor_data: Dict, lineage_data: Dict) -> str:

        if not self.client:
            return "LLM unavailable"

        prompt = f"""
You are a Forward Deployed Engineer analyzing a codebase.

Modules:
{list(surveyor_data.get("nodes", {}).keys())}

Sources:
{lineage_data.get("sources", [])}

Sinks:
{lineage_data.get("sinks", [])}

Answer these:

1. Primary ingestion path
2. Critical outputs
3. Failure blast radius
4. Where business logic lives
5. What changed most recently

Cite modules.
"""

        try:

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            return response.choices[0].message.content

        except Exception as e:

            logger.error(e)
            return "FDE analysis failed"

    # -------------------------------------------------------------------
    # Main Analysis
    # -------------------------------------------------------------------

    def analyze(self):

        logger.info("Running Semanticist analysis...")

        for module_path, module_data in self.module_data.items():

            code = module_data.get("code", "")
            docstring = module_data.get("docstring")

            purpose = self.generate_purpose_statement(
                module_path,
                code,
                docstring,
            )

            self.purpose_statements[module_path] = purpose

            if docstring:
                drift = self.detect_doc_drift(docstring, purpose)
                self.doc_drift_flags[module_path] = drift

        self.compute_embeddings()
        self.cluster_domains()

        self.stats["modules_analyzed"] = len(self.module_data)

        logger.info("Semantic analysis completed")

    # -------------------------------------------------------------------
    # Save Results
    # -------------------------------------------------------------------

    def save_results(self):

        output = {
            "purpose_statements": self.purpose_statements,
            "doc_drift": self.doc_drift_flags,
            "domain_clusters": self.domain_clusters,
            "stats": self.stats,
            "budget": self.budget.get_summary(),
        }

        path = self.cache_dir / "semantic_analysis.json"

        with open(path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Semantic results saved → {path}")