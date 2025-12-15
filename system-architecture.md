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
                SESSIONS[(Sessions Table)]
                CACHE[(Cache Table)]
            end
        end

        subgraph External["External Services"]
            GITHUB[GitHub API]
            GEMINI[Gemini AI]
        end
    end

    UI -->|REST API| APIGW
    APIGW --> L2
    APIGW --> SF
    
    SF --> L1
    SF --> L3
    
    L1 --> GITHUB
    L1 --> GEMINI
    L1 --> CACHE
    
    L2 --> SESSIONS
    L2 --> S3U
    
    L3 --> S3U
    L3 --> S3P
    L3 --> S3O
    
    UI -->|Direct Upload| S3U
    UI -->|Download| S3O