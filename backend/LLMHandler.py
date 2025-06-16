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

quantization = True


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

    model = OpenAI(base_url="http://frontend:6666/v1", api_key="unused")
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

def create_prompt_single_engine(fen, bestmoves, ponder):
    log.basicConfig(level=log.INFO)
    explainedFEN, side = fen_explainer(fen)
    best_eval = []
    for i in range(0, len(bestmoves)):
        best_eval.append(__format_eval(bestmoves[i]))
    print(bestmoves, best_eval)
    textualExtimationOfAdvantage = __mapWinProb(bestmoves[0]['winprob'], side)
    winPercentage = bestmoves[0]['w']
    drawPercentage = bestmoves[0]['d']
    lossPercentage = bestmoves[0]['l']
    

    prompt2 = f""" **Chess Position Analysis Request**

{explainedFEN}

Current situation: {textualExtimationOfAdvantage}



Please provide concise analysis (≤800 chars) covering:

1. **Advantage Assessment** - Who stands better and the primary reason (material/structure/activity)
2. **Best Move** - Why is {bestmoves[0]['move']} (eval: {best_eval[0]}) the best move? Highlight 1 idea max.
3. **Expected Outcome** - Who is more likely to win? Mention that the percentages Win/draw/Loss for {side}: {winPercentage}%/{drawPercentage}%/{lossPercentage}%.

Focus on concrete factors like:
- Key weaknesses/squares
- Piece activity/coordination
- Pawn structure implications
- Immediate tactical motifs"""

    prompt = f'''You are a chess engine analyst. This is the board state:{ explainedFEN }\n
{ textualExtimationOfAdvantage }

Explain in simple language:

1. Who is better and why (positional, tactical, material).
2. Given the best move  {bestmoves[0]['move']}, which has the score {best_eval[0]}, explain why it is the best (remind that the )
3. The idea behind these other top moves {[m['move'] for m in bestmoves[1:]]}.

Respond concisely (try to stay inside 800 characters).'''
    
    ## Questo causava confusione, riprovo diversamente
    prompt_old = f'''My chess engine suggests the best move {bestmoves[0]['move']} (expressed in uci standard) with the score {best_eval[0]}.
{"" if ponder == None else f"The engine expects that this best move will be met by {ponder} on the next move."}
Please also consider, without speaking about them, that the engine consideres other 3 good moves, which are the following:
{[m['move'] for m in bestmoves[1:]]}
Can you please comment about the following things:
1) The current position of the game (for example who has a better chance, but don't limit yourself on this)
2) Your judgment about the bestmove (consider the evaluation of the engine)

Please be concise in your answer.
'''

    question3 = "3) Your analysis on what is going to happen\n"
    question4 = "4) Your guess about the players strategy (for both sides)\n"
    prompt_old = "I will explain the board situation:\n" + explainedFEN + prompt_old
    log.info(prompt2)
    return prompt2

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
        {"role": "system", "content": f'''
         You are a strong chess analysis assistant, powered by expert-level knowledge of strategy, tactics, and positional understanding.
         When a user provides a move, respond with clear, insightful evaluations that include the best move, the reasoning behind it, and any critical ideas, threats, or positional plans.
         Avoid unnecessary filler, but enrich your answers with concrete ideas such as tactical motifs, piece activity, material advantage, positional advantage, weaknesses, and long-term plans.
         Use natural, chess-appropriate language. Stay strictly within the topic of chess.
         '''}
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
        {"role": "system", "content": "You are a strong chess analysis assistant..."},
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
