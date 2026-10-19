# ScholarAI

ScholarAI is an AI-powered academic learning platform designed to help students understand study material, prepare for examinations, and discover relevant educational resources.

## Planned Features

* AI-powered academic study assistant
* PDF question answering with source references
* Document summarization and important-point extraction
* Exam-oriented answer generation
* MCQ generation and mock tests
* Previous-year question paper analysis
* Personalized revision recommendations
* Online educational resource discovery
* Hackathon, competition, workshop, and internship discovery
* Learning history and progress tracking

## Technology Stack

* Python
* FastAPI
* Pydantic
* Pytest
* HTML, CSS, and JavaScript (planned frontend)
* SQL database (planned)
* Large Language Model APIs (planned)
* Retrieval-Augmented Generation (planned)

The technology stack will evolve as the project develops.

## Current Project Status

### Completed foundation

* Python virtual environment
* FastAPI application
* Basic home and health endpoints
* Initial academic chat endpoint
* Request validation using Pydantic
* Modular API, schema, and service structure
* Initial automated API tests
* Backend requirements and API design documentation
* Git version control and GitHub repository

### Current limitations

* The chat endpoint uses a temporary placeholder response.
* LLM integration has not yet been implemented.
* Conversation persistence is not yet implemented.
* Document processing and RAG are not yet implemented.
* Assessment and recommendation engines are not yet implemented.
* Authentication and database integration are not yet implemented.
* Frontend development has not yet begun.

### Test status

The initial automated API test suite contains 10 tests, which passed during the latest local test run.

## Project Structure

```text
ScholarAi/
├── app/
│   ├── api/
│   ├── core/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
├── docs/
├── requirements.txt
├── README.md
└── .gitignore
```

## Running Locally

Activate the project's virtual environment, then install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the development server:

```bash
python -m uvicorn app.main:app --reload
```

Open the following local addresses in your browser:

* Application: `http://127.0.0.1:8000/`
* Health check: `http://127.0.0.1:8000/health`
* Interactive API documentation: `http://127.0.0.1:8000/docs`

Run the automated tests:

```bash
python -m pytest -v
```

## Development Roadmap

ScholarAI is being developed incrementally, with separate phases for frontend development, LLM integration, database design, document intelligence, RAG, recommendation systems, security, evaluation, testing, and deployment.

Features will be marked complete only after their implementation and appropriate verification.
