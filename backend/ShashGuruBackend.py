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

import LLMHandler
import engineCommunication

app = Flask(__name__)
CORS(app)


@app.route("/analysis", methods=['GET', 'POST'])
def analysis():
    fen = request.json.get('fen')  
    print("Received analysis request for:", fen)
    depth = 15
    
    bestmoves, ponder = engineCommunication.call_engine(fen, depth)
    prompt = LLMHandler.create_prompt_single_engine(fen, bestmoves, ponder)

    ############################
    #  Questo è per due engine #
    ############################
    #engine_analysis = engineCommunication.engines(fen, depth)
    #prompt = LLMHandler.create_prompt_double_engine(fen, engine_analysis)


    ## NON STREAM OPTION
    #analysis, chat_history = LLMHandler.query_LLM(prompt, tokenizer, model)
    #print(chat_history)

    def generate():
        yield "[START_STREAM]\n"  # optional: delimiter for stream start
        for token in LLMHandler.stream_LLM(prompt, model):  # <-- stream here
            yield token
        yield "\n[END_STREAM]"  # optional: delimiter for stream end 
    
    return Response(stream_with_context(generate()), mimetype='text/plain')
    #return jsonify(chat_history)


@app.route("/response", methods=['GET','POST'])
def response():
    chat_history = request.get_json()
    if chat_history is None:
        chat_history = [] 
    new_question = chat_history[-1].get("content")
    print('Received question:' , new_question)


    ### NO STREAM OPTION
    #related = LLMHandler.is_chess_related(new_question, tokenizer, model)
    #if related:
    #    print("is chess related")
    #    answer, chat_history = LLMHandler.query_LLM(new_question, tokenizer, model, chat_history=chat_history[:-1])
    #    print(answer)
    #else: 
    #    default_not_chess = '''Your question might not be chess-related, therefore I cannot answer it.\nIf you believe this is a false report, try to reformulate the question.'''
    #    chat_history.append({ "role" : "assistant", "content": default_not_chess })

    
    #print(chat_history) 

    #return jsonify(chat_history)
    def generate():
        yield "[START_STREAM]\n"
        for token in LLMHandler.stream_LLM(new_question, model, chat_history=chat_history[:-1]):
            yield token
        yield "\n[END_STREAM]"

    return Response(stream_with_context(generate()), mimetype='text/plain')



    





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

    #THIS IS NECESSARY, DO NOT REMOVE
    app.run(host="0.0.0.0", port=5000, debug=True)
    
