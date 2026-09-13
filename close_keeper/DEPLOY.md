# Deploying close-keeper to Amazon Bedrock AgentCore Runtime

One-time AWS setup (about ten minutes):

1. **AWS Builder ID + account** — the hackathon requires a Builder ID anyway;
   create both at builder.aws.com / aws.amazon.com.
2. **Bedrock model access** — Bedrock console → Model access → enable a Claude
   model (Strands' default) in your deployment region.
3. **Local credentials** — `aws configure` (or SSO) with a principal allowed to
   use Bedrock, ECR, IAM role creation, and AgentCore.
4. **$50 hackathon credits** — request form is on the Devpost Resources tab.

Deploy:

```bash
pip install bedrock-agentcore-starter-toolkit
agentcore configure --entrypoint close_keeper/agentcore_app.py
agentcore deploy
agentcore invoke '{"prompt": "Tie out the close package, then tell me which cells need my decision."}'
```

The toolkit packages the repo, builds the container, creates the execution role,
and prints the runtime ARN. `agentcore invoke` runs the agent end-to-end on
Bedrock — the same tools, the same governance, IAM instead of API keys.

## Notes and honest limits

- **Governance travels with the tools.** Runtime hosting changes where the loop
  runs, not what it may do: `apply_review_decisions` remains the only write path
  and `memory_store` the only way a rule activates.
- **The pipeline tool's model** inside Runtime is configured in
  `harness/pipeline.py` (`--model`); its keys (`TINKER_API_KEY` etc.) must be set
  as Runtime environment variables via `agentcore configure --env`, or the
  pipeline falls back to whatever adapter has credentials.
- **Memory is ephemeral** in Runtime (per-session container filesystem). For
  durable sessions, back `memory_db` with a volume or move session state to
  AgentCore Memory — see `close_keeper/policies/README.md` for the governance
  mapping.
- **Verify before you demo:** `agentcore status`, then one `agentcore invoke`
  with the default prompt; the first cold start builds the container image and
  can take several minutes.
