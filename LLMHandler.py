import transformers, torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Imports that remove logging
import warnings
from transformers.utils import logging

# Import for prompt creation
from fenManipulation import fen_explainer

model_path = 'E:/LLAMA3/baseModel/llama3' #TODO: replace this path with a directory of your local model

def load_LLM_model():

    # Removing logging
    #transformers.utils.logging.disable_progress_bar()
    logging.set_verbosity(transformers.logging.FATAL)
    warnings.filterwarnings("ignore")

    # Quantizing the model to ensure it runs on machines with mid hardware 
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        )
    
    # Tokenizer and model creation (takes a long time on my machine)
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        legacy=False)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, 
        quantization_config=bnb_config,
        torch_dtype=torch.float16,
        device_map="auto")
    print
    return (tokenizer, model)



def create_prompt(fen, bestmoves, ponder):    
    explainedFEN = fen_explainer(fen)
    prompt = f'''My chess engine suggests the best move {bestmoves[0]} (expressed in uci standard).
    {"" if ponder == None else f"The engine expects that this best move will be met by {ponder} on the next move."}
    Please also consider, without speaking about them, that the engine consideres other 3 good moves, which are the following:
    {bestmoves[1:]}
    Can you please explain why is the best move good? Answer with a lengthy analysis'''
    prompt = "I will explain the board situation:\n" + explainedFEN + prompt
    return prompt

def query_LLM(prompt, tokenizer, model, chat_history=None, max_history=5):
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")
    
    if chat_history is None:
        chat_history = []
    chat_history = chat_history[-max_history:]
    
    messages = [
        {"role": "system", "content": '''You are an AI chess analyzer.
            You should answer in a concise manner, without filler text.
            Unless instructed otherwise, respond in the same language as the user's query.
            Only answer about chess, no other topic should be discussed.
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

# Handles chat request 
# Takes json input
# Returns json output