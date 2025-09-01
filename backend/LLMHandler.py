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
#along with this program.  If not, see <https://www.gnu.org/licenses/>.vb

import transformers
from openai import OpenAI
import logging as log

# Imports that remove logging
import warnings
from transformers.utils import logging

# Import for prompt creation
from fenManipulation import fen_explainer
import chess
import os

quantization = True

SYSTEM_MESSAGE = f'''
You are a concise chess analysis assistant. For initial position analysis, provide brief, accurate insights based only on the given information.
Focus on the most important aspects: the recommended move and its purpose.
Keep responses short (2-3 sentences max). Avoid speculation or moves not mentioned in the analysis.
Use clear, natural chess language without unnecessary elaboration.

For follow-up questions, refer back to the position and engine analysis provided in the conversation context.
Maintain the same brevity and focus on concrete information when answering follow-ups.

If asked about moves that were not analyzed by the engine, respond that you don't have analysis for those moves and suggest the user try those moves on the board and re-run the analysis to get engine evaluation for them.
'''


def load_LLM_model(modelNumber=1):
    
    # Removing logging
    #transformers.utils.logging.disable_progress_bar()
    logging.set_verbosity(transformers.logging.FATAL)
    warnings.filterwarnings("ignore")
    model_path = ""
    #__ Llama 3.1-8B ___#
    if modelNumber == 1: 
            model_path = "meta-llama/Llama-3.1-8B-Instruct"
    #__ Llama 3.2-1B ___#
    if modelNumber == 2:
            model_path = "meta-llama/Llama-3.2-1B"
    #__ Llama 3.1-8B, finetuned with MATE database ___#
    #elif modelNumber == 3: 
        ## non credo vada
        #model = AutoModel.from_pretrained("OutFlankShu/MATE/both/checkpoint-1000")
    base_url = os.environ.get("AI_BASE_URL", "http://frontend:6666/v1")
    model = OpenAI(base_url=base_url, api_key="unused")
    return None, model

def __format_eval(entry):
        
        if 'mate' in entry and entry['mate'] is not None:
            return f"mate in {entry['mate']}"
        elif 'score' in entry:
            return f"{entry['score']} cp"
        return None

def __mapWinProb(winprob, side):
    if 0 <= winprob <= 5:
        return f"{side} has a decisive disadvantage, with the position clearly leading to a loss."
    elif 6 <= winprob <= 10:
        return f"{side} has decisive disadvantage: the opponent has a dominant position and is likely winning."
    elif 11 <= winprob <= 15:
        return f"{side} has clear disadvantage: a substantial positional disadvantage, but a win is not yet inevitable."
    elif 16 <= winprob <= 20:
        return f"{side} has a significant disadvantage: difficult to recover."
    elif 21 <= winprob <= 24:
        return f"{side} has a slight disadvantage with a positional edge, but no immediate threats."
    elif 25 <= winprob <= 49:
        return f"{side} is in a defensive position. The opponent has an initiative."
    elif winprob == 50:
        return f"The position is equal. Both sides are evenly matched, with no evident advantage."
    elif 51 <= winprob <= 75:
        return f"{side} has initiative: by applying pressure and it can achieve an edge with active moves and forcing ideas."
    elif 76 <= winprob <= 79:
        return f"{side} has a slight advantage: a minor positional edge, but it’s not decisive."
    elif 80 <= winprob <= 84:
        return f"{side} is slightly better, tending toward a clear advantage. The advantage is growing, but the position is still not decisive."
    elif 85 <= winprob <= 89:
        return f"{side} has a clear advantage: a significant edge, but still with defensive chances."
    elif 90 <= winprob <= 94:
        return f"{side} has a dominant position, almost decisive, not quite winning yet, but trending toward victory."
    elif 95 <= winprob <= 100:
        return f"{side} has a decisive advantage, with victory nearly assured."
    else:
        return "Total chaos: unclear position, dynamically balanced, with no clear advantage for either side and no clear positional trends."

def generate_line(line, board):
    tmp_board = board.copy()
    san_line = []
    for idx, move in enumerate(line):
        uci_move = chess.Move.from_uci(move)
        san_move = tmp_board.san(uci_move)
        if idx > 0:
            # Skip the first move
            san_line.append(san_move)
        tmp_board.push(uci_move)
    return " ".join(san_line)

