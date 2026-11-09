# Phase 17.4 – Conversation Context Management

## Objective

Implement bounded, ownership-aware conversation history retrieval
for ScholarAI's advanced LLM workflows.

## Existing Architecture

The implementation reuses:

- Conversation ORM model
- Message ORM model
- Existing conversation database relationships
- Existing message role and token_count fields

No duplicate database tables are introduced.

## Implemented Components

### 1. Context Configuration

File:

app/core/conversation_context_config.py

Defines:

- Maximum history messages
- Maximum context token budget
- Maximum individual message length
- Estimated characters per token

### 2. Context Schemas

File:

app/schemas/conversation_context.py

Defines validated context messages and context results.

### 3. Context Management Service

File:

app/services/conversation_context_service.py

Responsibilities:

- Validate conversation and user UUIDs.
- Verify conversation ownership.
- Exclude archived conversations.
- Retrieve user and assistant messages.
- Exclude stored system messages.
- Preserve chronological order.
- Apply message-count limits.
- Apply context token budgets.
- Return structured context metadata.

### 4. Token Budgeting

Token estimation currently uses a configurable
character-to-token approximation.

This is not an exact Gemini tokenizer.

Provider-reported token counting can be introduced
in a later LLM optimization stage.

## Security

Conversation retrieval requires both:

- conversation_id
- user_id

A conversation cannot be retrieved merely by knowing
its identifier.

Authentication integration remains scheduled for Phase 18.

## Integration Boundary

The current unauthenticated chat endpoint does not
provide a trusted user identity.

Therefore, this service is not yet connected to the
public chat endpoint.

Phase 18 will provide the authenticated identity
required for secure chat-history integration.

## Database

No migration required.

Existing Conversation and Message models are reused.

## Tests

Focused tests cover:

- Token estimation
- Context construction
- Chronological ordering
- System message exclusion
- Context budget enforcement
- Recent-message prioritization
- Excluded-message reporting
- Invalid input handling
- Empty context handling

## Known Limitations

1. Token counts are approximate.
2. No semantic summarization of old messages.
3. No automatic conversation summarization.
4. No authenticated chat endpoint integration yet.
5. No provider-specific token counting yet.
6. No persistent summary storage.

These can be addressed in subsequent phases.