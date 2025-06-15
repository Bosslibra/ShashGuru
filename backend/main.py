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
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from LLMHandler import * 
from engineCommunication import *
#Please note that this shouldn't be used, as it is outdated and only for test purposes. Everything can be now accessed from the gui that uses ShashGuruBackend.py as a server

def query_LLM(prompt, tokenizer, model, chat_history=None, max_history=11):
    if chat_history is None:
        chat_history = []

    chat_history = chat_history[-max_history:]

    # Construct the full conversation history into a single string
    system_prompt = (
        "You are a strong chess analysis assistant, powered by expert-level knowledge of strategy, "
        "tactics, and positional understanding.\n"
        "When a user provides a move, respond with clear, insightful evaluations that include the best move, "
        "the reasoning behind it, and any critical ideas, threats, or positional plans.\n"
        "Avoid unnecessary filler, but enrich your answers with concrete ideas such as tactical motifs, "
        "piece activity, material advantage, positional advantage, weaknesses, and long-term plans.\n"
        "Use natural, chess-appropriate language. Stay strictly within the topic of chess.\n\n"
    )

    # Combine chat history with prompt
    conversation = system_prompt
    for message in chat_history:
        if message["role"] == "user":
            conversation += f"User: {message['content']}\n"
        elif message["role"] == "assistant":
            conversation += f"Assistant: {message['content']}\n"
    conversation += f"User: {prompt}\nAssistant:"

    # Tokenize and generate
    inputs = tokenizer(conversation, return_tensors="pt", truncation=True).to(model.device)
    output_tokens = model.generate(
        **inputs,
        max_new_tokens=1024,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=tokenizer.eos_token_id
    )
    output_text = tokenizer.decode(output_tokens[0], skip_special_tokens=True)

    # Extract only the assistant's reply
    if "Assistant:" in output_text:
        analysis = output_text.split("Assistant:")[-1].strip()
    else:
        analysis = output_text.strip()

    # Update chat history
    chat_history.append({"role": "user", "content": prompt})
    chat_history.append({"role": "assistant", "content": analysis})

    return analysis, chat_history

def chat():
    #1. Input collection
    # Starting position FEN for debug porpouses: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    fen = input("Paste your FEN here:\n").strip()
    depth = input("Please specify the search depth number:\n").strip()

    #2. Engine call
    bestmoves, ponder = call_engine(fen, depth)
    print(f"The best move found by the engine is: {bestmoves[0]}\n")

    #3. LLM interaction
    prompt = create_prompt_single_engine(fen, bestmoves, ponder)
    logging.info(prompt)
    analysis, chat_history = query_LLM(prompt, tokenizer, model)
    print("AI:", analysis,"\n")

    #4. Continuous Chat
    while True:
        new_question = input("You: ").strip().lower()
        if new_question in {"exit" or "quit"}:
            return True # Here we completely exit the program
        elif new_question in {"restart"}:
            return False # Here we exit the chat about this particular FEN
        
        answer, chat_history = query_LLM(new_question, tokenizer, model, chat_history=chat_history)
        print("AI:", answer, "\n")

# Header
print("Welcome to ChessAnalyzer!\n")

# 0. LLM model loading #TODO: desyncronize
print("Loading LLM model. This operation may take some time.")
tokenizer = AutoTokenizer.from_pretrained("Waterhorse/chessgpt-base-v1")
model = AutoModelForCausalLM.from_pretrained("Waterhorse/chessgpt-base-v1", torch_dtype=torch.float16)
print("Model loaded.\n")

# Starting analysis
while True:
    # chat() returns True if you want to restart chat with a different FEN, otherwise False
    stop = chat()
    if stop:
        break
        


# Footer
print("\n\nThank you for using our ChessAnalyzer.")