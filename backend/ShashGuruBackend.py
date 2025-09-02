#This file is part of ShashGuru, a chess analyzer that takes a FEN, asks a UCI chess engine to analyse it and then outputs a natural language analysis made by an LLM.
#Copyright (C) 2025  Alessandro Libralesso
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.

from flask import Flask, request, Response, stream_with_context, jsonify, json
from prometheus_client import Summary, Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask_cors import CORS
import argparse
import logging 
import time
from functools import wraps


import LLMHandler
import engineCommunication
from engineCache import get_cache

# Prometheus metrics
REQUEST_COUNT = Counter(
    'shashguru_requests_total',
    'Total number of requests by endpoint',
    ['endpoint', 'method', 'status']
)

REQUEST_DURATION = Summary(
    'shashguru_request_duration_seconds',
    'Request duration in seconds by endpoint',
    ['endpoint', 'method']
)

ACTIVE_REQUESTS = Gauge(
    'shashguru_active_requests',
    'Number of active requests by endpoint',
    ['endpoint']
)

ERROR_COUNT = Counter(
    'shashguru_errors_total',
    'Total number of errors by endpoint',
    ['endpoint', 'error_type']
)

# Global variables for model and tokenizer
tokenizer = None
model = None

def track_metrics(endpoint_name):
    """Decorator to track metrics for endpoints"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            method = request.method
            start_time = time.time()
            
            # Increment active requests
            ACTIVE_REQUESTS.labels(endpoint=endpoint_name).inc()
            
            try:
                # Execute the function
                response = func(*args, **kwargs)
                
                # Determine status code
                if hasattr(response, 'status_code'):
                    status = str(response.status_code)
                elif isinstance(response, tuple) and len(response) > 1:
                    status = str(response[1])
                else:
                    status = '200'
                
                # Record successful request
                REQUEST_COUNT.labels(endpoint=endpoint_name, method=method, status=status).inc()
                
                return response
                
            except Exception as e:
                # Record error
                error_type = type(e).__name__
                REQUEST_COUNT.labels(endpoint=endpoint_name, method=method, status='500').inc()
                ERROR_COUNT.labels(endpoint=endpoint_name, error_type=error_type).inc()
                raise
                
            finally:
                # Record duration and decrement active requests
                duration = time.time() - start_time
                REQUEST_DURATION.labels(endpoint=endpoint_name, method=method).observe(duration)
                ACTIVE_REQUESTS.labels(endpoint=endpoint_name).dec()
        
        return wrapper
    return decorator

def load_models():
    """Load the LLM model and tokenizer - called once at startup"""
    global tokenizer, model
    if tokenizer is None or model is None:
        logging.info("Loading LLM model...")
        tokenizer, model = LLMHandler.load_LLM_model()
        logging.info("Model loaded successfully.")

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    CORS(app)
    
    # Load models when creating the app
    load_models()
    
    return app

app = create_app()


@app.route("/health", methods=['GET'])
def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "tokenizer_loaded": tokenizer is not None
    }), 200


@app.route("/metrics", methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/analysis", methods=['GET', 'POST'])
@track_metrics('analysis')
def analysis():
    fen = request.json.get('fen')  
    print("Received analysis request for:", fen)
    depth = request.json.get('depth', 20)
    style = request.json.get('style', 'default')

    # Request 3 lines for multiple move analysis
    bestmoves, ponder = engineCommunication.call_engine(fen, depth, lines=3)
    prompt = LLMHandler.create_prompt_single_engine(fen, bestmoves, ponder, style)

    ############################
    #  Questo è per due engine #
    ############################
    #engine_analysis = engineCommunication.engines(fen, depth)
    #prompt = LLMHandler.create_prompt_double_engine(fen, engine_analysis)

    def generate():
        yield json.dumps({"prompt": prompt}) + "\n[PROMPT_END]\n" # sends single chunk with prompt, to save it as context for responses
        yield "[START_STREAM]\n"  # optional: delimiter for stream start
        for token in LLMHandler.stream_LLM(prompt, model, style=style):  # <-- stream here
            yield token
        yield "\n[END_STREAM]"  # optional: delimiter for stream end 
    
    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route("/response", methods=['GET','POST'])
@track_metrics('response')
def response():
    chat_history = request.get_json()
    if chat_history is None:
        chat_history = [] 
    new_question = chat_history[-1].get("content")
    style = request.args.get('style', 'default')  # Get style from query parameters
    print('Received question:' , new_question)

    def generate():
        yield "[START_STREAM]\n"
        for token in LLMHandler.stream_LLM(new_question, model, chat_history=chat_history[:-1], style=style):
            yield token
        yield "\n[END_STREAM]"

    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route("/evaluation", methods=['GET', 'POST'])
@track_metrics('evaluation')
def evaluation():
    """
    Returns engine evaluation for a given FEN position.
    
    Expected JSON payload:
    {
        "fen": "string",
        "depth": int (optional, default: 15),
        "lines": int (optional, default: 3)
    }
    
    Returns JSON with evaluation data including score, best moves, etc.
    """
    try:
        data = request.get_json()
        fen = data.get('fen')
        depth = data.get('depth', 15)
        lines = data.get('lines', 3)
        
        if not fen:
            return jsonify({"error": "FEN is required"}), 400
            
        print(f"Received evaluation request for FEN: {fen}, depth: {depth}, lines: {lines}")
        
        # Get engine analysis
        bestmoves, ponder = engineCommunication.call_engine(fen, depth, lines=lines)
        
        # Format the response to match frontend expectations
        evaluation_data = {
            "evaluation": {
                "move": bestmoves[0]['move'] if bestmoves else None,
                "score": bestmoves[0]['score'] if bestmoves else None,
                "mate": bestmoves[0]['mate'] if bestmoves else None,
                "winprob": bestmoves[0]['winprob'] if bestmoves else None,
                "lines": [
                    {
                        "moves": ' '.join(move_data['pv_moves']) if 'pv_moves' in move_data and move_data['pv_moves'] else move_data['move'],
                        "evaluation": move_data['score'] if move_data['score'] is not None else (1000 + move_data['mate'] if move_data['mate'] is not None else 0)
                    }
                    for move_data in bestmoves[:lines]
                ]
            }
        }
        
        return jsonify(evaluation_data)
        
    except Exception as e:
        print(f"Error in evaluation endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/cache/stats", methods=['GET'])
def cache_stats():
    """
    Returns cache statistics.
    """
    try:
        cache = get_cache()
        stats = cache.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/cache/clear", methods=['POST'])
def clear_cache():
    """
    Clears all cached analysis data.
    """
    try:
        cache = get_cache()
        cache.clear_cache()
        return jsonify({"message": "Cache cleared successfully"})
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/pgn-analysis", methods=['POST'])
@track_metrics('pgn_analysis')
def pgn_analysis():
    """
    Analyzes a complete PGN game using a dedicated engine instance.
    More efficient for game analysis as the engine can reuse hash table entries.
    
    Expected JSON payload:
    {
        "pgn": "string" (PGN format game) OR "moves": ["e2e4", "e7e5", ...] (UCI moves),
        "depth": int (optional, default: 15),
        "lines": int (optional, default: 3),
        "engine": "NNUE" or "HUMAN" (optional, default: "NNUE")
    }
    
    Returns JSON with analysis for each position in the game.
    """
    try:
        data = request.get_json()
        
        # Get PGN or moves
        pgn_string = data.get('pgn')
        moves_list = data.get('moves')
        
        if not pgn_string and not moves_list:
            return jsonify({"error": "Either 'pgn' or 'moves' is required"}), 400
            
        if pgn_string and moves_list:
            return jsonify({"error": "Provide either 'pgn' or 'moves', not both"}), 400
        
        # Get optional parameters
        depth = data.get('depth', 15)
        lines = data.get('lines', 3)
        engine_type = data.get('engine', 'NNUE').upper()
        
        # Validate parameters
        if depth < 1 or depth > 30:
            return jsonify({"error": "Depth must be between 1 and 30"}), 400
            
        if lines < 1 or lines > 10:
            return jsonify({"error": "Lines must be between 1 and 10"}), 400
            
        if engine_type not in ['NNUE', 'HUMAN']:
            return jsonify({"error": "Engine must be 'NNUE' or 'HUMAN'"}), 400
        
        # Select engine path
        engine_path = engineCommunication.engine_path_NNUE if engine_type == 'NNUE' else engineCommunication.engine_path_HUMAN
        
        print(f"Received PGN analysis request: depth={depth}, lines={lines}, engine={engine_type}")
        
        # Perform analysis
        if pgn_string:
            analysis_results = engineCommunication.analyze_pgn_game(pgn_string, depth, lines, engine_path)
        else:
            analysis_results = engineCommunication.analyze_pgn_game(moves_list, depth, lines, engine_path)
        
        return jsonify({
            "success": True,
            "game_analysis": analysis_results,
            "metadata": {
                "total_positions": len(analysis_results),
                "depth": depth,
                "lines": lines,
                "engine": engine_type
            }
        })
        
    except ValueError as ve:
        print(f"Validation error in PGN analysis: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"Error in PGN analysis endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/pool/stats", methods=['GET'])
def pool_stats():
    """
    Returns engine pool statistics.
    """
    try:
        stats = engineCommunication.get_pool_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting pool stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/analysis/styles", methods=['GET'])
def analysis_styles():
    """
    Returns available analysis styles.
    """
    try:
        styles = LLMHandler.get_analysis_styles()
        return jsonify({"styles": styles})
    except Exception as e:
        print(f"Error getting analysis styles: {e}")
        return jsonify({"error": str(e)}), 500



    





if __name__ == "__main__":
    # This will only run when called directly (not with gunicorn)
    logging.basicConfig(level=logging.INFO)
    load_models()
    logging.info("Starting development server...")
    app.run(host="0.0.0.0", port=5000, debug=True)
    
