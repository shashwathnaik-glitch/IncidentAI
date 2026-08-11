# API Design

**Project:** IncidentMind\
**Version:** 1.0 (Draft)\
**Status:** 🟡 Draft

------------------------------------------------------------------------

# Purpose

Defines the REST API contract between the frontend, backend, AI agent,
and external services.

------------------------------------------------------------------------

# API Principles

-   RESTful endpoints
-   JSON request/response
-   JWT authentication
-   Role-Based Access Control (RBAC)
-   Versioned APIs (`/api/v1`)

------------------------------------------------------------------------

# Authentication

## POST /api/v1/auth/login

Authenticate Employee or Admin.

### Request

``` json
{
  "email": "user@company.com",
  "password": "********"
}
```

### Response

``` json
{
  "access_token": "...",
  "role": "employee"
}
```

------------------------------------------------------------------------

# Incidents

## POST /api/v1/incidents

Create a new incident.

## GET /api/v1/incidents/{id}

Get incident details.

## GET /api/v1/incidents

List incidents with filters.

------------------------------------------------------------------------

# AI

## POST /api/v1/ai/analyze

Analyze a new incident.

Returns: - Similar incidents - Confidence score - Suggested resolution -
Reasoning summary

## POST /api/v1/ai/approve

Approve AI-recommended action.

------------------------------------------------------------------------

# Memory

## GET /api/v1/memory/search

Semantic search across previous incidents.

Query Parameters: - category - severity - limit

------------------------------------------------------------------------

# Notifications

## POST /api/v1/notifications/send

Trigger Email or Slack notification.

------------------------------------------------------------------------

# Admin

## GET /api/v1/admin/dashboard

Returns: - Active incidents - Incident trends - AI usage - Reward
leaderboard

## GET /api/v1/admin/users

List users.

------------------------------------------------------------------------

# Response Codes

  Code   Meaning
  ------ -----------------------
  200    Success
  201    Created
  400    Bad Request
  401    Unauthorized
  403    Forbidden
  404    Not Found
  500    Internal Server Error

------------------------------------------------------------------------

# API Flow

``` mermaid
sequenceDiagram
participant FE as Frontend
participant API as Backend
participant AI as AI Agent
participant DB as CockroachDB

FE->>API: Create Incident
API->>AI: Analyze
AI->>DB: Search Memory
DB-->>AI: Similar Incidents
AI-->>API: Recommendation
API-->>FE: JSON Response
```

------------------------------------------------------------------------

# Security

-   JWT on protected endpoints
-   Input validation
-   Rate limiting
-   Audit logging
-   HTTPS only

------------------------------------------------------------------------

# Future Endpoints

-   WebSocket live incident updates
-   Batch incident import
-   AI feedback endpoint
-   Team management
