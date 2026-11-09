# Phase 17.6 — Structured AI Workflow Engine

## Objective

Implement a structured multi-step workflow engine that
coordinates registered application tools.

## Architecture

- Workflow registry
- Workflow definitions
- Pydantic input validation
- Pydantic step output validation
- Dependency graph validation
- Topological execution ordering
- Restricted reference resolution
- Workflow state machine
- Failure policies
- Execution tracking

## Workflow Execution

A workflow consists of registered steps.

Each step specifies:

- Unique step ID
- Registered tool name
- Argument template
- Expected output schema
- Dependencies

## Reference Resolution

Supported references:

- input.field
- steps.step_id.output.field

Arbitrary Python expressions and function execution
are prohibited.

## Dependency Management

The registry rejects:

- Unknown dependencies
- Duplicate step IDs
- Self-dependencies
- Circular dependencies

The execution engine uses topological ordering.

## Failure Policies

STOP:

Stop executing new independent steps after a failure.
Dependent steps are skipped.

CONTINUE:

Continue executing independent steps.
Dependent steps are skipped if their dependencies fail.

## State Management

Workflow states:

- pending
- running
- succeeded
- failed
- partially_succeeded

Step states:

- pending
- running
- succeeded
- failed
- skipped

## Execution Tracking

Execution records are currently stored in memory.

They are lost when the application restarts.

Persistent execution tracking is deferred to a later
database integration.

## Security

- Only registered workflows execute.
- Only registered tools execute.
- Workflow inputs are schema-validated.
- Tool arguments pass through the Phase 17.5 executor.
- Tool outputs are schema-validated.
- Reference resolution does not evaluate Python.
- Existing Phase 17.5 authorization checks remain active.

## Not Implemented

- Gemini function-calling integration
- LLM-generated workflow planning
- Production educational workflow registration
- Durable workflow execution records
- Workflow resume after application restart
- Human approval workflows
- Parallel step execution
- Authentication implementation

## Verification

Run:

    python -m pytest tests/services/ai_workflows/ -v

Review the actual test output before declaring Phase 17.6
verified.