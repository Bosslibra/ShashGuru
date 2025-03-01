import subprocess
import os

engine_name = 'shashchess'
engine_path = f".\executables\{engine_name}" if os.name == 'nt' else f"./executables/{engine_name}"

#0. Creates pipeline with the engine


# Takes a uci command as input and sends it to the engine
def send_command(cmd):
    engine.stdin.write(cmd + '\n')
    engine.stdin.flush()

def call_engine(fen, depth):
    engine = subprocess.Popen([engine_path], # Change relative path here, or if your engine is in PATH, only write the name 
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True)
    #1. Initializing the engine
    send_command('uci')
    send_command('isready')
    print("Engine is ready!\n")

    #2. Get the game position
    print("Paste your FEN here:")
    
    send_command(f"position fen {fen}")

    #3. Starting the engine and capturing bestmove
    send_command(f"go depth {depth}")
    print("Thinking...\n")
    while True:
        output = engine.stdout.readline().strip()
        if output.startswith("bestmove"):
            bestmove = output.split()[1]
            return bestmove