def analyze_position_context(fen, board):
    """Generate additional context about the position for the LLM"""
    context = []
    
    # Material count
    material = {
        chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
        chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0
    }
    
    white_material = sum(material[piece.piece_type] for piece in board.piece_map().values() if piece.color == chess.WHITE)
    black_material = sum(material[piece.piece_type] for piece in board.piece_map().values() if piece.color == chess.BLACK)
    
    material_diff = white_material - black_material
    if material_diff > 0:
        context.append(f"Material: White is ahead by {material_diff} points")
    elif material_diff < 0:
        context.append(f"Material: Black is ahead by {abs(material_diff)} points")
    else:
        context.append("Material: Equal material")
    
    # King safety
    white_king_square = board.king(chess.WHITE)
    black_king_square = board.king(chess.BLACK)
    
    if white_king_square:
        white_king_file = chess.square_file(white_king_square)
        white_king_rank = chess.square_rank(white_king_square)
        if white_king_rank <= 1 and (white_king_file <= 2 or white_king_file >= 5):
            context.append("White king appears castled/safe")
        elif white_king_rank >= 3:
            context.append("White king is exposed in the center")
    
    if black_king_square:
        black_king_file = chess.square_file(black_king_square)
        black_king_rank = chess.square_rank(black_king_square)
        if black_king_rank >= 6 and (black_king_file <= 2 or black_king_file >= 5):
            context.append("Black king appears castled/safe")
        elif black_king_rank <= 4:
            context.append("Black king is exposed in the center")
    
    # Check status
    if board.is_check():
        context.append(f"{'White' if board.turn == chess.WHITE else 'Black'} king is in check")
    
    # Game phase indicator
    total_pieces = len(board.piece_map())
    if total_pieces > 24:
        context.append("Position: Opening/Early middlegame")
    elif total_pieces > 12:
        context.append("Position: Middlegame")
    else:
        context.append("Position: Endgame")
    
    return "; ".join(context)

def analysis_to_string(fen, side, analysis):
    output = []
    board = chess.Board(fen)
    
    # Show top 3 moves with their evaluations
    for idx, item in enumerate(analysis[:3]):
        eval_text = __mapWinProb(item['winprob'], side)
        line_moves = generate_line(item['pv_moves'][:5], board)
        
        # Add move explanation
        first_move = item['pv_moves'][0] if item['pv_moves'] else "No move"
        move_obj = chess.Move.from_uci(first_move)
        move_san = board.san(move_obj)
        
        output.append(f"Option {idx+1}: {move_san} - {eval_text}")
        if line_moves:
            output.append(f"   Continuation: {line_moves}")
    
    return "\n".join(output)


def create_prompt_single_engine(fen, bestmoves, ponder):
    log.basicConfig(level=log.INFO)
    explainedFEN, side = fen_explainer(fen)
    board = chess.Board(fen)
    
    # Get position context
    position_context = analyze_position_context(fen, board)
    
    # Get the best move in readable format
    best_move_uci = bestmoves[0]['pv_moves'][0] if bestmoves[0]['pv_moves'] else "No move"
    best_move_san = board.san(chess.Move.from_uci(best_move_uci))
    
    # Get evaluation
    win_prob_text = __mapWinProb(bestmoves[0]['winprob'], side)
    
    # Show only the top move with continuation
    top_move = bestmoves[0]
    continuation = generate_line(top_move['pv_moves'][:4], board)
    
    # Create a concise, flowing prompt
    prompt = f"""{explainedFEN}

{position_context}

The engine recommends {side} to play {best_move_san}, leading to the continuation {continuation}. The position evaluation shows that {win_prob_text.lower()}. 

In 2-3 sentences, explain why {best_move_san} is the strongest choice and what this evaluation means for {side}'s position. Focus only on the concrete information provided."""
    
    log.info("Generated prompt for single engine:")
    log.info(prompt) 
    return prompt

