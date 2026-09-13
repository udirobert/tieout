# Two-layer governance: the tools, then the platform

close-keeper's working agreement is enforced where it cannot be talked out of:

| rule | tool layer (always on) | platform layer (AgentCore Policy) |
|---|---|---|
| Approved values are written only through one recorded path | `exceptions.apply_decisions` persists the decision before touching a workbook; no other tool writes | `CloseKeeper___apply_review_decisions` is forbidden for the agent's Runtime role — permit requires `role="close-reviewer"` |
| A correction is evidence, not behavior | `memory_store`: candidate → validated → active, each transition recorded | `record_correction` without a rationale is forbidden at the boundary |
| Rules activate only after the replay gate | `activate()` replays stored cases and refuses ineligible candidates | `activate_rule` / `revoke_rule` / `validate_rule` require the reviewer identity; the agent role is forbidden |

The layers are independent: bypass the tool (prompt injection, a compromised
loop, a bug in our own code) and the Gateway still says no. Bypass the Gateway
(call the tool directly) and the store still says no. That independence is the
point — one layer's failure is the other layer's demo.

## Using the policies

1. Expose the close-keeper tools through an AgentCore Gateway target named
   `CloseKeeper` (the Cedar action names assume it).
2. Substitute `GATEWAY_ARN` in `close-keeper.cedar` with the deployed Gateway ARN.
3. Create a policy engine, add the policies, associate it with the Gateway
   (console: Bedrock AgentCore → Policy; or `aws bedrock-agentcore-control`).
4. Authenticate reviewers as OAuth users tagged `role="close-reviewer"`, or adapt
   the `AgentCore::IamEntity` principal to your reviewer role ARN (the IAM
   variant pattern is in the AWS example-policies doc).

## Status

Authored against the AgentCore Policy GA docs (Cedar schema, `context.input`
access, forbid-wins semantics) — not yet exercised against a live Gateway;
that's the deploy step in `close_keeper/DEPLOY.md`. The natural-language
authoring path in the console can also validate these against the tool schema
and flag unsatisfiable conditions before enforcement.
