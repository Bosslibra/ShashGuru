from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import warnings

def load_model():
    """Load the model with proper configuration"""
    model_name = "Waterhorse/chessgpt-chat-v1"
    
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Configure tokenizer
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model with specific settings
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        low_cpu_mem_usage=True
    )
    
    return tokenizer, model

def chat_loop(tokenizer, model):
    """Main chat loop with chess-specific optimizations"""
    print("\nWelcome to ChessGPT Chat!")
    print("Type 'quit' to exit the chat.\n")
    
    chat_history = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    
    # Suppress flash attention warning
    warnings.filterwarnings("ignore", message="Torch was not compiled with flash attention")
    
    while True:
        try:
            # Get user input
            user_input = input("You: ")
            
            if user_input.lower() == 'quit':
                break
            
            # Special handling for chess analysis
            if "chess position analysis" in user_input.lower():
                response = generate_chess_analysis(tokenizer, model, user_input, device)
            else:
                response = generate_regular_response(tokenizer, model, user_input, device, chat_history)
                chat_history.append(f"User: {user_input}")
                chat_history.append(f"Assistant: {response}")
            
            print(f"\nAssistant: {response}\n")
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Please try again or rephrase your question.\n")

def generate_chess_analysis(tokenizer, model, user_input, device):
    """Specialized generation for chess analysis"""
    inputs = tokenizer(
        user_input,
        return_tensors="pt",
        max_length=1024,
        truncation=True,
        padding=True
    ).to(device)
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=400,  # More tokens for detailed analysis
        temperature=0.3,     # Lower temperature for more factual analysis
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    
    return tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

def generate_regular_response(tokenizer, model, user_input, device, chat_history):
    """Standard conversation generation"""
    prompt = "\n".join(chat_history[-6:]) + f"\nUser: {user_input}\nAssistant:"
    
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        max_length=1024,
        truncation=True,
        padding=True
    ).to(device)
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        temperature=0.7,
        top_p=0.95,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    
    return tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

if __name__ == "__main__":
    tokenizer, model = load_model()
    chat_loop(tokenizer, model)