def create_prompt_double_engine(fen, engine_analysis):    
    explainedFEN = fen_explainer(fen)

    nnue = engine_analysis['NNUE']
    human = engine_analysis['HUMAN']

    nnue_best = nnue['top_moves'][0]['move']
    human_best = human['top_moves'][0]['move']

    

    nnue_best_eval = __format_eval(nnue['top_moves'][0])
    human_best_eval = __format_eval(human['top_moves'][0])

    bestmove_prompt = f"""I have two engines: one with NNUE, called ShashChess, and another that simulates human thought, called Alexander.
        ShashChess suggests the best move **{nnue_best}** (in UCI format) {f"with an evaluation of {nnue_best_eval}" if nnue_best_eval is not None else "" }, 
        while Alexander suggests the best move is **{human_best}** (in UCI format) {f"with an evaluation of {human_best_eval}" if human_best_eval is not None else "" }.
        ShashChess evaluates Alexander's top move with a score of {nnue['eval_human_move']} and Alexander evaluates ShashChess' best move with a score of {human['eval_nnue_move']}.
        If the engines disagree on the best move, note that ShashChess also suggests these other strong moves: {nnue['top_moves'][1:]}, 
        while Alexander suggests these: {human['top_moves'][1:]}.
        If either engine considers the other’s top choice among these alternatives, that might imply partial agreement."""
    
    counter_prompt = f'''{"ShashChess expects a reply to his best move of **" + engine_analysis['NNUE'].get('ponder', '') + "**." if engine_analysis['NNUE'].get('ponder') else ""}
        {"Alexander expects a reply to his best move of **" + engine_analysis['HUMAN'].get('ponder', '') + "**." if engine_analysis['HUMAN'].get('ponder') else ""}
        {"ShashChess also evaluates Alexander’s expected reply with a score of " + str(nnue['eval_human_ponder']) + "." if nnue['eval_human_ponder'] is not None else ""}
        {"Alexander also evaluates ShashChess’s expected reply with a score of " + str(human['eval_nnue_ponder']) + "." if human['eval_nnue_ponder'] is not None else ""}'''

    full_prompt = "I will explain the board situation:\n" + explainedFEN + "\n\n" + bestmove_prompt + " " + counter_prompt + "Can you explain why these suggested moves are strong? Provide an insightful chess analysis."
    return full_prompt

def query_LLM(prompt, tokenizer, model, chat_history=None, max_history=10):

    pipe = lambda messages, max_new_tokens: model.chat.completions.create(
        model = "meta-llama/Llama-3.1-8B-Instruct",
        messages=messages,
        max_completion_tokens=max_new_tokens,
    )
    if chat_history is None:
        chat_history = []
    chat_history = chat_history[-max_history:]
    
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE}
    ] + chat_history + [
        {"role": "user", "content": prompt}
    ]
    output = pipe(messages, max_new_tokens=1024)
    analysis = output.choices[0].message.content

    chat_history.append({"role": "user", "content": prompt})
    chat_history.append({"role": "assistant", "content": analysis})

    return analysis, chat_history


def stream_LLM(prompt, model, chat_history=None, max_history=10):
    pipe = lambda messages, max_new_tokens: model.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=messages,
        stream=True,
        max_completion_tokens=1024,
        temperature=0.0,
    )
    if chat_history is None:
        chat_history = []
    chat_history = chat_history[-max_history:]

    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        *chat_history,
        {"role": "user", "content": prompt}
    ]

    output = pipe(messages, max_new_tokens=1024)

    for out in output:
        if out.choices[0].finish_reason is not None:
            break
        delta = out.choices[0].delta.content
        if delta:
            yield delta


def is_chess_related(question, tokenizer, model):
    pipe = lambda messages, max_new_tokens: model.chat.completions.create(
        model = "meta-llama/Llama-3.1-8B-Instruct",
        messages=messages,
        max_completion_tokens=max_new_tokens,
    )

    messages = [
        {"role": "system", "content": '''You are a filtering agent.
            Your job is to decide if the text is chess-related.
            Keep context in mind.
            Only answer with a "yes" or a "no".
            '''},
        {"role": "user", "content": question + "Is this question chess-related?"}
    ]
    output = pipe(messages, max_new_tokens=256)
    response = output.choices[0].message.content
    
    return response in ["yes", "yes."]
