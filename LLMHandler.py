import transformers, torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, AutoModel

# Imports that remove logging
import warnings
from transformers.utils import logging

# Import for prompt creation
from fenManipulation import fen_explainer

#TODO: replace this path with a directory of your local model, not great code I know
model_path_8B = 'E:/LLAMA3/baseModel/Llama3.1_8B' 
model_path_1B = 'E:/LLAMA3/baseModel/Llama3.2_1B' 

model_path = model_path_8B

def load_LLM_model(modelNumber):

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
    if not hasattr(tokenizer, "chat_template") or tokenizer.chat_template is None:
        tokenizer.chat_template = """{{- bos_token }}
{%- if custom_tools is defined %}
    {%- set tools = custom_tools %}
{%- endif %}
{%- if not tools_in_user_message is defined %}
    {%- set tools_in_user_message = true %}
{%- endif %}
{%- if not date_string is defined %}
    {%- set date_string = "26 Jul 2024" %}
{%- endif %}
{%- if not tools is defined %}
    {%- set tools = none %}
{%- endif %}

{#- This block extracts the system message, so we can slot it into the right place. #}
{%- if messages[0]['role'] == 'system' %}
    {%- set system_message = messages[0]['content']|trim %}
    {%- set messages = messages[1:] %}
{%- else %}
    {%- set system_message = "" %}
{%- endif %}

{#- System message + builtin tools #}
{{- "<|start_header_id|>system<|end_header_id|>\n\n" }}
{%- if builtin_tools is defined or tools is not none %}
    {{- "Environment: ipython\n" }}
{%- endif %}
{%- if builtin_tools is defined %}
    {{- "Tools: " + builtin_tools | reject('equalto', 'code_interpreter') | join(", ") + "\n\n"}}     
{%- endif %}
{{- "Cutting Knowledge Date: December 2023\n" }}
{{- "Today Date: " + date_string + "\n\n" }}
{%- if tools is not none and not tools_in_user_message %}
    {{- "You have access to the following functions. To call a function, please respond with JSON for a function call." }}
    {{- 'Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}.' }}
    {{- "Do not use variables.\n\n" }}
    {%- for t in tools %}
        {{- t | tojson(indent=4) }}
        {{- "\n\n" }}
    {%- endfor %}
{%- endif %}
{{- system_message }}
{{- "<|eot_id|>" }}

{#- Custom tools are passed in a user message with some extra guidance #}
{%- if tools_in_user_message and not tools is none %}
    {#- Extract the first user message so we can plug it in here #}
    {%- if messages | length != 0 %}
        {%- set first_user_message = messages[0]['content']|trim %}
        {%- set messages = messages[1:] %}
    {%- else %}
        {{- raise_exception("Cannot put tools in the first user message when there's no first user message!") }}
{%- endif %}
    {{- '<|start_header_id|>user<|end_header_id|>\n\n' -}}
    {{- "Given the following functions, please respond with a JSON for a function call " }}
    {{- "with its proper arguments that best answers the given prompt.\n\n" }}
    {{- 'Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}.' }}
    {{- "Do not use variables.\n\n" }}
    {%- for t in tools %}
        {{- t | tojson(indent=4) }}
        {{- "\n\n" }}
    {%- endfor %}
    {{- first_user_message + "<|eot_id|>"}}
{%- endif %}

{%- for message in messages %}
    {%- if not (message.role == 'ipython' or message.role == 'tool' or 'tool_calls' in message) %}    
        {{- '<|start_header_id|>' + message['role'] + '<|end_header_id|>\n\n'+ message['content'] | trim + '<|eot_id|>' }}
    {%- elif 'tool_calls' in message %}
        {%- if not message.tool_calls|length == 1 %}
            {{- raise_exception("This model only supports single tool-calls at once!") }}
        {%- endif %}
        {%- set tool_call = message.tool_calls[0].function %}
        {%- if builtin_tools is defined and tool_call.name in builtin_tools %}
            {{- '<|start_header_id|>assistant<|end_header_id|>\n\n' -}}
            {{- "<|python_tag|>" + tool_call.name + ".call(" }}
            {%- for arg_name, arg_val in tool_call.arguments | items %}
                {{- arg_name + '="' + arg_val + '"' }}
                {%- if not loop.last %}
                    {{- ", " }}
                {%- endif %}
                {%- endfor %}
            {{- ")" }}
        {%- else  %}
            {{- '<|start_header_id|>assistant<|end_header_id|>\n\n' -}}
            {{- '{"name": "' + tool_call.name + '", ' }}
            {{- '"parameters": ' }}
            {{- tool_call.arguments | tojson }}
            {{- "}" }}
        {%- endif %}
        {%- if builtin_tools is defined %}
            {#- This means we're in ipython mode #}
            {{- "<|eom_id|>" }}
        {%- else %}
            {{- "<|eot_id|>" }}
        {%- endif %}
    {%- elif message.role == "tool" or message.role == "ipython" %}
        {{- "<|start_header_id|>ipython<|end_header_id|>\n\n" }}
        {%- if message.content is mapping or message.content is iterable %}
            {{- message.content | tojson }}
        {%- else %}
            {{- message.content }}
        {%- endif %}
        {{- "<|eot_id|>" }}
    {%- endif %}
{%- endfor %}
{%- if add_generation_prompt %}
    {{- '<|start_header_id|>assistant<|end_header_id|>\n\n' }}
{%- endif %}"""
    if modelNumber == 1:
            model = AutoModelForCausalLM.from_pretrained(
                model_path_8B, 
                quantization_config=bnb_config,
                torch_dtype=torch.float16,
                device_map="auto")
    if modelNumber == 2:
            model = AutoModelForCausalLM.from_pretrained(
                model_path_1B, 
                quantization_config=bnb_config,
                torch_dtype=torch.float16,
                device_map="auto")
    elif modelNumber == 3:
            model = AutoModel.from_pretrained("OutFlankShu/MATE/both/checkpoint-1000")
    
    return (tokenizer, model)

def __format_eval(entry):
        """Helper to format evaluation: prefer 'mate in' if available."""
        if 'mate' in entry and entry['mate'] is not None:
            return f"mate in {entry['mate']}"
        elif 'eval' in entry:
            return f"{entry['eval']} cp"
        return None


def create_prompt(fen, engine_analysis):    
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