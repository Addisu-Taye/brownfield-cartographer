"""Agent 3: The Semanticist - LLM-Powered Purpose Analyst

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
    
    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
        self.calls_made = 0
        self.model_pricing = {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0015,
        }
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // 4
    
    def select_model(self, tokens: int) -> str:
        """Select model based on token count."""
        if tokens < 2000:
            return "gpt-3.5-turbo"
        return "gpt-4"
    
    def track_call(self, model: str, tokens: int):
        """Track token usage and cost."""
        self.calls_made += 1
        self.total_tokens += tokens
        cost_per_k = self.model_pricing.get(model, 0.0015)
        self.total_cost += (tokens / 1000) * cost_per_k
    
    def get_summary(self) -> Dict:
        """Get budget summary."""
        return {
            "total_calls": self.calls_made,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4)
        }


class Semanticist:
    """Agent 3: LLM-Powered Purpose Analyst
    
    Uses LLMs to generate semantic understanding:
    - Purpose statements for modules
    - Documentation drift detection
    - Domain clustering
    - Answering FDE Day-One questions
    """
    
    def __init__(self, repo_path: str, cache_dir: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = cache_dir or self.repo_path / ".cartography"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize budget tracker
        self.budget = ContextWindowBudget()
        
        # Storage for semantic data
        self.purpose_statements: Dict[str, str] = {}
        self.doc_drift_flags: Dict[str, bool] = {}
        self.domain_clusters: Dict[str, str] = {}
        self.embeddings_cache: Dict[str, List[float]] = {}
        self.day_one_answers: Dict[str, str] = {}
        
        # Statistics
        self.stats = {
            "modules_analyzed": 0,
            "purpose_statements_generated": 0,
            "doc_drift_detected": 0,
            "domains_identified": 0,
            "llm_calls": 0,
            "total_cost": 0.0
        }
        
        # Load existing module data if available
        self._load_module_data()
        
        # Try to load API key from .env file (multiple methods)
        api_key = None
        
        # Method 1: Check environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            logger.info("✅ Found API key in environment variables")
        
        # Method 2: Try to load from .env file in project root
        if not api_key:
            try:
                env_path = Path(__file__).parent.parent.parent / '.env'
                if env_path.exists():
                    logger.info(f"📄 Found .env file at: {env_path}")
                    with open(env_path, 'r') as f:
                        for line in f:
                            if line.startswith('OPENAI_API_KEY='):
                                api_key = line.strip().split('=', 1)[1].strip('"').strip("'")
                                logger.info(f"✅ Loaded API key from .env file (starts with: {api_key[:10]}...)")
                                break
            except Exception as e:
                logger.debug(f"Error reading .env file: {e}")
        
        # Method 3: Try using dotenv if available
        if not api_key:
            try:
                from dotenv import load_dotenv
                env_path = Path(__file__).parent.parent.parent / '.env'
                if env_path.exists():
                    load_dotenv(env_path)
                    api_key = os.environ.get("OPENAI_API_KEY")
                    if api_key:
                        logger.info(f"✅ Loaded API key via dotenv from {env_path}")
            except ImportError:
                logger.debug("python-dotenv not installed, skipping")
        
        # Initialize OpenAI client if available
        self.client = None
        if OPENAI_AVAILABLE:
            if api_key and len(api_key) > 20 and not api_key.startswith('sk11'):
                try:
                    self.client = OpenAI(api_key=api_key)
                    logger.info("✅ OpenAI client initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI client: {e}")
            else:
                logger.warning("⚠️ No valid API key found. LLM features will be disabled.")
        else:
            logger.warning("⚠️ OpenAI SDK not installed. LLM features will be disabled.")
        
        # Initialize embedding model if available
        self.embedding_model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ SentenceTransformer model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
        else:
            logger.warning("⚠️ Sentence-transformers not installed. Domain clustering disabled.")
    
    def _load_module_data(self):
        """Load module data from surveyor output."""
        module_graph = self.cache_dir / "module_graph.json"
        if module_graph.exists():
            try:
                with open(module_graph, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.module_data = data.get("nodes", {})
                logger.info(f"Loaded {len(self.module_data)} modules from surveyor")
            except Exception as e:
                logger.error(f"Error loading module data: {e}")
                self.module_data = {}
        else:
            self.module_data = {}
            logger.warning("No module graph found. Run Surveyor first.")
    
    def generate_purpose_statement(
        self, module_path: str, code: str, docstring: Optional[str] = None
    ) -> str:
        """Generate a purpose statement for a module using LLM."""
        if not self.client:
            return "LLM not available - set valid API key"
        
        if len(code) > 4000:
            code = code[:4000] + "... (truncated)"
        
        # Detect language for better prompting
        language = "unknown"
        if module_path.endswith('.py'):
            language = "python"
        elif module_path.endswith('.sql'):
            language = "SQL"
        elif module_path.endswith(('.yml', '.yaml')):
            language = "YAML"
        
        prompt = f"""You are analyzing a {language} file to understand its business purpose, not its implementation details.

File: {module_path}

Code:{language}
{code}
Original docstring (if any):
{docstring or "None"}

Task: Write a 2-3 sentence purpose statement explaining:

What business function this module performs

What are its inputs/outputs (if applicable)

Why it exists in the system

