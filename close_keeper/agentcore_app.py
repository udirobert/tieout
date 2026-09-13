"""close-keeper on Amazon Bedrock AgentCore Runtime.

Deploy (needs an AWS account with Bedrock model access — see DEPLOY.md):

    pip install bedrock-agentcore-starter-toolkit
    agentcore configure --entrypoint close_keeper/agentcore_app.py
    agentcore deploy
    agentcore invoke '{"prompt": "Tie out the close package, then tell me which cells need my decision."}'

Inside the Runtime the model is Bedrock (IAM, no keys); the workspace paths come
from CLOSE_KEEPER_DATASET_DIR / CLOSE_KEEPER_OUT_DIR / CLOSE_KEEPER_MEMORY_DB
with repo-local defaults. Writes stay behind the same governed tools — Runtime
hosting changes where the loop runs, not what it may do.
"""

import os
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from close_keeper.agent import DEFAULT_DATASET_DIR, DEFAULT_OUT_DIR, make_agent

app = BedrockAgentCoreApp()

DATASET_DIR = os.environ.get("CLOSE_KEEPER_DATASET_DIR", str(DEFAULT_DATASET_DIR))
OUT_DIR = os.environ.get("CLOSE_KEEPER_OUT_DIR", str(DEFAULT_OUT_DIR))
MEMORY_DB = os.environ.get("CLOSE_KEEPER_MEMORY_DB", str(DEFAULT_OUT_DIR / "memory.sqlite3"))

Path(OUT_DIR).mkdir(parents=True, exist_ok=True)


@app.entrypoint
def invoke(payload, context=None):
    prompt = (payload or {}).get("prompt") or (
        "Tie out the close package, then tell me which cells need my decision and why."
    )
    agent = make_agent(None, DATASET_DIR, OUT_DIR, MEMORY_DB)  # None: Strands default Bedrock
    return {"result": str(agent(prompt))}


if __name__ == "__main__":
    app.run()
