# ScholarAI — API Design

## 1. Purpose

This document describes the API structure of ScholarAI, an AI-powered academic learning platform.

The backend uses FastAPI and is being developed incrementally. This document distinguishes currently implemented endpoints from planned endpoints.

**Important:** An endpoint listed as planned is a design specification, not a working feature.

## 2. API Conventions

* API prefix for versioned endpoints: `/api/v1`
* Data format: JSON, except where file uploads or other content types are required.
* GET: Retrieve resources.
* POST: Create resources or initiate operations.
* PUT: Replace a resource.
* PATCH: Partially update a resource.
* DELETE: Delete a resource.
* Validate incoming requests.
* Return appropriate HTTP status codes and structured error responses.
* Add authentication and authorization where required.
* Document request and response schemas.

## 3. Implemented Endpoints

The following endpoints currently exist in the backend.

| Method | Endpoint       | Purpose                                           | Current Status                                   |
| ------ | -------------- | ------------------------------------------------- | ------------------------------------------------ |
| GET    | `/`            | Return application information and status         | Implemented                                      |
| GET    | `/health`      | Check application health                          | Implemented                                      |
| POST   | `/api/v1/chat` | Accept an academic question and return a response | Implemented with a temporary placeholder service |

### Current Chat Limitations

The chat endpoint currently validates the request and returns a temporary response.

It does not yet use a Large Language Model (LLM) to generate genuine AI-powered academic answers. LLM integration is planned for Phase 5.

Conversation history is not yet stored in a database.

## 4. Planned API Endpoints

The following endpoints describe future functionality. They are **not implemented yet**.

### 4.1 Academic Chat and Conversations

| Method | Endpoint                                  | Purpose                          |
| ------ | ----------------------------------------- | -------------------------------- |
| GET    | `/api/v1/conversations`                   | Retrieve conversation history    |
| GET    | `/api/v1/conversations/{conversation_id}` | Retrieve a specific conversation |
| DELETE | `/api/v1/conversations/{conversation_id}` | Delete a conversation            |

### 4.2 Documents

| Method | Endpoint                                    | Purpose                                          |
| ------ | ------------------------------------------- | ------------------------------------------------ |
| POST   | `/api/v1/documents`                         | Upload a document                                |
| GET    | `/api/v1/documents`                         | List the user's documents                        |
| GET    | `/api/v1/documents/{document_id}`           | Retrieve document metadata and processing status |
| DELETE | `/api/v1/documents/{document_id}`           | Delete a document                                |
| POST   | `/api/v1/documents/{document_id}/questions` | Ask a question about a document                  |
| POST   | `/api/v1/documents/{document_id}/summary`   | Generate a document summary                      |

### 4.3 Assessments

| Method | Endpoint                                          | Purpose                                      |
| ------ | ------------------------------------------------- | -------------------------------------------- |
| POST   | `/api/v1/assessments/generate`                    | Generate practice questions or an assessment |
| GET    | `/api/v1/assessments/{assessment_id}`             | Retrieve an assessment                       |
| POST   | `/api/v1/assessments/{assessment_id}/submissions` | Submit answers and evaluate a submission     |

### 4.4 Recommendations

| Method | Endpoint                  | Purpose                                    |
| ------ | ------------------------- | ------------------------------------------ |
| POST   | `/api/v1/recommendations` | Generate a unified list of recommendations |

The planned recommendation system will evolve through rule-based filtering, content-based relevance, and machine-learning-based ranking.

### 4.5 Educational Resource Discovery

| Method | Endpoint                   | Purpose                          |
| ------ | -------------------------- | -------------------------------- |
| GET    | `/api/v1/resources/search` | Search for educational resources |

### 4.6 Opportunity Discovery

| Method | Endpoint                       | Purpose                                      |
| ------ | ------------------------------ | -------------------------------------------- |
| GET    | `/api/v1/opportunities/search` | Search for relevant events and opportunities |

### 4.7 Learning and Personalization

| Method | Endpoint                           | Purpose                                        |
| ------ | ---------------------------------- | ---------------------------------------------- |
| GET    | `/api/v1/learning/profile`         | Retrieve the user's learning profile           |
| GET    | `/api/v1/learning/progress`        | Retrieve learning progress                     |
| GET    | `/api/v1/learning/recommendations` | Retrieve personalized learning recommendations |

These endpoints will be designed and implemented when their supporting features are developed.

## 5. Example Chat Request

**Endpoint:** `POST /api/v1/chat`

### Request

```json
{
  "message": "Explain machine learning in simple terms.",
  "conversation_id": null
}
```

### Illustrative Response

```json
{
  "answer": "ScholarAI received your question: Explain machine learning in simple terms.\n\nAI-powered academic responses will be available after LLM integration.",
  "conversation_id": null,
  "status": "success"
}
```

This response illustrates the current placeholder implementation. It is not an AI-generated academic answer.

The request validates the message and accepts an optional conversation ID. Persistent conversation management has not yet been implemented.

## 6. Planned Recommendation Architecture

The planned recommendation workflow is:

1. Receive the student's query and preferences.
2. Retrieve candidate resources.
3. Apply relevant rules and constraints.
4. Calculate content-based relevance.
5. Rank suitable candidates using a machine-learning model when available.
6. Validate the results.
7. Return recommendations with source information and explanations where possible.

The exact workflow will be refined during implementation and evaluation.

## 7. Error Handling

The backend should handle errors such as:

* Invalid request data.
* Missing resources.
* Unauthorized access.
* Rate-limit violations.
* External service failures.
* Internal server errors.

The current chat request uses Pydantic validation and FastAPI's default structured validation-error responses.

More comprehensive error handling will be added as the application grows. Error responses must not expose secrets or sensitive internal details.

## 8. Versioning and Compatibility

The `/api/v1` prefix identifies the first version of the planned versioned API.

Changes to request and response schemas should be managed carefully to avoid breaking existing clients.

## 9. Implementation Status

ScholarAI is being developed incrementally according to its 22-phase roadmap.

Currently implemented:

* Basic application endpoint.
* Health-check endpoint.
* Initial chat endpoint.
* Chat request validation.
* Initial automated API tests.

Still planned:

* LLM integration.
* Conversation persistence.
* Document processing and question answering.
* Assessments.
* Recommendation engines.
* Educational resource and opportunity discovery.
* Learning progress and personalization.
* Authentication and security.

**Implementation rule:** An endpoint or feature should only be marked implemented after its functionality has been developed and appropriately tested.

