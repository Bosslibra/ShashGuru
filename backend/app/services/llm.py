# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import logging
from typing import Any, Optional

import chess

from app.services.fen_explainer import fen_explainer

log = logging.getLogger(__name__)

MAX_HISTORY = 10

SYSTEM_MESSAGES = {
    'default': '''
You are a concise chess analysis assistant. For initial position analysis, provide brief, accurate insights based only on the given information.
Focus on the most important aspects: the recommended move and its purpose.
Keep responses short (2-3 sentences max). Avoid speculation or moves not mentioned in the analysis.
Use clear, natural chess language without unnecessary elaboration.

For follow-up questions, refer back to the position and engine analysis provided in the conversation context.
Maintain the same brevity and focus on concrete information when answering follow-ups.

If asked about moves that were not analyzed by the engine, respond that you don't have analysis for those moves and suggest the user try those moves on the board and re-run the analysis to get engine evaluation for them.
''',
    'grandmaster': '''
You are a distinguished grandmaster providing professional chess analysis. Draw from deep strategic understanding and classical chess principles.
Analyze positions with the precision and depth of a world-class player. Reference opening principles, middlegame strategy, and endgame technique as appropriate.
Use sophisticated chess terminology and explain the deeper strategic concepts behind moves.
Provide insights that would be valuable to serious competitive players, focusing on long-term positional factors and tactical nuances.
Keep responses focused and concise - avoid lengthy explanations. 3-4 sentences maximum.

For follow-up questions, maintain the same authoritative and educational tone, always grounding responses in sound chess theory while staying brief.
''',
}

STYLE_LABELS = {
    'default': 'Commentator',
    'grandmaster': 'Grandmaster',
}


def get_analysis_styles() -> list[dict[str, str]]:
    return [{"value": key, "label": STYLE_LABELS.get(key, key.title())} for key in SYSTEM_MESSAGES]


def is_known_style(style: str) -> bool:
    return style in SYSTEM_MESSAGES


# ---------------------------------------------------------------- prompts ---

# (upper bound inclusive on the rounded win probability, template)
_WINPROB_TEXT = [
    (5, "{side} has a decisive disadvantage, with the position clearly leading to a loss."),
    (10, "{side} has decisive disadvantage: the opponent has a dominant position and is likely winning."),
    (15, "{side} has clear disadvantage: a substantial positional disadvantage, but a win is not yet inevitable."),
    (20, "{side} has a significant disadvantage: difficult to recover."),
    (24, "{side} has a slight disadvantage with a positional edge, but no immediate threats."),
    (49, "{side} is in a defensive position. The opponent has an initiative."),
    (50, "The position is equal. Both sides are evenly matched, with no evident advantage."),
    (75, "{side} has initiative: by applying pressure and it can achieve an edge with active moves and forcing ideas."),
    (79, "{side} has a slight advantage: a minor positional edge, but it’s not decisive."),
    (84, "{side} is slightly better, tending toward a clear advantage. The advantage is growing, but the position is still not decisive."),
    (89, "{side} has a clear advantage: a significant edge, but still with defensive chances."),
    (94, "{side} has a dominant position, almost decisive, not quite winning yet, but trending toward victory."),
    (100, "{side} has a decisive advantage, with victory nearly assured."),
]


def map_win_prob(winprob: Optional[float], side: str) -> str:
    if winprob is None or not 0 <= winprob <= 100:
        return ("Total chaos: unclear position, dynamically balanced, with no clear advantage "
                "for either side and no clear positional trends.")
    rounded = round(winprob)
    for upper, text in _WINPROB_TEXT:
        if rounded <= upper:
            return text.format(side=side)
    return _WINPROB_TEXT[-1][1].format(side=side)


def generate_line(line: list[str], board: chess.Board) -> str:
    """SAN continuation of a PV, skipping its first move (that one is named separately)."""
    tmp = board.copy()
    san_line = []
    for idx, uci in enumerate(line):
        move = chess.Move.from_uci(uci)
        san = tmp.san(move)
        if idx > 0:
            san_line.append(san)
        tmp.push(move)
    return " ".join(san_line)


