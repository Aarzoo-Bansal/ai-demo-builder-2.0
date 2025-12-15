# 🎬 AI Demo Builder

> Automatically generate professional demo videos for GitHub repositories using AI

[![AWS](https://img.shields.io/badge/AWS-Serverless-orange?logo=amazon-aws)](https://aws.amazon.com/)
[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)](https://www.typescriptlang.org/)

## 🌟 Overview

AI Demo Builder analyzes your GitHub repository and generates intelligent suggestions for demo videos. Upload your screen recordings, and the system automatically stitches them into a professional demo video.

### Key Features

- 🤖 **AI-Powered Analysis** - Uses Gemini AI to understand your project
- 📹 **Smart Video Processing** - Validates, converts, and stitches videos
- ⚡ **Serverless Architecture** - Scales automatically, pay-per-use
- 🔄 **Real-time Updates** - Polling-based progress tracking

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React + Vite)"]
        UI[Web Application]
    end

    subgraph AWS["AWS Cloud"]
        subgraph API["API Layer"]
            APIGW[API Gateway]
        end

        subgraph Compute["Compute Layer"]
            SF[Step Functions]
            L1[Analysis Service]
            L2[Session Service]
            L3[Video Service]
        end

        subgraph Storage["Storage Layer"]
            subgraph S3["S3 Buckets"]
                S3U[(Uploads)]
                S3P[(Processing)]
                S3O[(Output)]
            end
            subgraph DDB["DynamoDB"]
                SESSIONS[(Sessions)]
                CACHE[(Cache)]
            end
        end
    end

    UI -->|REST API| APIGW
    APIGW --> SF
    SF --> L1
    SF --> L3
    L2 --> SESSIONS
    L3 --> S3O
    UI -->|Direct Upload| S3U
```

---

## 📊 User Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as API Gateway
    participant SF as Step Functions
    participant S3 as S3

    U->>F: Enter GitHub URL
    F->>API: POST /analyze
    API->>SF: Start Workflow
    SF-->>F: session_id + suggestions
    
    U->>F: Upload Video Clips
    F->>S3: Direct Upload
    
    U->>F: Click Generate
    F->>API: POST /generate
    
    loop Every 2 seconds
        F->>API: GET /status
        API-->>F: Progress Update
    end
    
    API-->>F: Complete!
    F-->>U: Download Video
```

---

## 🔧 Microservices

```mermaid
flowchart LR
    subgraph Services["3 Microservices"]
        AS["Analysis Service<br/>GitHub + Gemini"]
        SS["Session Service<br/>State Management"]
        VS["Video Service<br/>FFmpeg Processing"]
    end

    AS --> SS
    SS --> VS
```

| Service | Responsibility | Key Tech |
|---------|---------------|----------|
| **Analysis Service** | Fetch GitHub repo, call Gemini AI | Python, GitHub API, Gemini |
| **Session Service** | Manage sessions, presigned URLs | Python, DynamoDB |
| **Video Service** | Validate, convert, stitch videos | Python, FFmpeg |

---

## 💾 Data Storage

### DynamoDB Tables

| Table | Partition Key | Sort Key | Purpose |
|-------|--------------|----------|---------|
| `sessions` | session_id | - | Track user sessions |
| `cache` | repo_url | commit_sha | Cache GitHub analysis |

### S3 Buckets

| Bucket | Lifecycle | Purpose |
|--------|-----------|---------|
| `uploads` | 7 days | Raw user video clips |
| `processing` | 1 day | Temporary processing files |
| `output` | 30 days | Final demo videos |

---

## 🔄 Caching Strategy

```mermaid
flowchart TD
    A[GitHub URL] --> B{Cache Check}
    B -->|HIT| C[Return Cached<br/>100ms]
    B -->|MISS| D[Full Analysis<br/>8-10 seconds]
    D --> E[Save to Cache]
    
    style C fill:#90EE90,stroke:#333,stroke-width:2px
    style D fill:#FFB6C1,stroke:#333,stroke-width:2px
```

**Cache Key:** `repo_url + commit_sha`
- Same repo + same commit = Cache HIT
- Same repo + new commit = Cache MISS (re-analyze)

---

## 🚀 Getting Started

### Prerequisites

- AWS Account with CLI configured
- Node.js 18+
- Python 3.11+
- GitHub Personal Access Token
- Gemini API Key

### Deployment

```bash
# Clone repository
git clone https://github.com/yourusername/ai-demo-builder.git
cd ai-demo-builder

# Deploy infrastructure
cd infrastructure
npm install
cdk deploy --all

# Start frontend
cd ../frontend
npm install
npm run dev
```

---

## 📁 Project Structure

```
ai-demo-builder/
├── infrastructure/          # CDK (TypeScript)
│   └── lib/stacks/
│       ├── storage-stack.ts
│       ├── compute-stack.ts
│       └── api-stack.ts
├── services/                # Lambda (Python)
│   ├── analysis-service/
│   ├── session-service/
│   └── video-service/
├── frontend/                # React + Vite
│   └── src/
└── docs/                    # Documentation
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React, Vite, Tailwind CSS, TypeScript |
| **API** | AWS API Gateway |
| **Compute** | AWS Lambda, Step Functions |
| **Storage** | S3, DynamoDB |
| **AI** | Google Gemini |
| **Video** | FFmpeg |
| **IaC** | AWS CDK (TypeScript) |

---

## 📈 Cost Estimate

Running on AWS Free Tier:

| Service | Free Tier | Estimated Cost |
|---------|-----------|----------------|
| Lambda | 1M requests/month | $0 |
| S3 | 5GB storage | $0 |
| DynamoDB | 25GB storage | $0 |
| API Gateway | 1M calls/month | $0 |
| **Total** | | **~$1/month** |

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## Acknowledgments
- Powered by AWS Serverless
- AI suggestions by Google Gemini