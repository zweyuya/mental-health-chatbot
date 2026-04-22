# Mental Health Chatbot — Automated ML Pipeline

An end-to-end serverless mental health support chatbot built on AWS with a fully automated MLOps pipeline. The system detects user emotions using DistilBERT, generates empathetic responses using T5, and automatically redeploys when new conversation data is collected.

---

## 🌐 Live Demo & Datasets

### 💬 Try the Chatbot
> **[🚀 Open Chatbot](https://mental-health-chatbot-frontend.s3.us-east-1.amazonaws.com/index.html)**
>

### 📊 Datasets Used

| Dataset | Description | Link |
|---|---|---|
| EmpatheticDialogues | 25K empathetic conversations (Meta AI) — used to train T5 response generator | [🔗 HuggingFace](https://huggingface.co/datasets/empathetic_dialogues) |
| dair-ai/emotion | 20K labelled emotion sentences — used to fine-tune DistilBERT classifier | [🔗 HuggingFace](https://huggingface.co/datasets/dair-ai/emotion) |

### 📓 Training Notebooks

| Notebook | Description | Link |
|---|---|---|
| `emotion_distilbert.ipynb` | DistilBERT fine-tuning for 4-class emotion classification | [🔗 View Notebook](../../blob/main/emotion_distilbert.ipynb) |
| `t5_response.ipynb` | T5-small fine-tuning on EmpatheticDialogues | [🔗 View Notebook](../../blob/main/t5_response.ipynb) |

---

## 📋 Table of Contents

- [Live Demo & Datasets](#live-demo--datasets)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Pipeline Flow](#pipeline-flow)
- [Setup Guide](#setup-guide)
- [Environment Variables](#environment-variables)
- [GitHub Secrets](#github-secrets)
- [Models](#models)
- [API Reference](#api-reference)
- [Cost Estimate](#cost-estimate)
- [Demo Checklist](#demo-checklist)
- [Limitations](#limitations)
- [Future Work](#future-work)

---

## 🏗️ Architecture Overview

```
User (S3 Frontend)
        ↓  API Gateway
Lambda 1 (DistilBERT — Emotion & Safety)
        ↓  safe input
Lambda 2 (T5 — Response Generation)
        ↓  saves conversation
DynamoDB (mental-health-conversations)
        ↓  CloudWatch metric +1
CloudWatch Alarm (ConversationCount >= 5)
        ↓  IN ALARM
SNS Topic (pipeline-trigger)
        ↓  invokes
Lambda 3 (lambda3-scheduler)
        ↓  exports JSON
S3 Bucket (myapp-pipeline-data) — versioned
        ↓  GitHub API dispatch
GitHub Actions (deploy.yml)
        ↓  update-function-code
Lambda 1 & 2 Redeployed from ECR ✅
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Amazon S3 (Static Website Hosting) |
| API | Amazon API Gateway (REST) |
| Inference | AWS Lambda (Python 3.11, Docker) |
| Emotion Model | DistilBERT (fine-tuned, 4-class) |
| Response Model | T5-small (EmpatheticDialogues fine-tuned) |
| Database | Amazon DynamoDB |
| Container Registry | Amazon ECR |
| Pipeline Trigger | Amazon CloudWatch + SNS |
| Data Export | AWS Lambda (Python) |
| Data Storage | Amazon S3 (versioning enabled) |
| CI/CD | GitHub Actions |
| Region | us-east-1 |

---

## 📁 Project Structure

```
mental-health-chatbot/
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD pipeline
├── lambda1_emotion/
│   ├── Dockerfile                  # Lambda 1 container
│   ├── handler.py                  # DistilBERT emotion classifier
│   └── distilbert_4class/          # Model weights (not in repo)
│       ├── config.json
│       ├── pytorch_model.bin
│       └── tokenizer files
├── lambda2_response/
│   ├── Dockerfile                  # Lambda 2 container
│   ├── handler.py                  # T5 response generator
│   └── t5_empathetic_4class/       # Model weights (not in repo)
│       ├── config.json
│       ├── pytorch_model.bin
│       └── tokenizer files
├── emotion_distilbert.ipynb        # DistilBERT training notebook (Google Colab)
├── t5_response.ipynb               # T5 training notebook (Google Colab)
├── infrastructure.yaml             # CloudFormation IaC template
├── lambda3_export.zip              # Lambda 3 source code (export & GitHub trigger)
├── index.html                      # Chatbot frontend (deployed to S3)
├── .gitignore
└── README.md
```

> ⚠️ Model weight folders (`distilbert_4class/`, `t5_empathetic_4class/`) are not committed to GitHub due to file size limits. They are packaged directly into Docker images and stored in Amazon ECR.
### Model Output credentials :
> **[Click here:](https://drive.google.com/drive/folders/1KOvc23agxWMU_TXL54BmQwOQKaSS_Y_p?usp=sharing)**
>

---

## 🔄 Pipeline Flow

### Inference Pipeline
1. User sends message via `index.html` hosted on S3
2. JavaScript `fetch()` sends POST request to API Gateway
3. **Lambda 1** receives the message:
   - Validates input (max 2000 chars)
   - Checks for crisis keywords → returns hotline response immediately if detected
   - Runs DistilBERT to classify emotion: `joy`, `sadness`, `anger`, `fear`
4. **Lambda 2** generates response:
   - Constructs prompt: `emotion: {label} message: {input}`
   - T5 model generates empathetic response
   - Saves conversation to DynamoDB
   - Pushes `+1` to CloudWatch metric `MyApp/ConversationCount`
5. Response returned to user

### Automated Data Pipeline
1. **CloudWatch alarm** (`five-conversations-alarm`) monitors `ConversationCount`
2. When `Sum >= 5` within 5 minutes → alarm triggers
3. **SNS topic** (`pipeline-trigger`) notifies:
   - Email to configured address
   - Invokes Lambda 3
4. **Lambda 3** (`lambda3-scheduler`):
   - Scans entire DynamoDB table
   - Serialises to `new_data.json`
   - Uploads to S3 (`myapp-pipeline-data`) — previous versions preserved
   - Calls GitHub API to dispatch `deploy.yml` workflow
5. **GitHub Actions** pipeline runs:
   - Downloads `new_data.json` from S3
   - Simulates retraining step
   - Redeploys Lambda 1 & 2 from ECR
   - Verifies both functions are active

---

## 🚀 Setup Guide

### Prerequisites
- AWS Academy Learner Lab account
- GitHub account
- Docker Desktop installed locally
- AWS CLI configured

### Phase 1 — AWS Prerequisites

```bash
# Create ECR repositories
aws ecr create-repository --repository-name lambda1-emotion --region us-east-1
aws ecr create-repository --repository-name lambda2-response --region us-east-1

# Create S3 pipeline bucket
aws s3 mb s3://myapp-pipeline-data --region us-east-1
```

### Phase 2 — Build and Push Docker Images

```bash
1. Login to ECR

2. Build and push Lambda 1

3. Build and push Lambda 2

```

### Phase 3 — Deploy Lambda Functions

```bash
1. Deploy Lambda 1

2. Deploy Lambda 2

3. Deploy Lambda 3 (zip upload)

```

### Phase 4 — CloudWatch Alarm Setup

```bash
1. Create CloudWatch alarm
2. Enable SNS to trigger email & github CI/CD pipeline 

```

### Phase 5 — Test End-to-End

```bash
- Manually invoke Lambda 3 to test pipeline

```

---

## 🔐 Environment Variables

### Lambda 3 (`lambda3-scheduler`)

| Key | Value |
|---|---|
| `DYNAMODB_TABLE` | `mental-health-conversations` |
| `S3_BUCKET` | `myapp-pipeline-data` |
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `GITHUB_OWNER` | GitHub username |
| `GITHUB_REPO` | Repository name |
| `GITHUB_WORKFLOW` | `deploy.yml` |

### Lambda 2 (`lambda2-response`)

| Key | Value |
|---|---|
| `HF_HOME` | `/tmp` |
| `TRANSFORMERS_CACHE` | `/tmp` |

### Lambda 1 (`lambda1-emotion`)

| Key | Value |
|---|---|
| `LAMBDA2_ARN` | ARN of lambda2-response function |

---

## 🔑 GitHub Secrets

Add these in your repo → **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS access key (from Learner Lab AWS Details) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (from Learner Lab AWS Details) |
| `AWS_SESSION_TOKEN` | Session token (from Learner Lab AWS Details) |
| `S3_BUCKET` | `myapp-pipeline-data` |
| `ECR_REGISTRY` | `...` |

> ⚠️ **Learner Lab Note:** AWS credentials expire every ~4 hours. Update all three AWS secrets before running the pipeline or doing a demo.

---

## 🤖 Models

### DistilBERT Emotion Classifier
- **Base model:** `distilbert-base-uncased`
- **Task:** 4-class sequence classification
- **Classes:** `joy (0)`, `sadness (1)`, `anger (2)`, `fear (3)`
- **Training data:** dair-ai/emotion dataset
- **Accuracy:** 87.3% | **F1:** 86.9%
- **Inference time:** ~310ms (warm)

### T5 Empathetic Response Generator
- **Base model:** `t5-small`
- **Task:** Conditional text generation
- **Training data:** EmpatheticDialogues (Meta AI, 25K conversations)
- **Input format:** `emotion: {label} message: {user_input}`
- **BLEU-4:** 18.2 | **ROUGE-L:** 0.412
- **Inference time:** ~900ms (warm)

### Crisis Detection
Keyword-based safety check **before** any ML inference:
```python
CRISIS_KEYWORDS = [
    "hurt myself", "kill myself", "suicide", "suicidal",
    "don't want to live", "end my life", "want to die",
    "self harm", "self-harm", "no reason to live"
]
```
Returns Thai + English emergency hotline numbers immediately.

---

## 📡 API Reference

### POST `/chat`

**Endpoint:** `...`

**Request:**
```json
{
  "message": "I am feeling very sad today",
  "session_id": "user-123"
}
```

**Response:**
```json
{
  "response": "I'm sorry to hear that. Would you like to talk about what's going on?",
  "emotion": "sadness"
}
```

**Crisis Response:**
```json
{
  "response": "I am concerned about you. Please reach out to a professional: [(02) 713 6793 (Thai), (02) 713-6791 (English)]",
  "emotion": "crisis",
  "routed_to": "safe_response"
}
```

---

## 💰 Cost Estimate

Estimated for AWS us-east-1, ~100 conversations/day:

| Service | Daily Cost |
|---|---|
| Lambda 1 & 2 (inference) | ~$0.006 |
| Lambda 3 (pipeline) | ~$0.0001 |
| DynamoDB | ~$0.0003 |
| API Gateway | ~$0.0004 |
| S3 Storage | ~$0.0001 |
| CloudWatch | ~$0.0033 |
| ECR Storage (~5GB) | ~$0.0167 |
| SNS | <$0.0001 |
| **Total** | **~$0.027/day** |

---

## ⚠️ Limitations

- **No real retraining:** Model weights are static. Pipeline simulates retraining by redeploying existing containers. Production implementation would use SageMaker Training Jobs.
- **Cold start latency:** Lambda cold starts take 45-90 seconds due to large transformer models (~400-800MB).
- **Credential expiry:** AWS Academy session tokens expire every ~4 hours, requiring manual GitHub secret updates.
- **4-class emotion taxonomy:** Simplified emotion space — full human emotional range is broader.

---

## 🔭 Future Work

- [ ] Integrate **Amazon SageMaker** for real model fine-tuning on new conversation data
- [ ] Add **Lambda SnapStart** or Provisioned Concurrency to eliminate cold start latency
- [ ] Expand crisis detection to **Thai language**
- [ ] Add **A/B testing** infrastructure to compare model versions
- [ ] Implement **Infrastructure as Code** using AWS CloudFormation or Terraform
- [ ] Add **model confidence score** as a CloudWatch custom metric
- [ ] Implement **conversation quality rating** for user feedback collection

---

## 📚 References

- Rashkin et al. (2019). *Towards Empathetic Open-Domain Conversation Models.* ACL 2019.
- Sanh et al. (2019). *DistilBERT, a distilled version of BERT.* arXiv:1910.01108.
- Raffel et al. (2020). *Exploring the Limits of Transfer Learning with T5.* JMLR 21(140).
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)

---

## 👤 Authors

**Zwe Yu Ya Kyaw Zin Oo (st125990), Supipi Karunathilaka (st126489)**

Master of Science in Data Science and Artificial Intelligence

Asian Institute of Technology

April 2026
