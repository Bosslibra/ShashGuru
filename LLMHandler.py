import transformers, torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Imports that remove logging
import warnings
from transformers.utils import logging

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


def create_prompt(fen, bestmove):
    prompt = f'''I have the following fen {fen} and my chess engine suggests the move {bestmove} (expressed in uci standard).
    Can you please explain why is this move good? Answer without filler text, in a concise manner'''
    return prompt

def query_LLM(prompt, tokenizer, model):
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")
    messages = [
        {"role": "system", "content": "You are an AI chess analyzer. You should answer in a concise manner, without filler text. Unless instructed otherwise, respond in the same language as the user's query."},
        {"role": "user", "content": prompt}
    ]
    output = pipe(messages, max_new_tokens=256)
    analysis = output[0]["generated_text"][-1]["content"]
    return analysis




prompt = create_prompt('8/5ppk/6p1/R7/P7/7P/2r3PK/8 w - - 1 36', "a5a6")


