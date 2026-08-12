# AWS Infrastructure & Deployment Guide — IncidentMind

This document details the target cloud architecture, security setups, IAM policies, and deployment steps for launching the IncidentMind persistent memory storage (CockroachDB) and backend service on AWS.

## Architecture Overview

For a resilient, secure, and cost-efficient hackathon MVP, the system uses a serverless and containerized architecture on AWS:

```
[ ECS Fargate (Backend API) ] 
       │
       ├─► [ Amazon Bedrock (Titan Embeddings V2) ] ── (AI model interface)
       │
       ├─► [ CockroachDB Serverless ] ───────────────── (Persistent outcome-aware memory)
       │
       └─► [ AWS Secrets Manager ] ──────────────────── (Credentials, SSL certs, connection strings)
```

---

## 1. Database Provisioning (CockroachDB Serverless)

We leverage CockroachDB Serverless to host our PostgreSQL-compatible distributed SQL database, which natively supports pgvector and vector indexes.

### Steps to Set Up:
1. Create a CockroachDB Cloud account.
2. Spin up a new cluster:
   * **Tier:** Serverless (free tier is sufficient for MVP).
   * **Cloud Provider:** AWS (same region as ECS, e.g., `us-east-1`, to minimize latency).
   * **Name:** `incidentmind-cluster`.
3. Create database credentials:
   * SQL user: `incidentmind_app`.
   * Save the password securely (do not commit to Git).
4. Download the CockroachDB CA root certificate for SSL verification. The certificate will be injected into the ECS containers.

---

## 2. Environment Variables & AWS Secrets Manager

To comply with database security practices, all credentials must be stored in **AWS Secrets Manager** and injected into ECS task definitions at runtime.

### Secret Key: `prod/incidentmind/db`
Create a secret containing:
* `DB_HOST`: `<your-cockroach-serverless-host>`
* `DB_PORT`: `26257`
* `DB_NAME`: `defaultdb`
* `DB_USER`: `incidentmind_app`
* `DB_PASSWORD`: `<your-secret-password>`
* `DB_SSLMODE`: `verify-full`

---

## 3. IAM Policies & Security Permissions

To securely run the containerized backend and allow it to read parameters, retrieve secret values, and invoke Bedrock, we must configure two IAM Roles:

### A. ECS Task Execution Role (`ecsTaskExecutionRole`)
This role is used by the ECS agent to pull images and fetch Secrets Manager secrets.
* **AWS Managed Policy:** `AmazonECSTaskExecutionRolePolicy`
* **Custom Inline Policy for Secrets Manager:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/incidentmind/db-*"
      ]
    }
  ]
}
```

### B. ECS Task Role (`ecsTaskRole`)
This role is assumed by the backend container code at runtime. It grants permissions to invoke Bedrock.
* **Bedrock Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
      ]
    }
  ]
}
```

---

## 4. ECS Fargate Container Deployment

### Task Definition Configuration
* **Compatibilities:** Fargate
* **CPU:** `0.5 vCPU`, **Memory:** `1.0 GB`
* **Task Role:** `ecsTaskRole`
* **Task Execution Role:** `ecsTaskExecutionRole`
* **Log Configuration:** AWS FireLens or CloudWatch Logs (`awslogs`)

### Container Definitions (Backend)
Configure the backend container to pull environment configurations from the Secrets Manager secret:

```json
{
  "name": "backend",
  "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/incidentmind-backend:latest",
  "portMappings": [
    {
      "containerPort": 8000,
      "hostPort": 8000,
      "protocol": "tcp"
    }
  ],
  "secrets": [
    { "name": "DB_HOST", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/incidentmind/db:DB_HOST::" },
    { "name": "DB_PORT", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/incidentmind/db:DB_PORT::" },
    { "name": "DB_NAME", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/incidentmind/db:DB_NAME::" },
    { "name": "DB_USER", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/incidentmind/db:DB_USER::" },
    { "name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/incidentmind/db:DB_PASSWORD::" },
    { "name": "DB_SSLMODE", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/incidentmind/db:DB_SSLMODE::" }
  ],
  "environment": [
    { "name": "EMBEDDING_DIMENSION", "value": "1024" }
  ],
  "healthCheck": {
    "command": ["CMD-SHELL", "python scripts/health_check.py || exit 1"],
    "interval": 30,
    "timeout": 5,
    "retries": 3,
    "startPeriod": 15
  }
}
```

---

## 5. Network Security & Routing

* **VPC Setup:** Deploy ECS Fargate tasks inside **Private Subnets**.
* **NAT Gateway:** Required in public subnets to allow Fargate instances to connect out to Amazon Bedrock and CockroachDB Serverless.
* **Security Group Rules (ECS Fargate):**
  * **Inbound:** Allow port `8000` (HTTP) from the Application Load Balancer (ALB) security group.
  * **Outbound:** Allow port `443` (HTTPS) to connection domains, and port `26257` to CockroachDB Cloud server.
* **Application Load Balancer (ALB):**
  * Place in **Public Subnets**.
  * Forward HTTP/HTTPS (ports 80/443) traffic to target group containing ECS Fargate container instances.
