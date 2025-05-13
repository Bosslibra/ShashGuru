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

import transformers, torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, AutoModel

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

    if quantization:
        # Quantizing the model to ensure it runs on machines with mid hardware 
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            )
        
        # Tokenizer and model creation 
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            legacy=False)
        
        model = AutoModelForCausalLM.from_pretrained(
            model_path, 
            quantization_config=bnb_config,
            torch_dtype=torch.float16,
            device_map={"":0})
    else:
         # Tokenizer and model creation 
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            legacy=False)
        
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map={"":0})
    
    return (tokenizer, model)

def __format_eval(entry):
        
        if 'mate' in entry and entry['mate'] is not None:
            return f"mate in {entry['mate']}"
        elif 'score' in entry:
            return f"{entry['score']} cp"
        return None

def create_prompt_single_engine(fen, bestmoves, ponder):
    
    best_eval = []
    for i in range(0, len(bestmoves)):
        best_eval.append(__format_eval(bestmoves[i]))
    print(bestmoves, best_eval)

    prompt = f'''My chess engine suggests the best move {bestmoves[0]['move']} (expressed in uci standard) with the score {best_eval[0]}.
        {"" if ponder == None else f"The engine expects that this best move will be met by {ponder} on the next move."}
        Please also consider, without speaking about them, that the engine consideres other 3 good moves, which are the following:
        {[m['move'] for m in bestmoves[1:]]}
        '''
    prompt = "I will explain the board situation:\n" + prompt
    print(prompt)
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

def query_LLM(prompt, tokenizer, model, fen=None, chat_history=None, max_history=10):
    explainedFEN = fen_explainer(fen)
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")
    if chat_history is None:
        chat_history = []
    chat_history = chat_history[-max_history:]
    
    messages = [
        {"role": "system", "content": f'''
         You are a strong chess analysis assistant, powered by expert-level knowledge of strategy, tactics, and positional understanding.
         { 'You explain this position ' + fen_explainer(fen) if fen is not None else '' }
         When a user provides a move, respond with clear, insightful evaluations that include the best move, the reasoning behind it, and any critical ideas, threats, or positional plans.
         Avoid unnecessary filler, but enrich your answers with concrete ideas such as tactical motifs, piece activity, material advantage, positional advantage, weaknesses, and long-term plans.
         Use natural, chess-appropriate language. Stay strictly within the topic of chess.
         '''}
    ] + chat_history + [
        {"role": "user", "content": prompt}
    ]
    output = pipe(messages, max_new_tokens=1024)
    analysis = output[0]["generated_text"][-1]["content"]

    chat_history.append({"role": "user", "content": prompt})
    chat_history.append({"role": "assistant", "content": analysis})

    return analysis, chat_history

def is_chess_related(question, tokenizer, model):
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")
    messages = [
        {"role": "system", "content": '''You are a filtering agent.
            Your job is to decide if the text is chess-related.
            Keep context in mind.
            Only answer with a "yes" or a "no".
            '''},
        {"role": "user", "content": question + "Is this question chess-related?"}
    ]
    output = pipe(messages, max_new_tokens=256)
    response = output[0]["generated_text"][-1]["content"].strip().lower()
    
    return response in ["yes", "yes."]
