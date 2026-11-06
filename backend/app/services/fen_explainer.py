# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import string

PIECE_NAMES = {"p": "pawn", "r": "rook", "n": "knight", "b": "bishop", "q": "queen", "k": "king"}


def _fen_to_piece_names(placement: str) -> str:
    files = string.ascii_lowercase[:8]
    output = []
    for rank_idx, rank in enumerate(placement.split("/")):
        file_idx = 0
        for char in rank:
            if char.isdigit():
                # Empty squares are not listed: small models get confused by them.
                file_idx += int(char)
            else:
                color = "white" if char.isupper() else "black"
                output.append(f"{files[file_idx]}{8 - rank_idx} has a {color} {PIECE_NAMES[char.lower()]}")
                file_idx += 1
    output.append("Every unmentioned square is empty.")
    return ", ".join(output) + "\n"


def fen_explainer(fen: str) -> tuple[str, str]:
    """Turn a FEN into a natural language description. Returns (description, side to move)."""
    placement, turn, castling, en_passant, halfmove, fullmove = fen.split()[:6]
    side = "White" if turn == "w" else "Black"

    description = [f"It's move number {int(fullmove)}.", f"It's {side}'s turn to move"]

    castling_labels = {
        "K": "White can castle kingside",
        "Q": "White can castle queenside",
        "k": "Black can castle kingside",
        "q": "Black can castle queenside",
    }
    castling_info = [label for key, label in castling_labels.items() if key in castling]
    if not castling_info:
        castling_info.append("Neither side has castling rights.")
    description.append(", ".join(castling_info))

    description.append(_fen_to_piece_names(placement))

    halfmoves = int(halfmove)
    description.append(f"There have been {halfmoves} move{'' if halfmoves == 1 else 's'} without captures.")

    if en_passant == "-":
        description.append("There are no en-passant moves to be made.")
    else:
        description.append(f"There is an en-passant capture on square {en_passant}.")

    return "\n\n".join(description), side
