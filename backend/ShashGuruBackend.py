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
from flask_cors import CORS
import argparse
import logging 


import LLMHandler
import engineCommunication
from engineCache import get_cache

app = Flask(__name__)
CORS(app)


@app.route("/analysis", methods=['GET', 'POST'])
def analysis():
    fen = request.json.get('fen')  
    print("Received analysis request for:", fen)
    depth = request.json.get('depth', 20)

    bestmoves, ponder = engineCommunication.call_engine(fen, depth, lines=1)
    prompt = LLMHandler.create_prompt_single_engine(fen, bestmoves, ponder)

    ############################
    #  Questo è per due engine #
    ############################
    #engine_analysis = engineCommunication.engines(fen, depth)
    #prompt = LLMHandler.create_prompt_double_engine(fen, engine_analysis)

    def generate():
        yield json.dumps({"prompt": prompt}) + "\n[PROMPT_END]\n" # sends single chunk with prompt, to save it as context for responses
        yield "[START_STREAM]\n"  # optional: delimiter for stream start
        for token in LLMHandler.stream_LLM(prompt, model):  # <-- stream here
            yield token
        yield "\n[END_STREAM]"  # optional: delimiter for stream end 
    
    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route("/response", methods=['GET','POST'])
def response():
    chat_history = request.get_json()
    if chat_history is None:
        chat_history = [] 
    new_question = chat_history[-1].get("content")
    print('Received question:' , new_question)

    def generate():
        yield "[START_STREAM]\n"
        for token in LLMHandler.stream_LLM(new_question, model, chat_history=chat_history[:-1]):
            yield token
        yield "\n[END_STREAM]"

    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route("/evaluation", methods=['GET', 'POST'])
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



    





if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run ShashGuru Backend with optional flags.")
    parser.add_argument("--M", action="store_true", help="Use MATE model")
    parser.add_argument("--S", action="store_true", help="Use Llama3.2-1B model")
    parser.add_argument("--L", action="store_true", help="Use Llama3.1-8B model")
    args = parser.parse_args()

    modelNumber = 1
    if args.L:
        modelNumber = 1
    elif args.S:
        modelNumber = 2
    elif args.M:
        modelNumber = 3
    else: 
        model_number = 1

    tokenizer, model = LLMHandler.load_LLM_model(modelNumber)
    logging.info("Loaded model.")
    #THIS IS NECESSARY, DO NOT REMOVE
    app.run(host="0.0.0.0", port=5000, debug=True)
    
