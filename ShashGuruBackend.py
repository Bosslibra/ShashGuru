from flask import Flask, request, jsonify, json
from flask_cors import CORS
import argparse

import LLMHandler
import engineCommunication

app = Flask(__name__)
CORS(app)


@app.route("/analysis", methods=['GET', 'POST'])
def analysis():
    fen = request.json.get('fen')  
    print("Received message:", fen)
    depth = 5
    
    engine_analysis = engineCommunication.engines(fen, depth)
    prompt = LLMHandler.create_prompt(fen, engine_analysis)
    analysis, chat_history = LLMHandler.query_LLM(prompt, tokenizer, model)
    print(chat_history)
    return jsonify(chat_history)


@app.route("/response", methods=['GET','POST'])
def response():
    chat_history = request.get_json()
    if chat_history is None:
        chat_history = [] 
    new_question = chat_history[-1].get("content")
    print('Received question:' , new_question)

    related = LLMHandler.is_chess_related(new_question, tokenizer, model)
    if related:
        print("is chess related")
        answer, chat_history = LLMHandler.query_LLM(new_question, tokenizer, model, chat_history=chat_history[:-1])
        print(answer)
    else: 
        default_not_chess = '''Your question might not be chess-related, therefore I cannot answer it.\nIf you believe this is a false report, try to reformulate the question.'''
        chat_history.append({ "role" : "assistant", "content": default_not_chess })
    
    #chat_history = json.dumps(chat_history)
    print(chat_history) 

    return jsonify(chat_history)





if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run ShashGuru Backend with optional flags.")
    parser.add_argument("--M", action="store_true", help="Use MATE model")
    parser.add_argument("--S", action="store_true", help="Use Llama3.2-1B model")
    parser.add_argument("--L", action="store_true", help="Use Llama3.1-8B model")
    args = parser.parse_args()

    modelNumber = 0
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
    app.run(debug=True)