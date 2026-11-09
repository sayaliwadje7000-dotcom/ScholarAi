# Phase 17.7 — Educational Tool Orchestration

## Objective

Integrate ScholarAI's existing educational-resource
discovery capabilities with the Phase 17.5 tool-calling
architecture and Phase 17.6 workflow engine.

## Existing Integrations Reused

- YouTubeProvider
- OpenAlexProvider
- CrossrefProvider
- GoogleBooksProvider
- BaseResourceProvider
- ResourceProviderRegistry
- ResourceDiscoveryService

## Implemented Components

### Educational Resource Search Tool

Registered tool:

    educational_resource_search

The tool delegates discovery to the existing
ResourceDiscoveryService.

It supports:

- Query
- Provider selection
- Resource type
- Subject
- Language
- Result limit per provider

### Educational Workflow

Registered workflow:

    educational_resource_discovery

The workflow:

1. Validates the student request.
2. Resolves workflow input references.
3. Invokes the educational resource search tool.
4. Validates the standardized discovery response.
5. Returns structured educational resources.

## Architecture

Phase 17.5:
- Tool registry
- Tool execution
- Argument validation
- Authorization checks
- Execution timeouts

Phase 17.6:
- Workflow registry
- Workflow execution
- Input/output validation
- Dependency management
- Failure policies

Phase 17.7:
- Educational resource tool
- Discovery service adapter
- Educational workflow registration

## Security

- Tool execution uses the allowlisted registry.
- Tool arguments use Pydantic validation.
- Existing provider configuration is reused.
- External resource metadata is treated as untrusted data.
- Tool execution limits remain enforced by Phase 17.5.

## Deferred

- PDF retrieval orchestration
- RAG question-answering tool
- Recommendation-engine orchestration
- Gemini autonomous tool selection
- Multi-step LLM planning
- Authentication-dependent student workflows

These require verified interfaces and subsequent integration.

## Persistence

No database migration is introduced.

Workflow execution tracking remains in memory through
the Phase 17.6 engine.

## Verification

Run:

    python -m pytest tests/services/educational_tools/ -v

Then run:

    python -m pytest tests/services/educational_tools/ tests/services/ai_workflows/ tests/services/llm_tools/ -v