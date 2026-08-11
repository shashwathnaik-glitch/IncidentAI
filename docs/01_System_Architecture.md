# System Architecture

**Project:** IncidentMind\
**Version:** 1.0 (Draft)\
**Status:** 🟡 Draft

------------------------------------------------------------------------

# Purpose

This document defines the high-level architecture of IncidentMind and
how each major component interacts.

------------------------------------------------------------------------

# High-Level Architecture

``` mermaid
flowchart LR
U[Employee/Admin]
--> FE[Frontend]
--> API[Backend API]
--> AGENT[AI Agent]
AGENT --> CRDB[CockroachDB Memory]
AGENT --> BEDROCK[Amazon Bedrock]
API --> NOTIFY[Email / Slack]
API --> CRDB
```

------------------------------------------------------------------------

# Core Components

  Component              Responsibility
  ---------------------- -------------------------------------------------------
  Frontend               User interface, dashboards, authentication
  Backend API            Business logic, security, orchestration
  AI Agent               Incident reasoning, memory retrieval, recommendations
  CockroachDB            Persistent memory, incident history, vectors
  Amazon Bedrock         LLM reasoning and embeddings
  Notification Service   Email and Slack alerts

------------------------------------------------------------------------

# Request Lifecycle

``` mermaid
sequenceDiagram
participant User
participant Frontend
participant Backend
participant Agent
participant CockroachDB

User->>Frontend: Report Incident
Frontend->>Backend: Submit Incident
Backend->>Agent: Analyze
Agent->>CockroachDB: Search Similar Incidents
CockroachDB-->>Agent: Matches
Agent-->>Backend: Recommendation
Backend-->>Frontend: Show Result
Backend->>CockroachDB: Save Outcome
```

------------------------------------------------------------------------

# Authentication Flow

1.  User logs in.
2.  Backend validates credentials.
3.  JWT token issued.
4.  Role determines dashboard.
5.  Protected APIs require valid token.

------------------------------------------------------------------------

# Incident Processing Flow

1.  Incident submitted.
2.  AI extracts context.
3.  Embedding generated.
4.  Vector search executed.
5.  Similar incidents ranked.
6.  AI recommends fix.
7.  User approves if required.
8.  Outcome stored as memory.

------------------------------------------------------------------------

# Security Boundaries

-   JWT Authentication
-   Role-Based Access Control (RBAC)
-   Audit logging
-   Approval required for risky actions
-   Encrypted secrets and environment variables

------------------------------------------------------------------------

# External Integrations

-   CockroachDB Cloud
-   Amazon Bedrock
-   Slack API
-   Email Provider (SMTP/SES)

------------------------------------------------------------------------

# Deployment View

``` mermaid
flowchart TB
Browser --> Frontend
Frontend --> Backend
Backend --> Bedrock
Backend --> CockroachDB
Backend --> Slack
Backend --> Email
```

------------------------------------------------------------------------

# Scalability Goals

-   Stateless backend
-   Independent AI service
-   Horizontally scalable frontend
-   Managed CockroachDB cluster
-   Cloud-native deployment on AWS

------------------------------------------------------------------------

# Open Design Decisions

-   Background job queue for long-running tasks
-   Choice of email provider
-   Automatic remediation safeguards
