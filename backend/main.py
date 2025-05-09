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

from engineCommunication import *
from LLMHandler import *
from colorama import Fore, Style
#Please note that this shouldn't be used, as it is outdated and only for test purposes. Everything can be now accessed from the gui that uses ShashGuruBackend.py as a server
def chat():
    #1. Input collection
    # Starting position FEN for debug porpouses: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    fen = input("Paste your FEN here:\n").strip()
    depth = input("Please specify the search depth number:\n").strip()

    #2. Engine call
    bestmoves, ponder = call_engine(fen, depth)
    print(f"The best move found by the engine is: {bestmoves[0]}\n")

    #3. LLM interaction
    prompt = create_prompt(fen, bestmoves, ponder)
    analysis, chat_history = query_LLM(prompt, tokenizer, model)
    print("AI:", analysis,"\n")

    #4. Continuous Chat
    while True:
        new_question = input("You: ").strip().lower()
        if new_question in {"exit" or "quit"}:
            return True # Here we completely exit the program
        elif new_question in {"restart"}:
            return False # Here we exit the chat about this particular FEN
        # Filter chess questions
        related = is_chess_related(new_question, tokenizer, model)
        if related:
            answer, chat_history = query_LLM(new_question, tokenizer, model, chat_history=chat_history)
        else: 
            answer = '''Your question might not be chess-related, therefore I cannot answer it.\nIf you believe this is a false report, try to reformulate the question.'''
        print("AI:", answer, "\n")

# Header
print("Welcome to ChessAnalyzer!\n")

# 0. LLM model loading #TODO: desyncronize
print("Loading LLM model. This operation may take some time.")
tokenizer, model = load_LLM_model()
print("Model loaded.\n")

# Starting analysis
while True:
    # chat() returns True if you want to restart chat with a different FEN, otherwise False
    stop = chat()
    if stop:
        break
        
    
# Footer
print("\n\nThank you for using our ChessAnalyzer.")