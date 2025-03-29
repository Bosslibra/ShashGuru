from flask import Flask, request, jsonify, json
from flask_cors import CORS

import LLMHandler
import engineCommunication

app = Flask(__name__)
CORS(app)


@app.route("/analysis", methods=['GET', 'POST'])
def analysis():
    fen = request.json.get('fen')  
    print("Received message:", fen)
    depth = 5
    
    bestmoves, ponder = engineCommunication.call_engine(fen, depth)
    prompt = LLMHandler.create_prompt(fen, bestmoves, ponder)
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
    tokenizer, model = LLMHandler.load_LLM_model()

    #THIS IS NECESSARY, DO NOT REMOVE
    app.run(debug=True)