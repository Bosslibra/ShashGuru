from engineCommunication import *
from LLMHandler import *
from colorama import Fore, Style



# Header
print("Welcome to ChessAnalyzer!\n")

#1. Input collection
print("Paste your FEN here:")
fen = input().strip()
print("Please specify the search depth number:")
depth = input().strip()

#2. Engine call
bestmove = call_engine(fen, depth)
print(f"The best move found by the engine is: {bestmove}")

#3. Prompt generation
create_prompt(fen, bestmove)


# Footer
print("\n\nThank you for using our ChessAnalyzer.")