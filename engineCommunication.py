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

    #2. Set the game position
    engine.stdin.write(f'position fen {fen}\n')
    engine.stdin.flush()

    #3. Starting search and capturing bestmove
    engine.stdin.write(f'setoption name MultiPV value 3\n')
    engine.stdin.flush()
    engine.stdin.write(f'go depth {depth}\n')
    engine.stdin.flush()
    print("\nThinking...\n")
    bestmoves=[]
    while True:
        output = engine.stdout.readline().strip()
        # Saving principal variations for follow up questions
        if output.startswith(f"info depth {depth}") and "multipv" in output:
            output_split = output.split()
            i = int(output_split.index("multipv")) + 1
            pv = int(output_split.index("pv")) + 1
            bestmoves.insert(int(output_split[i])-1, output_split[pv]) # moves will be added in order of how strong they are
        # Saving ponder move and exiting the loop 
        elif output.startswith("bestmove"):
            output_split = output.split()
            ponder = None
            if len(output_split) > 2:
                ponder = output_split[3]
            return bestmoves, ponder
        
