import subprocess
import os

engine_name = 'shashchess'
engine_path = f".\executables\{engine_name}.exe" if os.name == 'nt' else f"./executables/{engine_name}"

#0. Creates pipeline with the engine


# Takes a uci command as input and sends it to the engine

def call_engine(fen, depth):
    engine = subprocess.Popen([engine_path], # Change relative path here, or if your engine is in PATH, only write the name 
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True)
    #1. Initializing the engine
    engine.stdin.write('uci\n')
    engine.stdin.flush()
    engine.stdin.write('isready\n')
    engine.stdin.flush()
    print("Engine is ready!\n")

    #2. Set the game position
    engine.stdin.write(f'position fen {fen}\n')
    engine.stdin.flush()

    #3. Starting search and capturing bestmove
    engine.stdin.write(f'go depth {depth}\n')
    engine.stdin.flush()
    print("Thinking...\n")
    while True:
        output = engine.stdout.readline().strip()
        if output.startswith("bestmove"):
            bestmove = output.split()[1]
            return bestmove