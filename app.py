#!/usr/bin/env python
"""Brownfield Cartographer - Web Frontend

A modern web interface for visualizing and querying codebase intelligence.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
import plotly
import plotly.graph_objs as go
import plotly.express as px
import networkx as nx
import pandas as pd

from src.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Store orchestrator instances per repo (in production, use a database)
orchestrators = {}


def get_orchestrator(repo_path):
    """Get or create orchestrator for a repo."""
    repo_path = str(Path(repo_path).resolve())
    if repo_path not in orchestrators:
        try:
            orchestrators[repo_path] = Orchestrator(repo_path)
            logger.info(f"Created orchestrator for {repo_path}")
        except Exception as e:
            logger.error(f"Failed to create orchestrator: {e}")
            return None
    return orchestrators[repo_path]


@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')


@app.route('/api/repos', methods=['POST'])
def add_repo():
    """Add a repository to analyze."""
    data = request.json
    repo_path = data.get('repo_path', '').strip()
    
    if not repo_path:
        return jsonify({'error': 'Repository path is required'}), 400
    
    repo_path = Path(repo_path).resolve()
    if not repo_path.exists():
        return jsonify({'error': f'Repository path does not exist: {repo_path}'}), 400
    
    # Store in session
    session['repo_path'] = str(repo_path)
    
    return jsonify({
        'status': 'ok',
        'repo_path': str(repo_path),
        'message': 'Repository added successfully'
    })


@app.route('/api/analyze/<path:repo_path>', methods=['POST'])
def analyze_repo(repo_path):
    """Run analysis on a repository."""
    data = request.json
    phase = data.get('phase', 'all')
    
    orchestrator = get_orchestrator(repo_path)
    if not orchestrator:
        return jsonify({'error': 'Failed to initialize orchestrator'}), 500
    
    try:
        if phase == '1':
            result = orchestrator.run_phase1()
        elif phase == '2':
            result = orchestrator.run_phase2()
        elif phase == '3':
            result = orchestrator.run_phase3()
        elif phase == '4':
            result = orchestrator.run_phase4()
        else:
            result = orchestrator.run_full_analysis()
        
        status = orchestrator.get_status()
        
        return jsonify({
            'status': 'ok',
            'phase': phase,
            'result': result,
            'status': status
        })
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status/<path:repo_path>')
def get_status(repo_path):
    """Get analysis status for a repository."""
    orchestrator = get_orchestrator(repo_path)
    if not orchestrator:
        return jsonify({'error': 'Failed to initialize orchestrator'}), 500
    
    try:
        status = orchestrator.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/query/<path:repo_path>', methods=['POST'])
def query_repo(repo_path):
    """Query the knowledge graph."""
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    orchestrator = get_orchestrator(repo_path)
    if not orchestrator:
        return jsonify({'error': 'Failed to initialize orchestrator'}), 500
    
    try:
        result = orchestrator.query(question)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/lineage/<path:repo_path>/<dataset>')
def get_lineage_viz(repo_path, dataset):
    """Get lineage visualization data for a dataset."""
    orchestrator = get_orchestrator(repo_path)
    if not orchestrator:
        return jsonify({'error': 'Failed to initialize orchestrator'}), 500
    
    try:
        # Get lineage data
        upstream_result = orchestrator.query(f"trace lineage of {dataset} upstream")
        downstream_result = orchestrator.query(f"trace lineage of {dataset} downstream")
        
        # Extract paths
        upstream_path = []
        downstream_path = []
        
        if 'result' in upstream_result and 'path' in upstream_result['result']:
            upstream_path = upstream_result['result']['path']
        
        if 'result' in downstream_result and 'path' in downstream_result['result']:
            downstream_path = downstream_result['result']['path']
        
        # Create graph visualization
        G = nx.DiGraph()
        
        # Add nodes and edges
        all_nodes = set(upstream_path + downstream_path + [dataset])
        for node in all_nodes:
            G.add_node(node)
        
        # Add edges for upstream (reverse direction for visualization)
        for i in range(len(upstream_path) - 1):
            G.add_edge(upstream_path[i + 1], upstream_path[i])
        
        # Add edges for downstream
        for i in range(len(downstream_path) - 1):
            G.add_edge(downstream_path[i], downstream_path[i + 1])
        
        # Create Plotly figure
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Create edge trace
        edge_trace = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace.append(go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                line=dict(width=1, color='#888'),
                hoverinfo='none',
                mode='lines'
            ))
        
        # Create node trace
        node_x = []
        node_y = []
        node_colors = []
        node_sizes = []
        node_text = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Color based on node type
            if node == dataset:
                node_colors.append('red')
                node_sizes.append(30)
                node_text.append(f"<b>{node}</b> (selected)")
            elif node in upstream_path:
                node_colors.append('lightblue')
                node_sizes.append(20)
                node_text.append(f"{node}<br>⬆️ Upstream")
            elif node in downstream_path:
                node_colors.append('lightgreen')
                node_sizes.append(20)
                node_text.append(f"{node}<br>⬇️ Downstream")
            else:
                node_colors.append('gray')
                node_sizes.append(15)
                node_text.append(node)
        
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            text=list(G.nodes()),
            textposition="top center",
            hoverinfo='text',
            hovertext=node_text,
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='darkblue')
            )
        )
        
        # Create figure
        fig = go.Figure(
            data=edge_trace + [node_trace],
            layout=go.Layout(
                title=f'📊 Lineage Graph: {dataset}',
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='white'
            )
        )
        
        return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))
        
    except Exception as e:
        logger.error(f"Lineage visualization failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/datasets/<path:repo_path>')
def get_datasets(repo_path):
    """Get all datasets from lineage graph."""
    orchestrator = get_orchestrator(repo_path)
    if not orchestrator:
        return jsonify({'error': 'Failed to initialize orchestrator'}), 500
    
    try:
        status = orchestrator.get_status()
        hydrologist = status.get('hydrologist', {})
        
        datasets = []
        for name, info in hydrologist.get('datasets', {}).items():
            datasets.append({
                'name': name,
                'type': info.get('type', 'unknown'),
                'files': info.get('files', [])
            })
        
        return jsonify({
            'datasets': sorted(datasets, key=lambda x: x['name']),
            'sources': hydrologist.get('sources', []),
            'sinks': hydrologist.get('sinks', [])
        })
    except Exception as e:
        logger.error(f"Failed to get datasets: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/modules/<path:repo_path>')
def get_modules(repo_path):
    """Get all modules from surveyor."""
    orchestrator = get_orchestrator(repo_path)
    if not orchestrator:
        return jsonify({'error': 'Failed to initialize orchestrator'}), 500
    
    try:
        status = orchestrator.get_status()
        surveyor = status.get('surveyor', {})
        
        return jsonify({
            'modules': surveyor.get('nodes_count', 0),
            'python_files': surveyor.get('stats', {}).get('python_files', 0),
            'sql_files': surveyor.get('stats', {}).get('sql_files', 0),
            'yaml_files': surveyor.get('stats', {}).get('yaml_files', 0)
        })
    except Exception as e:
        logger.error(f"Failed to get modules: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/semantic/<path:repo_path>')
def get_semantic(repo_path):
    """Get semantic analysis results."""
    orchestrator = get_orchestrator(repo_path)
    if not orchestrator:
        return jsonify({'error': 'Failed to initialize orchestrator'}), 500
    
    try:
        status = orchestrator.get_status()
        semantic = status.get('semanticist', {})
        
        # Load full semantic index
        semantic_path = Path(repo_path) / '.cartography' / 'semantic_index.json'
        if semantic_path.exists():
            with open(semantic_path, 'r', encoding='utf-8') as f:
                full_semantic = json.load(f)
        else:
            full_semantic = {}
        
        return jsonify({
            'stats': semantic,
            'purposes': full_semantic.get('purpose_statements', {}),
            'domains': full_semantic.get('domain_clusters', {}),
            'drift': full_semantic.get('doc_drift_flags', {})
        })
    except Exception as e:
        logger.error(f"Failed to get semantic data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/artifact/<path:repo_path>/<artifact>')
def get_artifact(repo_path, artifact):
    """Get a specific artifact file."""
    try:
        # Security: prevent directory traversal
        safe_artifact = Path(artifact).name
        artifact_path = Path(repo_path) / '.cartography' / safe_artifact
        
        if not artifact_path.exists():
            return jsonify({'error': 'Artifact not found'}), 404
        
        # Only allow specific file types
        allowed_extensions = ['.json', '.md', '.jsonl']
        if artifact_path.suffix.lower() not in allowed_extensions:
            return jsonify({'error': 'File type not allowed'}), 403
        
        return send_file(artifact_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Failed to get artifact: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)