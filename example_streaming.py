from openai import OpenAI
import sys
import os

__this__file__path__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(__this__file__path__, "backend"))

import LLMHandler



def query_LLM(prompt, model, chat_history=None, max_history=10):

    pipe = lambda messages, max_new_tokens: model.chat.completions.create(
        model = "meta-llama/Llama-3.1-8B-Instruct",
        messages=messages,
        stream=True,
        max_completion_tokens=max_new_tokens,
    )
    if chat_history is None:
        chat_history = []
    chat_history = chat_history[-max_history:]
    
    messages = [
        {"role": "system", "content": f'''
         You are a strong chess analysis assistant, powered by expert-level knowledge of strategy, tactics, and positional understanding.
         When a user provides a move, respond with clear, insightful evaluations that include the best move, the reasoning behind it, and any critical ideas, threats, or positional plans.
         Avoid unnecessary filler, but enrich your answers with concrete ideas such as tactical motifs, piece activity, material advantage, positional advantage, weaknesses, and long-term plans.
         Use natural, chess-appropriate language. Stay strictly within the topic of chess.
         '''}
    ] + chat_history + [
        {"role": "user", "content": prompt}
    ]

    output = pipe(messages, max_new_tokens=1024)
    analysis = ""
    for out in output:
        if out.choices[0].finish_reason is not None:
            break
        delta = out.choices[0].delta.content
        print(delta, end="", flush=True)
        analysis += delta

    chat_history.append({"role": "user", "content": prompt})
    chat_history.append({"role": "assistant", "content": analysis})

    return analysis, chat_history

def main():
    model = OpenAI(base_url="http://127.0.0.1:6666/v1", api_key="unused")

    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    prompt = LLMHandler.create_prompt_single_engine(fen, 
                                         bestmoves=[{"move": "e2e4", "score": 100}, {"move": "d2d4", "score": 50}, {"move": "g1f3", "score": 30}, {"move": "c2c4", "score": 20}],
                                         ponder="e7e5")

    query_LLM(prompt, model=model)


if __name__ == "__main__":
    main()