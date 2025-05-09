# ──────────────────────────────────
# black_agent.py   (container: black-player)
# ──────────────────────────────────
"""Identical to white_agent but for black side (port 5002)."""
import os, chess, sys
from mcp.server.fastmcp import FastMCP
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv
load_dotenv()

board = chess.Board()

mcp = FastMCP(title="Black Chess Agent", protocol_version="0.2.0")

model_client = AzureOpenAIChatCompletionClient(
    model="gpt-4o",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    api_version="2024-02-15-preview",
)
black_llm = AssistantAgent("black_player",description= "You are a black chess player. You should analyze the current board and provide a legal best move in UCI notation." , model_client=model_client)

@mcp.tool(
    name="move",
    description="Generate a legal black move in UCI (Universal Chess Interface) notation based on current FEN (Forsyth-Edwards Notation).",
   
)
#rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1

async def move_tool(fen: str):
    print("[BlackAgent] Received move request. FEN:", fen, file=sys.stderr)
    
    # Verify that we got a valid FEN string, not a UCI move
    if len(fen.split()) < 4 or '/' not in fen:
        print(f"[BlackAgent] ERROR: Invalid FEN format: {fen}", file=sys.stderr)
        return {"error": f"Invalid input: expected FEN position string, got '{fen}'"}
    
    try:
        board.set_fen(fen)
    except ValueError as e:
        print(f"[BlackAgent] ERROR: Cannot set board from FEN: {e}", file=sys.stderr)
        return {"error": f"Invalid FEN: {str(e)}"}
    
    # Make sure it's black's turn in this position
    if board.turn:
        print("[BlackAgent] ERROR: It's white's turn in this position, but I'm the black player", file=sys.stderr)
        return {"error": "It's not black's turn in this position"}
    
    prompt = f"You are black. Current board FEN: {fen}. Provide one legal move in UCI only."
    resp = await black_llm.run(task=prompt)
    uci_raw = resp.messages[-1].content        # e.g. "e2e4 TERMINATE"
    uci = uci_raw.split()[0]              # take first token → "e2e4"
    print("[BlackAgent] LLM suggested:", uci, file=sys.stderr)
    
    # Validate the UCI move
    try:
        mv = chess.Move.from_uci(uci)
        if mv not in board.legal_moves:
            print("[BlackAgent] Illegal move detected ->", uci, file=sys.stderr)
            return {"error": f"illegal move {uci}"}
    except ValueError:
        print(f"[BlackAgent] Invalid UCI format: {uci}", file=sys.stderr)
        return {"error": f"Invalid UCI move format: {uci}"}
    
    print("[BlackAgent] Move accepted ->", uci, file=sys.stderr)
    return {"uci": uci}

if __name__ == "__main__":
    # Initialize and run the server
    print("Starting Black Player Agent...", file=sys.stderr)
    
    # Diagnostic info
    print(f"[BlackAgent] Python path: {sys.executable}", file=sys.stderr)
    print(f"[BlackAgent] Package versions:", file=sys.stderr)
    print(f"  - mcp: {mcp.__version__ if hasattr(mcp, '__version__') else 'unknown'}", file=sys.stderr)
    print(f"  - chess: {chess.__version__ if hasattr(chess, '__version__') else 'unknown'}", file=sys.stderr)
    
    protocol = os.getenv("MCP_PROTOCOL", "stdio").lower()
    print("[BlackAgent] Transport:", protocol, file=sys.stderr)
    
    try:
        # Simple transport detection
        print(f"[BlackAgent] Starting in {protocol.upper()} mode", file=sys.stderr)
        sys.stderr.flush()
        mcp.run(transport=protocol)
    except Exception as e:
        import traceback
        print(f"[BlackAgent] !!! ERROR STARTING SERVER: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Re-raise the exception after logging
        raise

