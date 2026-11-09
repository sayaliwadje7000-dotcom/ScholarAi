# Phase 17.5 — LLM Tool Calling Architecture

## Objective

Establish a controlled architecture through which ScholarAI's
LLM can request approved application tools.

## Architecture Components

1. LLM tool configuration
2. Typed tool schemas
3. Central tool registry
4. Pydantic argument validation
5. Authentication requirement checks
6. Asynchronous execution engine
7. Execution timeout
8. Request call limit
9. Structured execution results
10. Logging and failure handling

## Security

- Only explicitly registered tools can execute.
- Tool names are validated.
- Tool arguments are validated against Pydantic models.
- Unexpected arguments are rejected when the registered model
  uses extra="forbid".
- Authentication-dependent tools reject requests without a
  trusted application-supplied user identity.
- Tool handlers must be asynchronous.
- Execution is bounded by a timeout.
- Arguments and outputs have size limits.
- Internal exception details are not returned to the caller.
- User-provided documents cannot register or execute tools.

## Execution Model

Tool calls are executed sequentially.

This preserves execution ordering and avoids uncontrolled
parallel side effects.

## Integration Boundaries

Phase 17.5 does not yet:

- Integrate Gemini function calling.
- Register production educational tools.
- Connect tools to external APIs.
- Implement multi-step workflow planning.
- Integrate authenticated user identity.
- Implement production authorization policies.

These capabilities belong to subsequent phases.

## Known Limitations

1. Authentication is deferred to Phase 18.
2. Tool output is size-limited but not yet semantically
   validated for every future tool.
3. Async timeout cancellation depends on handler cooperation.
4. No persistent tool-execution audit table exists.
5. The example academic search handler is a placeholder.
6. Tool execution is sequential, not parallel.

## Verification

Run:

    python -m pytest tests/services/llm_tools/ -v

The test output must be reviewed before declaring this
subphase verified.