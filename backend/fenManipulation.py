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
#along with this program.  If not, see <https://www.gnu.org/licenses/>.


import string

# Helper function, not my code
def __fen_to_piece_names(fen):
    ranks = fen.split()[0].split('/')  # Extract the board layout
    piece_names = {
        'p': 'pawn', 'r': 'rook', 'n': 'knight', 'b': 'bishop', 'q': 'queen', 'k': 'king'
    }
    
    files = string.ascii_lowercase[:8]  # 'a' to 'h'
    output = []
    
    for rank_idx, rank in enumerate(ranks):
        file_idx = 0  # Tracks file letter (column)
        for char in rank:
            if char.isdigit():  # Empty squares
                for _ in range(int(char)):
                    ## output.append(f"{files[file_idx]}{8 - rank_idx} is empty") removed because 1B freaks out
                    file_idx += 1
            else:  # Piece found
                color = 'white' if char.isupper() else 'black'
                piece = piece_names[char.lower()]
                output.append(f"{files[file_idx]}{8 - rank_idx} has a {color} {piece}")
                file_idx += 1
    output.append("Every unmentioned square is empty.")
    return ", ".join(output) + "\n"

# Main fuction, to be called outside
def fen_explainer(fen) -> str:
    description = []

    firstsplit = fen.split()

    # Move number
    description.append(f"It's move number {int(firstsplit[5])}.")

    # Whose move is it
    side2play = firstsplit[1]
    side = "White" if side2play == "w" else  "Black"
    description.append(f"It's {side}'s turn to move")

    # Castling
    castling_rights = list(firstsplit[2])
    castling_info = []
    if 'K' in castling_rights:
            castling_info.append("White can castle kingside")
    if 'Q' in castling_rights:
        castling_info.append("White can castle queenside")
    if 'k' in castling_rights:
        castling_info.append("Black can castle kingside")
    if 'q' in castling_rights:
        castling_info.append("Black can castle queenside")
    if castling_rights == "-":
        castling_info.append("Neither side has castling rights.")
    castling_info = ", ".join(castling_info)
    description.append(castling_info)

    # Piece splitting
    description.append(__fen_to_piece_names(firstsplit[0]))

    # 50-move rule
    description.append(f"There have been {int(firstsplit[4])} move{'s' if int(firstsplit[4]) > 1 else ''} without captures.")

    # En-passant
    if firstsplit[3] == "-":
        description.append("There are no en-passant moves to be made.")
    else:
        description.append(f"There is an en-passant capture on square {firstsplit[3]}.")
    explainedFEN = "\n\n".join(description)
    return explainedFEN, side