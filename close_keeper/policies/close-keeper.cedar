// close-keeper — AgentCore Policy (Cedar) for the Gateway boundary.
//
// The same governance the tools enforce in code, restated at the platform
// boundary: even a fully compromised agent loop cannot write a review decision
// or activate a business rule, because those calls never pass the Gateway.
//
// Conventions:
//   - Tools are exposed through one Gateway target named "CloseKeeper"
//     (actions are AgentCore::Action::"CloseKeeper___<tool>").
//   - The agent runs under the Runtime execution role (AgentCore::IamEntity).
//   - Human reviewers authenticate as AgentCore::OAuthUser tagged
//     role="close-reviewer" (or adapt the IAM variant below).
//   - GATEWAY_ARN is substituted at deploy time.
//
// Semantics: default-deny, forbid-wins.

// ---------------------------------------------------------------- reads
// The agent may inspect freely: read tools carry no write risk.
permit(
  principal is AgentCore::IamEntity,
  action in [
    AgentCore::Action::"CloseKeeper___tie_out_workbook",
    AgentCore::Action::"CloseKeeper___list_exceptions",
    AgentCore::Action::"CloseKeeper___list_memory_rules",
    AgentCore::Action::"CloseKeeper___suggest_mappings",
    AgentCore::Action::"CloseKeeper___preview_workbook"
  ],
  resource == AgentCore::Gateway::"GATEWAY_ARN"
);

// ------------------------------------------------- the recorded write path
// Review decisions are the ONE write path to a workbook — and they belong to
// a human reviewer, never to the agent.
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"CloseKeeper___apply_review_decisions",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  principal.hasTag("role") && principal.getTag("role") == "close-reviewer"
};

// The agent's own Runtime role is forbidden outright. Forbid wins over any
// permit, present or future — this is the platform restating what
// exceptions.apply_decisions already enforces in code.
forbid(
  principal is AgentCore::IamEntity,
  action == AgentCore::Action::"CloseKeeper___apply_review_decisions",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
);

// ------------------------------------------------------- memory governance
// Recording evidence and proposing candidates is safe for the agent: both are
// inert until a reviewer validates and activates.
permit(
  principal is AgentCore::IamEntity,
  action in [
    AgentCore::Action::"CloseKeeper___record_correction",
    AgentCore::Action::"CloseKeeper___propose_rule"
  ],
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  context.input has reviewer && context.input.reviewer != ""
};

// A correction without a rationale is refused at the boundary too
// (memory_store.required_text refuses it again in the tool).
forbid(
  principal is AgentCore::IamEntity,
  action == AgentCore::Action::"CloseKeeper___record_correction",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
unless {
  context.input has rationale && context.input.rationale != ""
};

// Validate / activate / revoke change what memory DOES, so they require the
// reviewer identity at the boundary. The tool still applies its own replay
// gate on top — two independent layers must both say yes.
permit(
  principal is AgentCore::OAuthUser,
  action in [
    AgentCore::Action::"CloseKeeper___validate_rule",
    AgentCore::Action::"CloseKeeper___activate_rule",
    AgentCore::Action::"CloseKeeper___revoke_rule"
  ],
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  principal.hasTag("role") && principal.getTag("role") == "close-reviewer"
};

forbid(
  principal is AgentCore::IamEntity,
  action in [
    AgentCore::Action::"CloseKeeper___activate_rule",
    AgentCore::Action::"CloseKeeper___revoke_rule"
  ],
  resource == AgentCore::Gateway::"GATEWAY_ARN"
);
