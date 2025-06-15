import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import warnings
from typing import List

class ChessGPTChat:
    def __init__(self):
        self.tokenizer, self.model = self._load_model()
        self.chat_history: List[str] = []
        self.system_message = """You are ChessGPT, an AI chess assistant with a friendly and conversational style. 
When analyzing positions:
- Use natural language and complete sentences
- Explain concepts clearly for players of all levels
- Structure your analysis with clear paragraphs
- Use chess terms but explain them when needed
- Maintain a helpful, enthusiastic tone
For non-chess chat, be warm and engaging."""
        
    def _load_model(self):
        """Load model with optimized settings"""
        tokenizer = AutoTokenizer.from_pretrained("Waterhorse/chessgpt-chat-v1")
        model = AutoModelForCausalLM.from_pretrained(
            "Waterhorse/chessgpt-chat-v1",
            torch_dtype=torch.float16,
            device_map="auto"
        )
        return tokenizer, model

    def _format_chess_prompt(self, user_input: str) -> str:
        """Special formatting for chess analysis requests"""
        if "chess position" in user_input.lower() or "fen" in user_input.lower():
            return f"[CHESS MODE]\n{user_input}\n[ANALYSIS REQUEST]\n"
        return user_input

    def generate_response(self, user_input: str) -> str:
        """Generate response with chess-specific optimizations"""
        formatted_input = self._format_chess_prompt(user_input)
        prompt = "\n".join(self.chat_history[-6:] + [f"User: {formatted_input}", "Assistant:"])
        
        inputs = self.tokenizer(prompt, return_tensors='pt').to(self.model.device)
        input_length = inputs.input_ids.shape[1]
        
        # Different parameters for chess vs regular chat
        gen_kwargs = {
            "max_new_tokens": 300 if "chess" in formatted_input.lower() else 128,
            "temperature": 0.3 if "chess" in formatted_input.lower() else 0.7,
            "do_sample": True,
            "top_p": 0.9,
            "pad_token_id": self.tokenizer.eos_token_id,
            "repetition_penalty": 1.1
        }
        
        with torch.no_grad():
            outputs = self.model.generate(**inputs, **gen_kwargs)
        
        response = self.tokenizer.decode(
            outputs[0][input_length:], 
            skip_special_tokens=True
        ).strip()
        
        # Clean up chess-specific responses
        if "chess" in formatted_input.lower():
            response = self._clean_chess_response(response)
        
        return response

    def _clean_chess_response(self, response: str) -> str:
        """Post-process chess analysis responses"""
        # Remove any trailing incomplete analysis
        for end_marker in ["\nUser:", "[ANALYSIS END]", "<|endoftext|>"]:
            if end_marker in response:
                response = response.split(end_marker)[0]
        return response.strip()

    def chat_loop(self):
        print("\nChessGPT Chat - Enter your move/position or 'quit' to exit\n")
        while True:
            try:
                user_input = input("You: ")
                if user_input.lower() == 'quit':
                    break
                
                response = self.generate_response(user_input)
                self.chat_history.extend([f"User: {user_input}", f"Assistant: {response}"])
                
                print(f"\nAssistant: {response}\n")
                
            except Exception as e:
                print(f"\nError: {e}\nPlease try again.\n")

if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="Torch was not compiled with flash attention")
    chat = ChessGPTChat()
    chat.chat_loop()