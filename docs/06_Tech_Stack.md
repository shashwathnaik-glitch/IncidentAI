# Tech Stack

**Project:** IncidentMind\
**Version:** 1.0 (Draft)\
**Status:** 🟡 Draft

------------------------------------------------------------------------

# Purpose

This document defines the proposed technology stack for building,
deploying, and maintaining IncidentMind.

------------------------------------------------------------------------

# Architecture Overview

  Layer             Technology                    Why
  ----------------- ----------------------------- ---------------------------------
  Frontend          Next.js (React)               Modern, fast, SSR support
  Styling           Tailwind CSS                  Rapid UI development
  Backend           FastAPI (Python)              High performance, AI-friendly
  Database          CockroachDB                   Distributed SQL + Vector Search
  AI Models         Amazon Bedrock                Managed foundation models
  Authentication    JWT                           Stateless authentication
  Notifications     Slack API, Email (SES/SMTP)   Enterprise alerts
  Deployment        AWS                           Cloud hosting
  Version Control   Git + GitHub                  Collaboration

------------------------------------------------------------------------

# AI Components

-   LLM via Amazon Bedrock
-   Prompt orchestration
-   Memory retrieval
-   Confidence scoring
-   Similar-incident reasoning

------------------------------------------------------------------------

# CockroachDB Usage

-   Persistent incident memory
-   Vector embeddings
-   Semantic search
-   Transactional data
-   Audit logs

------------------------------------------------------------------------

# AWS Services

  Service          Purpose
  ---------------- --------------------
  Amazon Bedrock   AI reasoning
  EC2/ECS          Backend hosting
  S3               Logs & attachments
  CloudWatch       Monitoring
  IAM              Security

------------------------------------------------------------------------

# Development Tools

-   VS Code
-   Claude (implementation)
-   GitHub
-   Postman
-   Docker
-   Mermaid

------------------------------------------------------------------------

# Coding Principles

-   Modular architecture
-   API-first design
-   Environment variables
-   Secure by default
-   Testable components

------------------------------------------------------------------------

# Future Improvements

-   CI/CD with GitHub Actions
-   Kubernetes deployment
-   Redis caching
-   Multi-model AI routing
