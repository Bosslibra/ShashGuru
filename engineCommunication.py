import subprocess
from colorama import Fore, Style


# Takes a uci command as input and sends it to the engine
def send_command(cmd):
    engine.stdin.write(cmd + '\n')
    engine.stdin.flush()

def get_best_move():
    print("we in here")
    while True:
        print("we still here")
        output = engine.stdout.readline().strip()
        if output.startswith("bestmove"):
            return output #infinite loop for some reason (the output is never read)
            

#0. Creates pipeline with the engine
engine = subprocess.Popen(['./executables/shashchess'], # Change relative path here, or if your engine is in PATH, only write the name 
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True)


# Header
print(f'''||Welcome to ChessAnalyzer!
||You can use this with any UCI engine.
||
||Use {Fore.RED}'exit'{Style.RESET_ALL} to quit the analyzer.\n
You are using the following engine:''')
print(engine.stdout.readline().strip()) #this will be the name and authors of the engine

#1. Initializing the engine
send_command('uci')
send_command('isready')
print("Engine is ready!\n")

#2. Get the game position
print("Starting position FEN is rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
#print("Paste your FEN here:")
#fen = input().strip()
print("got fen")
send_command("position fen {fen}")
print("position set")

#1. Starting the engine and capturing bestmove
send_command("go depth 5")
print("go gone")
print(get_best_move())
print("did we ever exit?")


print("\n\nThank you for using our ChessAnalyzer.")