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


import subprocess
import os
import chess
import logging
logging.basicConfig(level=logging.INFO)
engine_name_NNUE = 'shashchess'
engine_name_HUMAN = 'alexander'
engine_path_NNUE = f".\\executables\\{engine_name_NNUE}.exe" if os.name == 'nt' else f"./executables/{engine_name_NNUE}"
engine_path_HUMAN = f".\\executables\\{engine_name_HUMAN}.exe" if os.name == 'nt' else f"./executables/{engine_name_HUMAN}"

def call_engine(fen, depth, engine_path=engine_path_NNUE):
    engine = subprocess.Popen([engine_path],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)

    engine.stdin.write('uci\n')
    engine.stdin.flush()
    engine.stdin.write('isready\n')
    engine.stdin.flush()
    engine.stdin.write(f'position fen {fen}\n')
    engine.stdin.flush()
    engine.stdin.write(f'setoption name MultiPV value 3\n')
    engine.stdin.flush()
    engine.stdin.write(f'go depth {depth}\n')
    engine.stdin.flush()

    bestmoves = []
    ponder = None

    while True:
        output = engine.stdout.readline().strip()
        logging.info("ENGINE OUTPUT:", output)
        if output.startswith(f"info depth {depth}") and "multipv" in output:
            parts = output.split()
            try:
                mv_idx = parts.index("multipv") + 1
                pv_idx = parts.index("pv") + 1
                move = parts[pv_idx]

                # Get score
                score = None
                mate = None
                if "score" in parts:
                    score_idx = parts.index("score")
                    if parts[score_idx + 1] == "cp":
                        score = int(parts[score_idx + 2])
                    elif parts[score_idx + 1] == "mate":
                        mate = int(parts[score_idx + 2])

                # MODIFIED: Extract WDL if available
                winprob = None
                w = None
                d = None
                l = None
                if "wdl" in parts:
                    wdl_idx = parts.index("wdl") + 1
                    w = int(parts[wdl_idx])
                    d = int(parts[wdl_idx + 1])
                    l = int(parts[wdl_idx + 2])
                    winprob = (w +(d/2))/10

                bestmoves.insert(int(parts[mv_idx]) - 1, {
                    'move': move,
                    'score': score,
                    'mate': mate,
                    'w': w,
                    'd': d,
                    'l': l,
                    'winprob': winprob,
                })
                
            except Exception as e:
                print("Parse error:", e)
                continue

        elif output.startswith("bestmove"):
            parts = output.split()
            if len(parts) >= 4:
                ponder = parts[3]
            break

    engine.stdin.write('quit\n')
    engine.stdin.flush()
    
    logging.info("BESTMOVES", bestmoves)
    
    return bestmoves, ponder


def apply_move_to_fen(fen, move_uci):
    """
    Uses python-chess to apply a UCI move string to a FEN.
    Handles promotions, castling, en passant, clock updates.
    """
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)

    if move not in board.legal_moves:
        raise ValueError(f"Illegal move '{move_uci}' for given FEN")

    board.push(move)
    return board.fen()
# Evaluate specific move from a FEN
def eval_move(fen, move, depth, engine_path):
    try:
        new_fen = apply_move_to_fen(fen, move)
        evals, _ = call_engine(new_fen, depth, engine_path)
        return evals[0] if evals else None
    except Exception as e:
        print(f"Error evaluating move {move}: {e}")
        return None

# Master function
def engines(fen, depth):
    bestmovesNNUE, ponderNNUE = call_engine(fen, depth, engine_path_NNUE)
    bestmovesHUMAN, ponderHUMAN = call_engine(fen, depth, engine_path_HUMAN)

    human_move = bestmovesHUMAN[0]['move']
    nnue_eval_of_human = eval_move(fen, human_move, depth, engine_path_NNUE)

    nnue_move = bestmovesNNUE[0]['move']
    human_eval_of_nnue = eval_move(fen, nnue_move, depth, engine_path_HUMAN)

    nnue_eval_of_human_ponder = eval_move(fen, ponderHUMAN, depth, engine_path_NNUE) if ponderHUMAN else None
    human_eval_of_nnue_ponder = eval_move(fen, ponderNNUE, depth, engine_path_HUMAN) if ponderNNUE else None

    return {
        'NNUE': {
            'top_moves': bestmovesNNUE,
            'eval_human_move': nnue_eval_of_human,
            'eval_human_ponder': nnue_eval_of_human_ponder
        },
        'HUMAN': {
            'top_moves': bestmovesHUMAN,
            'eval_nnue_move': human_eval_of_nnue,
            'eval_nnue_ponder': human_eval_of_nnue_ponder
        }
    }