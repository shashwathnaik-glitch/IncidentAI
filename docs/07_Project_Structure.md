# Project Structure

**Project:** IncidentMind\
**Version:** 1.0 (Draft)\
**Status:** 🟡 Draft

------------------------------------------------------------------------

# Purpose

Define the repository layout so every team member follows the same
structure during development.

------------------------------------------------------------------------

# Repository Layout

``` text
incidentmind/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── styles/
│   └── public/
│
├── backend/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── agents/
│   ├── memory/
│   ├── db/
│   ├── migrations/
│   └── tests/
│
├── docs/
├── scripts/
├── docker/
├── .github/
├── .env.example
├── docker-compose.yml
└── README.md
```

------------------------------------------------------------------------

# Frontend Structure

-   `app/` -- Next.js routes
-   `components/` -- Reusable UI
-   `services/` -- API calls
-   `hooks/` -- Custom React hooks
-   `lib/` -- Utilities
-   `styles/` -- Global styling

------------------------------------------------------------------------

# Backend Structure

-   `api/` -- REST endpoints
-   `agents/` -- AI agent logic
-   `memory/` -- Retrieval and memory management
-   `services/` -- Business logic
-   `models/` -- ORM/database models
-   `schemas/` -- Request/response models
-   `db/` -- Database connection
-   `migrations/` -- Schema migrations
-   `tests/` -- Unit/integration tests

------------------------------------------------------------------------

# Documentation

``` text
docs/
├── research/
├── product/
├── architecture/
├── ui/
├── development/
├── deployment/
└── submission/
```

------------------------------------------------------------------------

# Naming Conventions

-   Files: `snake_case`
-   React Components: `PascalCase`
-   API Routes: `kebab-case`
-   Environment Variables: `UPPER_CASE`

------------------------------------------------------------------------

# Configuration Files

-   `.env`
-   `.env.example`
-   `docker-compose.yml`
-   `pyproject.toml`
-   `package.json`

------------------------------------------------------------------------

# Branch Strategy

-   `main`
-   `develop`
-   `feature/frontend`
-   `feature/backend`
-   `feature/ai`
-   `feature/database`

------------------------------------------------------------------------

# Future Improvements

-   Monorepo tooling
-   GitHub Actions
-   Infrastructure as Code
-   Automated documentation generation
