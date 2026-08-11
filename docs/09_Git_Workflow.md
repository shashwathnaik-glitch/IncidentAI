# Git Workflow

**Project:** IncidentMind\
**Version:** 1.0 (Draft)\
**Status:** 🟡 Draft

------------------------------------------------------------------------

# Purpose

Define how the team collaborates using Git and GitHub to avoid conflicts
and keep development organized.

------------------------------------------------------------------------

# Branch Strategy

``` text
main
│
├── develop
│   ├── feature/frontend
│   ├── feature/backend
│   ├── feature/ai-memory
│   └── feature/database-aws
```

-   **main** -- Production-ready code
-   **develop** -- Integration branch
-   **feature/**\* -- Individual work branches

------------------------------------------------------------------------

# Commit Message Convention

Format:

``` text
type(scope): short description
```

Examples:

``` text
feat(auth): add employee login
fix(api): handle invalid incident ID
docs(prd): update user stories
refactor(memory): simplify retrieval logic
```

Common types: - feat - fix - docs - refactor - test - chore

------------------------------------------------------------------------

# Pull Request Process

1.  Sync with `develop`
2.  Push feature branch
3.  Open Pull Request
4.  Request review
5.  Resolve comments
6.  Merge into `develop`

------------------------------------------------------------------------

# Merge Rules

-   No direct commits to `main`
-   Every PR must build successfully
-   Resolve merge conflicts before review
-   Keep PRs focused on one feature

------------------------------------------------------------------------

# Code Review Checklist

-   Feature works as expected
-   Tests pass
-   Documentation updated
-   No sensitive data committed
-   Follows coding standards

------------------------------------------------------------------------

# Release Flow

``` mermaid
flowchart LR
A[Feature Branch]
-->B[Develop]
-->C[Testing]
-->D[Main]
```

------------------------------------------------------------------------

# Git Ignore

Ignore: - `.env` - Virtual environments - Build artifacts - IDE
settings - Logs

------------------------------------------------------------------------

# Recommended Tools

-   GitHub
-   GitHub Issues
-   GitHub Projects
-   Pull Requests
-   Branch Protection Rules

------------------------------------------------------------------------

# Future Improvements

-   GitHub Actions CI
-   Automatic deployments
-   Semantic versioning
-   Release notes generation
