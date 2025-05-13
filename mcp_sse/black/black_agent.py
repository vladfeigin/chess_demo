# ──────────────────────────────────────────────
# 1.black_agent.py
# ──────────────────────────────────────────────
"""Black Pieces Player Chess Agent (SSE transport). Start with:
    
"""
import os
import sys
import chess
import logging
from mcp.server.fastmcp import FastMCP
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv
load_dotenv()


logging.basicConfig(level=logging.INFO, format="[BlackAgent] %(message)s")
log = logging.getLogger(__name__)

board = chess.Board()

mcp = FastMCP(name="Black Pieces Chess Agent",
              description="Black pieces chess agent using SSE transport",
              base_url="http://localhost:8000",

              describe_all_responses=True,  # Include all possible response schemas
              describe_full_response_schema=True)  # Include full JSON schema in descriptions)

client = AzureOpenAIChatCompletionClient(
    model="gpt-4o",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    api_version="2024-02-15-preview",
)
agent = AssistantAgent(
    name="black_pieces_player",
    model_client=client,
    description="""You are a chess player, playing with BLACK pieces. 
                    Before you decide about a next move, you must analyze the current 
                    board state and provide a legal best move in UCI notation. 
                    Provide LEGAL MOVES in UCI notation only.
                    Double check and reason about the selected move before sending it. 
                    Your goal is to win the game.""",
    system_message=
        """
            You are a world-renowned chess grandmaster. You play BLACK.
            Respond only with one legal UCI move (e.g. e7e5) for the given FEN.
            You must output exactly ONE move in Universal Chess Interface (UCI) format:
                • four characters like e2e4, or
                • five if promotion, e.g. e7e8q
                No capture symbol (x), no checks (+/#), no words. Output ONLY the move.
            Double-check the move is legal in the current position.
            Do not make stupid moves!
            Follow these basic rules:
            • Prevent the most common blunder (self-check).
            • Avoid pointless sacrifices.
            • Stop discovered checks / loss of the queen.
            • Bishops, rooks and queens cannot jump over pieces.
            • Pawns never move backwards or capture straight ahead.
            • Your move must remove any check to your own king. If not, try again.
        """)

@mcp.tool(
    name="move",
    description="Return a legal black move in UCI for the provided FEN.",
)
async def move_tool(fen: str):
    """Return next black move (UCI)."""
    log.info(f"[BlackAgent] Received move request. FEN: {fen}")
    
    # Verify that we got a valid FEN string, not a UCI move
    if len(fen.split()) < 4 or '/' not in fen:
        log.error(f"[BlackAgent] ERROR: Invalid FEN format: {fen}")
        return {"error": f"Invalid input: expected FEN position string, got '{fen}'"}
    
    try:
        board.set_fen(fen)
    except ValueError as e:
        log.error(f"[BlackAgent] ERROR: Cannot set board from FEN: {e}")
        return {"error": f"Invalid FEN: {str(e)}"}
    
    # Make sure it' black's turn in this position
    if board.turn:
        log.info("[BlackAgent] ERROR: It's white's turn in this position, but I'm the black pieces player")
        return {"error": "It's not black's turn in this position"}
    
    prompt = f"You are black pieces player. Current board FEN: {fen}. Provide one legal move in UCI only."
    resp = await agent.run(task=prompt)
    uci_raw = resp.messages[-1].content   # e.g. "e2e4 TERMINATE"
    uci = uci_raw.split()[0]              # take first token → "e2e4"
    log.info("[BlackAgent] LLM suggested: %s", uci)
    
    # Validate the UCI move
    try:
        mv = chess.Move.from_uci(uci)
        if mv not in board.legal_moves:
            log.info("[BlackAgent] Illegal move detected -> %s", uci)
            return {"error": f"illegal move {uci}"}
    except ValueError:
        log.error(f"[BlackAgent] Invalid UCI format: {uci}")
        return {"error": f"Invalid UCI move format: {uci}"}
        
    log.info("[BlackAgent] Move accepted -> %s", uci)
    return {"uci": uci}

if __name__ == "__main__":
    # mcp is your FastMCP instance
    mcp.run(transport='sse')
