# board_orchestrator_stdio.py

import asyncio
import json
import os
import sys
import chess
import chess.pgn
from chessboard import display
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

# Force STDIO transport in child MCP servers
os.environ.setdefault("MCP_PROTOCOL", "stdio")

# Absolute paths for consistency
WHITE_PATH = os.path.join(os.getcwd(), "WhiteAgent.py")
BLACK_PATH = os.path.join(os.getcwd(), "BlackAgent.py")

# Board customization options
BOARD_SIZE = 600  # Size in pixels
DARK_SQUARE_COLOR = "#8B4513"  # Saddle Brown
LIGHT_SQUARE_COLOR = "#F5DEB3"  # Wheat
HIGHLIGHT_COLOR = "#32CD32"  # Lime Green

moves_history = []

async def run() -> None:
    board = chess.Board()
    
    # Start the display with correct parameter names
    game_board = display.start( )
                               
   
    # Spawn two MCP servers over STDIO
    white_params = StdioServerParams(
        command=sys.executable,
        args=["-u", WHITE_PATH],
        timeout=90
    )
    black_params = StdioServerParams(
        command=sys.executable,
        args=["-u", BLACK_PATH],
        timeout=90
    )

    async with McpWorkbench(server_params=white_params) as wb_white, \
               McpWorkbench(server_params=black_params) as wb_black:

        # White starts
        current_wb, current_name = wb_white, "white"
        other_wb, other_name     = wb_black, "black"
        max_num_invalid_moves = 5
        num_invalid_moves = 0

        while not board.is_game_over():
            fen = board.fen()
            print(f"[Board] Asking {current_name} for move. FEN: {fen}", flush=True)

            #call tool by name    
            result = await current_wb.call_tool("move", {"fen": fen} )  #  [oai_citation:0‡Microsoft GitHub](https://microsoft.github.io/autogen/stable//reference/python/autogen_ext.tools.mcp.html?utm_source=chatgpt.com)
            print("tool result :", result.result[0].content) 
            # `result` is a ToolResult; `.content` holds the JSON payload
            #check if result is not empty and contains a valid move
            if not result.result[0].content:
                print(f"[Board] {current_name.title()}Agent error: No move found", flush=True)
                continue
            payload = json.loads(result.result[0].content) 
            print("payload:", payload)
            #check if result is an error, then try again to get valid move
            if "error" in payload: # and num_invalid_moves < max_num_invalid_moves:
                print("num_invalid_moves:", num_invalid_moves)
                print(f"[Board] {current_name.title()}Agent error:", payload, flush=True)
                num_invalid_moves += 1
                continue
            else:
                num_invalid_moves = 0
            
            uci     = payload.get("uci")
            print("uci:", uci)

            if not uci:
                print(f"[Board] {current_name.title()}Agent error:", payload, flush=True)
                break

            # Validate the move
            try:
                mv = chess.Move.from_uci(uci)
                if mv not in board.legal_moves:
                    raise ValueError("illegal")
            except Exception as e:
                print(f"[Board] Illegal move from {current_name}: {uci} ({e})", flush=True)
                break

            board.push_uci(uci)
            
            display.update(board.fen(), game_board)  
            print(f"[Board] Applied {uci}", flush=True)
            
            moves_history.append(uci)

            # swap players
            current_wb, other_wb       = other_wb, current_wb
            current_name, other_name   = other_name, current_name
            await asyncio.sleep(3)

    if board.is_game_over():
        result = board.result()
        reason = "Checkmate" if board.is_checkmate() else (
                 "Stalemate" if board.is_stalemate() else (
                 "Insufficient material" if board.is_insufficient_material() else (
                 "Fifty-move rule" if board.can_claim_fifty_moves() else (
                 "Threefold repetition" if board.can_claim_threefold_repetition() else "Unknown"))))
        print(f"[Board] Game over: {result} - Reason: {reason}")

    pgn = chess.pgn.Game.from_board(board)
    # display the board + history
    print(board)              # ASCII art from python-chess
    print("Moves so far:", " ".join(moves_history), flush=True)
    print("pgn:", pgn)  
    with open("game_record.pgn", "w") as f:
        f.write(str(pgn))
    print(f"[Board] Game saved to game_record.pgn")

    display.terminate()   
    await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run())