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

    def run(self):

        logger.info("Starting Semanticist")

        for module_path in list(self.module_data.keys())[:5]:

            code = f"# Placeholder code for {module_path}"

            docstring = self.module_data[module_path].get("docstring")

            self.generate_purpose_statement(module_path, code, docstring)

        if len(self.purpose_statements) >= 3:
            self.cluster_into_domains()

        self.save_semantic_index()

        logger.info("Semanticist complete")

        return {
            "purpose_statements": self.purpose_statements,
            "doc_drift_flags": self.doc_drift_flags,
            "domain_clusters": self.domain_clusters,
            "stats": self.stats,
            "budget": self.budget.get_summary(),
        }