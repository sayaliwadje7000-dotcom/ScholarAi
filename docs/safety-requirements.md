# ScholarAI Safety and Guardrails

## Purpose

This document defines the initial safety architecture
implemented in ScholarAI.

## 1. Academic Scope

ScholarAI prioritizes academic and educational requests.

## 2. Prompt Injection Protection

Known direct prompt-injection patterns are screened
before requests reach the language model.

## 3. System Instruction Protection

The system prompt instructs the model not to disclose
governing instructions or confidential configuration.

## 4. Citation Integrity

The model is instructed not to fabricate papers,
authors, publication dates, URLs or DOI identifiers.

Citation verification requires a trusted retrieval
and source-validation system.

## 5. Privacy Protection

Generated responses are checked for selected sensitive
credential patterns before being returned.

## 6. Unsafe Requests

Selected clearly harmful requests are blocked using
deterministic input patterns.

## 7. Output Validation

Generated responses are inspected for selected
sensitive credential patterns.

## 8. Evaluation

Safety behaviour is evaluated through:

- Unit tests
- Integration tests
- Adversarial input tests
- Existing API regression tests
- Existing academic reliability tests

## 9. Limitations

The current implementation does not guarantee complete
protection against:

- Semantic prompt injection
- Encoded attacks
- Multi-turn manipulation
- Novel harmful requests
- All possible credential formats
- Fabricated citations that resemble valid references

It does not independently verify research citations
because the current chat pipeline has no trusted
citation retrieval and verification component.

## 10. Future Improvements

- Semantic prompt-injection detection
- Trusted source retrieval
- Citation verification
- Structured output validation
- Rate limiting
- Abuse monitoring
- Security event logging
- Dedicated adversarial evaluation
