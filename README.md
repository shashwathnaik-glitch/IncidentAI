# IncidentMind

> **AI-Powered IT Incident Management & Resolution Assistant**

IncidentMind is an AI-powered IT incident management platform designed
to function as a digital resolution assistant. The system retains a
persistent memory of past incidents --- including successful, failed,
and partial resolutions --- and uses vector-based retrieval to surface
relevant historical context when new incidents are reported, reducing
time to resolution.

## Overview

Traditional incident management systems log incidents but do not learn
from them. IncidentMind addresses this by combining structured incident
intake with a vector memory layer, allowing the system to recall similar
past incidents and their outcomes, and to provide AI-generated
resolution recommendations grounded in that history.

## Core Capabilities

### Persistent Memory

A vector-based memory store, backed by CockroachDB, records the outcome
of every resolved incident and retrieves semantically similar past cases
when a new incident is reported.

### Incident Reporting

Structured intake capturing system category, severity level, detailed
description, and optional logs or stack traces to improve retrieval
accuracy.

### AI-Assisted Resolution

Incoming incidents are analyzed against historical memory using Amazon
Bedrock to generate resolution recommendations.

### Authentication and Access Control

A login system supports distinct experiences for standard users
(incident resolution workspace) and administrators (operational
dashboard).

### Administrative Dashboard

Provides operational metrics and user management for system
administrators.

## Architecture

### System Flow

``` text
Incident Report
      │
      ▼
React Frontend
      │
      ▼
FastAPI Backend
      │
      ├──────────────► Amazon Bedrock
      │                    │
      │                    ▼
      │              Resolution Recommendation
      │
      ▼
CockroachDB
(Vector Memory + Incident History)
      │
      ▼
Relevant Historical Context
```

  Layer            Technology
  ---------------- ----------------------------------
  Frontend         React (Vite), Tailwind CSS
  Backend          Python, FastAPI
  AI / Inference   Amazon Bedrock
  Data Store       CockroachDB (with vector search)
  Infrastructure   AWS EC2, Docker

## Repository Structure

    IncidentAI/
    ├── backend/             # FastAPI backend: API routes, agents, memory layer, services
    ├── frontend/            # React (Vite) frontend application
    ├── docker/              # Docker configuration files
    ├── docker-compose.yml   # CockroachDB service definition
    ├── docs/                # Supplementary documentation
    └── scripts/             # Utility and operational scripts

## Getting Started

### Prerequisites

-   Python 3.11 or later
-   Node.js 18 or later
-   Docker and Docker Compose

### 1. Provision the Database

``` bash
docker-compose up -d
```

This starts a single-node CockroachDB instance, exposing port `26257`
for SQL connections and port `8081` for the database admin console.

### 2. Backend Setup

``` bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
```

The backend must be started from the project root, as its modules are
imported using absolute package paths:

``` bash
cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Interactive API documentation is served at `http://localhost:8000/docs`.

### 3. Frontend Setup

``` bash
cd frontend
npm install
npm run build
npx serve -s dist -l 3000
```

The application is served at `http://localhost:3000`.

By default, the frontend issues API requests to the relative path
`/api/v1`, which is suitable when the frontend and backend are served
behind a common reverse proxy. For standalone deployments, update the
`API_BASE_URL` constant in `frontend/src/services/*.js` to reference the
backend's public address.

## API Reference

  ---------------------------------------------------------------------------
  Method                  Endpoint                    Description
  ----------------------- --------------------------- -----------------------
  POST                    `/api/v1/auth/login`        Authenticate a user

  GET                     `/api/v1/auth/me`           Retrieve the current
                                                      user's profile

  GET                     `/api/v1/memory/search`     Query the vector memory
                                                      store

  POST                    `/api/v1/incidents`         Create a new incident

  GET                     `/api/v1/incidents`         List reported incidents

  POST                    `/api/v1/ai/analyze`        Generate an AI
                                                      resolution
                                                      recommendation for an
                                                      incident

  GET                     `/api/v1/admin/dashboard`   Retrieve administrative
                                                      metrics

  GET                     `/api/v1/admin/users`       List registered users
                                                      (administrator access)
  ---------------------------------------------------------------------------

The full, interactive API specification is available via Swagger UI at
`/docs`.

## Team

This project was developed by a four-person team, with responsibilities
divided as follows:

-   Frontend and User Experience
-   Backend and Application Services
-   AI and Intelligence Systems
-   Database and Cloud Infrastructure

## License

This project is licensed under the terms specified in
[LICENSE](./LICENSE).