Focus on the WHAT and WHY, not the HOW. Be concise and specific.
"""

        tokens = self.budget.estimate_tokens(prompt)
        model = self.budget.select_model(tokens)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a code analyst focused on business purpose."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=150,
            )

            purpose = response.choices[0].message.content.strip()

            self.budget.track_call(model, tokens + 50)
            self.stats["purpose_statements_generated"] += 1
            self.stats["llm_calls"] += 1
            self.stats["total_cost"] = self.budget.total_cost

            self.purpose_statements[module_path] = purpose

            if docstring and docstring.strip():
                self._check_doc_drift(module_path, docstring, purpose)

            return purpose

        except Exception as e:
            logger.error(f"Purpose generation failed: {e}")
            return f"Error generating purpose: {str(e)}"

    def _check_doc_drift(self, module_path: str, docstring: str, purpose: str):
        """Check if docstring contradicts the actual purpose."""
        if not self.client:
            return

        prompt = f"""Compare the original docstring with the actual purpose of this module.

Original docstring:
{docstring}

Actual purpose (from code analysis):
{purpose}

Question: Does the docstring accurately describe what this module does?
Answer with just "YES" or "NO" and a one-sentence explanation.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )

            answer = response.choices[0].message.content.strip()
            has_drift = answer.upper().startswith("NO")

            self.doc_drift_flags[module_path] = has_drift
            if has_drift:
                self.stats["doc_drift_detected"] += 1
                logger.debug(f"Documentation drift detected in {module_path}")

        except Exception as e:
            logger.error(f"Drift check failed: {e}")

    def compute_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for clustering."""
        if not self.embedding_model:
            return []

        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    def cluster_into_domains(self, n_clusters: int = 5) -> Dict[str, str]:
        """Cluster modules into business domains based on purpose statements."""
        if not self.embedding_model or not self.purpose_statements:
            logger.warning("Cannot cluster: missing embeddings or purpose statements")
            return {}

        # Prepare data
        module_paths = list(self.purpose_statements.keys())
        purposes = list(self.purpose_statements.values())

        if len(module_paths) < 2:
            logger.warning(f"Not enough modules for clustering: {len(module_paths)}")
            return {}

        if len(module_paths) < n_clusters:
            n_clusters = max(2, len(module_paths) // 2)

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(module_paths)} modules...")
        embeddings = self.compute_embeddings(purposes)
        if not embeddings or len(embeddings) == 0:
            logger.error("Failed to generate embeddings")
            return {}

        # Cluster
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            # Generate domain names for each cluster
            domain_names = [f"Domain_{i+1}" for i in range(n_clusters)]

            # Map modules to domains
            for i, module_path in enumerate(module_paths):
                cluster_id = labels[i]
                self.domain_clusters[module_path] = domain_names[cluster_id]

            self.stats["domains_identified"] = len(set(domain_names))
            logger.info(f"Clustered modules into {self.stats['domains_identified']} domains")
            return self.domain_clusters

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return {}

    def analyze_module(self, module_path: str, code: str, docstring=None) -> Dict:
        """Analyze a single module."""
        result = {
            "path": module_path,
            "purpose": self.generate_purpose_statement(module_path, code, docstring),
            "docstring": docstring,
            "doc_drift": self.doc_drift_flags.get(module_path, False),
            "domain": self.domain_clusters.get(module_path, "unknown"),
        }

        self.stats["modules_analyzed"] += 1

        return result

    def save_semantic_index(self) -> None:
        """Save semantic index to disk."""
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

        with open(path, 'w', encoding='utf-8') as f:
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
Modules: {modules[:10]}... (and {len(modules)-10 if len(modules)>10 else 0} more)
Change velocity: {velocity}

LINEAGE DATA:
Sources: {sources}
Sinks: {sinks}
Datasets: {datasets[:10]}... (and {len(datasets)-10 if len(datasets)>10 else 0} more)

Questions:
{questions[0]}
{questions[1]}
{questions[2]}
{questions[3]}
{questions[4]}

Provide answers with citations to specific files and line numbers where possible.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
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
        """Run full semantic analysis pipeline."""
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
            logger.info(f"Found {len(surveyor_data['nodes'])} modules in surveyor data")

            # Filter to include SQL and YAML files as well
            modules_to_analyze = []
            for module_path, module_info in surveyor_data["nodes"].items():
                language = module_info.get("language", "unknown")
                if language in ["python", "sql", "yaml"]:
                    modules_to_analyze.append((module_path, module_info))

            logger.info(f"Analyzing {len(modules_to_analyze)} modules (SQL/YAML/Python)...")

            for module_path, module_info in modules_to_analyze:
                # Try to read the actual file content
                try:
                    full_path = self.repo_path / module_path
                    if full_path.exists():
                        with open(full_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                        logger.info(f"📝 Analyzing {module_path} ({module_info.get('language')})...")
                    else:
                        code = f"-- File not found: {module_path}"
                        logger.warning(f"File not found: {module_path}")
                except Exception as e:
                    code = f"-- Error reading file: {e}"
                    logger.debug(f"Could not read {module_path}: {e}")

                docstring = module_info.get("docstring")

                purpose = self.generate_purpose_statement(module_path, code, docstring)
                self.purpose_statements[module_path] = purpose

                # Limit to avoid too many API calls (remove this limit for production)
                if len(self.purpose_statements) >= 10:
                    logger.info("Reached limit of 10 purpose statements")
                    break

        # Cluster into domains if we have enough purpose statements
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