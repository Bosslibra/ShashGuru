import subprocess
import os
from colorama import Fore, Style

# Takes a uci command as input and sends it to the engine
def send_command(cmd):
    engine.stdin.write(cmd + '\n')
    engine.stdin.flush()

engine_name = 'shashchess'
engine_path = f".\executables\{engine_name}" if os.name == 'nt' else f"./executables/{engine_name}"

#0. Creates pipeline with the engine
engine = subprocess.Popen([engine_path], # Change relative path here, or if your engine is in PATH, only write the name 
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True)


# Header
print(f'''||Welcome to ChessAnalyzer!
||You can use this tool with any UCI engine.
||
||Use {Fore.RED}'exit'{Style.RESET_ALL} to quit the analyzer.\n
You are using the following engine:''')
print(engine.stdout.readline().strip() + "\n") #this will be the name and authors of the engine

#1. Initializing the engine
send_command('uci')
send_command('isready')
print("Engine is ready!\n")

#2. Get the game position
fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
print(f"Starting position FEN is {fen}")
print("Paste your FEN here:")
fen = input().strip()
send_command(f"position fen {fen}")

#3. Starting the engine and capturing bestmove
send_command("go depth 20")
print("Thinking...\n")
while True:
    output = engine.stdout.readline().strip()
    if output.startswith("bestmove"):
        print(f"The best move found by {engine_name} is: {output.split()[1]}")
        break


print("\n\nThank you for using our ChessAnalyzer.")