def analyze_position_context(board: chess.Board) -> str:
    context = []
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    pieces = board.piece_map().values()
    white = sum(values[p.piece_type] for p in pieces if p.color == chess.WHITE)
    black = sum(values[p.piece_type] for p in pieces if p.color == chess.BLACK)
    if white > black:
        context.append(f"Material: White is ahead by {white - black} points")
    elif black > white:
        context.append(f"Material: Black is ahead by {black - white} points")
    else:
        context.append("Material: Equal material")

    wk, bk = board.king(chess.WHITE), board.king(chess.BLACK)
    if wk is not None:
        file, rank = chess.square_file(wk), chess.square_rank(wk)
        if rank <= 1 and (file <= 2 or file >= 5):
            context.append("White king appears castled/safe")
        elif rank >= 3:
            context.append("White king is exposed in the center")
    if bk is not None:
        file, rank = chess.square_file(bk), chess.square_rank(bk)
        if rank >= 6 and (file <= 2 or file >= 5):
            context.append("Black king appears castled/safe")
        elif rank <= 4:
            context.append("Black king is exposed in the center")

    if board.is_check():
        context.append(f"{'White' if board.turn == chess.WHITE else 'Black'} king is in check")

    total = len(board.piece_map())
    if total > 24:
        context.append("Position: Opening/Early middlegame")
    elif total > 12:
        context.append("Position: Middlegame")
    else:
        context.append("Position: Endgame")
    return "; ".join(context)


def _default_prompt(fen_text: str, side: str, context: str, best: dict[str, Any]) -> str:
    return f"""{fen_text}

{context}

The engine recommends {side} to play {best['move_san']}, leading to the continuation {best['continuation']}. The position evaluation shows that {best['evaluation'].lower()}.

In 2-3 sentences, explain why {best['move_san']} is the strongest choice and what this evaluation means for {side}'s position. Focus only on the concrete information provided."""


def _grandmaster_prompt(fen_text: str, side: str, context: str, moves: list[dict[str, Any]]) -> str:
    moves_text = "\n".join(
        f"{m['rank']}. {m['move_san']} - {m['evaluation']} (continuation: {m['continuation']})" for m in moves
    )
    return f"""{fen_text}

{context}

Side to move: {side}

Engine Analysis - Top Candidate Moves:
{moves_text}

As a grandmaster, provide a professional analysis of this position. Evaluate the strategic merits of the top recommendation, consider the alternative options, and explain the underlying chess principles that make these moves strong. Address both tactical and positional factors that influence the evaluation."""


def create_analysis_prompt(fen: str, engine_lines: list[dict[str, Any]], style: str = 'default') -> str:
    """Build the user prompt from the engine lines (see services.engine_pool)."""
    fen_text, side = fen_explainer(fen)
    board = chess.Board(fen)
    context = analyze_position_context(board)

    moves = []
    for idx, line in enumerate(engine_lines[:3]):
        if not line["pv"]:
            continue
        moves.append({
            'rank': idx + 1,
            'move_san': board.san(chess.Move.from_uci(line["pv"][0])),
            'move_uci': line["pv"][0],
            'evaluation': map_win_prob(line.get("winprob"), side),
            'continuation': generate_line(line["pv"][:4], board),
        })
    if not moves:
        raise ValueError("No engine lines to build a prompt from")

    if style == 'grandmaster':
        return _grandmaster_prompt(fen_text, side, context, moves)
    return _default_prompt(fen_text, side, context, moves[0])


# --------------------------------------------------------------- messages ---

def build_messages(prompt: str, history: Optional[list[dict[str, str]]], style: str) -> list[dict[str, str]]:
    """System message + trimmed history + the new user prompt.

    The first history message holds the analysis context, so it is always kept.
    """
    history = list(history or [])
    if len(history) > MAX_HISTORY:
        history = history[:1] + history[-(MAX_HISTORY - 1):]
    system = SYSTEM_MESSAGES.get(style, SYSTEM_MESSAGES['default'])
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": prompt}]
