from engineCommunication import *
from LLMHandler import *
from colorama import Fore, Style


# Header
print("Welcome to ChessAnalyzer!\n")

# 0. LLM model loading #TODO: desyncronize
print("Loading LLM model. This operation may take some time.")
tokenizer, model = load_LLM_model()
print("Model loaded.\n")

#1. Input collection
# Starting position FEN for debug porpouses: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
fen = input("Paste your FEN here:\n").strip()
depth = input("Please specify the search depth number:\n").strip()

#2. Engine call
bestmove = call_engine(fen, depth)
print(f"The best move found by the engine is: {bestmove}\n")

#3. LLM interaction
prompt = create_prompt(fen, bestmove)
analysis, chat_history = query_LLM(prompt, tokenizer, model)
print("AI:", analysis,"\n")

#4. Continuous Chat
while True:
    new_question = input("You: ").strip().lower()
    if new_question in {"exit" or "quit"}:
        break
    # Filter chess questions
    related = is_chess_related(new_question, tokenizer, model)
    if related:
        answer, chat_history = query_LLM(new_question, tokenizer, model, chat_history=chat_history)
    else: 
        answer = '''Your question might not be chess-related, therefore I cannot answer it.\nIf you believe this is a false report, try to reformulate the question.'''
    print("AI:", answer, "\n")

# Footer
print("\n\nThank you for using our ChessAnalyzer.")