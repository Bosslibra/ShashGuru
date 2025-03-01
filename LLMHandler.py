def create_prompt(fen, bestmove):
    prompt = f'''I have the following fen {fen} and my chess engine suggests the move {bestmove} (expressed in uci standard).
    Can you please explain why is this move good? Answer without filler text, in a concise manner'''
    return prompt