# ==================================
# Chess Agents Project – Three‑Agent Design (AutoGen 0.5.x + FastMCP)
# --------------------------------------------------------------
# 1. white_agent.py  → MCP server that decides WHITE's move.
# 2. black_agent.py  → MCP server that decides BLACK's move.
# 3. chess_board_agent.py → Orchestrator (MCP *client*) that asks the two
#    servers for moves over SSE, updates an in‑memory board, and renders
#    the UI. Communication is strictly hub‑and‑spoke: white ⇄ board ⇄ black.
# --------------------------------------------------------------
# Requirements (each container):
#   pip install autogen-agentchat==0.5.* autogen-ext[openai,mcp]==0.5.* \
#               fastapi uvicorn python-chess chessboard mcp-fast
#   AZURE_OPENAI_ENDPOINT / API_KEY / DEPLOYMENT env vars per image.
# ==================================

# ──────────────────────────────────
# white_agent.py   (container: white-player)
# ──────────────────────────────────
"""MCP server that plays WHITE pieces. Exposes `move` tool via FastMCP.
The move is chosen by an AutoGen AssistantAgent backed by Azure OpenAI."""
import os, chess, sys
from mcp.server.fastmcp import FastMCP
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
# add load env variables
from dotenv import load_dotenv
load_dotenv()

board = chess.Board()  # local board for legal‑move validation only

mcp = FastMCP(title="White Chess Agent")

model_client = AzureOpenAIChatCompletionClient(
    model="gpt-4o",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    api_version="2024-02-15-preview",
)
white_llm = AssistantAgent(
    name="white_player",
    description=""" You are a chess player, playing with white pieces. 
                    Before you decide about a next move, you must analyze the current 
                    board state and provide a legal best move in UCI notation. 
                    Provide LEGAL MOVES in UCI notation only.
                    Double check and reason about the selected move before sending it. 
                    Your goal is to win the game.""",
    model_client=model_client,
)
#rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1

@mcp.tool(
    name="move",
    description="Generate a legal white move in UCI notation based on current FEN."
)
async def move_tool(fen: str):
    """Return next white move (UCI)."""
    print("[WhiteAgent] Received move request. FEN:", fen, file=sys.stderr)
    
    # Verify that we got a valid FEN string, not a UCI move
    if len(fen.split()) < 4 or '/' not in fen:
        print(f"[WhiteAgent] ERROR: Invalid FEN format: {fen}", file=sys.stderr)
        return {"error": f"Invalid input: expected FEN position string, got '{fen}'"}
    
    try:
        board.set_fen(fen)
    except ValueError as e:
        print(f"[WhiteAgent] ERROR: Cannot set board from FEN: {e}", file=sys.stderr)
        return {"error": f"Invalid FEN: {str(e)}"}
    
    # Make sure it's white's turn in this position
    if not board.turn:
        print("[WhiteAgent] ERROR: It's black's turn in this position, but I'm the white player", file=sys.stderr)
        return {"error": "It's not white's turn in this position"}
    
    prompt = f"You are white. Current board FEN: {fen}. Provide one legal move in UCI only."
    resp = await white_llm.run(task=prompt)
    uci_raw = resp.messages[-1].content        # e.g. "e2e4 TERMINATE"
    uci = uci_raw.split()[0]              # take first token → "e2e4"
    print("[WhiteAgent] LLM suggested:", uci, file=sys.stderr)
    
    # Validate the UCI move
    try:
        mv = chess.Move.from_uci(uci)
        if mv not in board.legal_moves:
            print("[WhiteAgent] Illegal move detected ->", uci, file=sys.stderr)
            return {"error": f"illegal move {uci}"}
    except ValueError:
        print(f"[WhiteAgent] Invalid UCI format: {uci}", file=sys.stderr)
        return {"error": f"Invalid UCI move format: {uci}"}
        
    print("[WhiteAgent] Move accepted ->", uci, file=sys.stderr)
    return {"uci": uci}

if __name__ == "__main__":
    # Initialize and run the server
    print("Starting White Player Agent...", file=sys.stderr)
    
    # Diagnostic info
    print(f"[WhiteAgent] Python path: {sys.executable}", file=sys.stderr)
    print(f"[WhiteAgent] Package versions:", file=sys.stderr)
    print(f"  - mcp: {mcp.__version__ if hasattr(mcp, '__version__') else 'unknown'}", file=sys.stderr)
    print(f"  - chess: {chess.__version__ if hasattr(chess, '__version__') else 'unknown'}", file=sys.stderr)
    
    # Decide which transport to expose based on environment variable.
    #   MCP_PROTOCOL=stdio  → run over stdin/stdout (default for local dev)
    #   MCP_PROTOCOL=sse    → start an HTTP SSE server (prod / container)
    protocol = os.getenv("MCP_PROTOCOL", "stdio").lower()
    print("[WhiteAgent] Transport:", protocol, file=sys.stderr)
    
    try:
        # Simple transport detection
        print(f"[WhiteAgent] Starting in {protocol.upper()} mode", file=sys.stderr)
        sys.stderr.flush()
        mcp.run(transport=protocol)
    except Exception as e:
        import traceback
        print(f"[WhiteAgent] !!! ERROR STARTING SERVER: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Re-raise the exception after logging
        raise
