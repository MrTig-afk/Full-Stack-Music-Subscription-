# Cloud Computing - Music Database ETL Pipeline

This project implements a cloud-based infrastructure for managing a music library using **AWS DynamoDB** and **S3**. It includes scripts for schema creation, batch data ingestion, an automated image processing pipeline, and a static web frontend for the subscription app.

## 🚀 Project Overview

- **Database:** Amazon DynamoDB (NoSQL)
- **Storage:** Amazon S3 (Object Storage)
- **Language:** Python 3.x
- **SDK:** Boto3

---

## 🛠️ Environment Setup

### 1. Local Configuration

Clone the repository and set up your virtual environment:

Preferred (if `uv` installed):

```bash
uv sync --no-dev
```

Fallback (without `uv`):

```bash
# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows (Git Bash)
# source venv/bin/activate    # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. AWS CLI Configuration

You must have the AWS CLI installed. Use the **DevTeam** credentials provided in our private channel:

```bash
aws configure
```

**Required Settings:**

- **AWS Access Key ID:** [Paste Team Key]
- **AWS Secret Access Key:** [Paste Team Secret]
- **Default region name:** `us-east-1` (Required for consistency)
- **Default output format:** `json`

---

## 📂 Project Structure

| File                 | Description                                                                 |
| :------------------- | :-------------------------------------------------------------------------- |
| `q1_create_login.py` | Creates the `login` table and populates 10 RMIT student entities.           |
| `q2_create_music.py` | Defines the `music` table schema (Title = Partition Key, Album = Sort Key). |
| `q3_load_music.py`   | Batch uploads 137 songs from the JSON dataset to DynamoDB.                  |
| `q4_s3_images.py`    | Downloads artist images and uploads them to the unique S3 bucket.           |
| `frontend/`          | Static HTML/CSS/JS frontend for login, register, query, and subscriptions.  |
| `2026a2_songs.json`  | The raw source data.                                                        |

---

## ⚡ How to Run

Run the scripts in the following order to ensure dependencies (like table creation) are met:

Preferred (if `uv` installed):

1. **Initialize Login Table:** `uv run python q1_create_login.py`
2. **Initialize Music Table:** `uv run python q2_create_music.py`
3. **Load Song Data:** `uv run python q3_load_music.py`
4. **Transfer Images:** `uv run python q4_s3_images.py`

Fallback (without `uv`):

1. **Initialize Login Table:** `python q1_create_login.py`
2. **Initialize Music Table:** `python q2_create_music.py`
3. **Load Song Data:** `python q3_load_music.py`
4. **Transfer Images:** `python q4_s3_images.py`

---

## 📊 Verification

You can verify the deployment by running:

```bash
# Check DynamoDB item count
aws dynamodb scan --table-name music --select "COUNT"

# List S3 bucket contents
aws s3 ls s3://your-unique-bucket-name/
```

## 🌐 FastAPI Backend

This FastAPI application provides backend APIs for the music subscription system. It connects to AWS DynamoDB and supports user authentication, song search, and subscription management.

## 🖥️ Frontend

The static frontend lives in [frontend/](frontend/) and consumes the backend REST API directly. See [deployment_guide.md](deployment_guide.md) for the recommended hosting path and backend URL configuration.

---

## 🚀 Features

- User Registration
- User Login & Logout
- Music Search (by title, artist, album, year)
- Subscribe to songs
- Remove subscribed songs
- View user subscriptions

---

## 🔗 API Endpoints

- POST `/register` → Register new user
- POST `/login` → Login user
- GET `/logout` → Logout
- POST `/logout` → Logout
- DELETE `/logout` → Logout
- GET `/health` → Health check
- GET `/songs/search?title=&artist=&album=&year=` → Search songs (query params)
- POST `/songs/search` → Search songs
- GET `/subscriptions/{email}` → Get user subscriptions
- POST `/subscriptions` → Add subscription
- DELETE `/subscriptions` → Remove subscription
- DELETE `/subscriptions/{email}/{music_id}` → Remove subscription by resource path

---

## ⚙️ Setup & Run

### 1. Activate virtual environment

Preferred (if `uv` installed):

```bash
# No manual activation needed; uv manages env per project
uv sync --no-dev
```

Fallback (without `uv`):

```bash
# Windows
source venv/Scripts/activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install dependencies

Preferred (if `uv` installed):

```bash
uv sync --no-dev
```

Fallback (without `uv`):

```bash
pip install fastapi uvicorn boto3 pydantic
```

### 3. Configure AWS

```bash
aws configure
```

(For AWS Learner Lab, use access key, secret key, and session token.)

### 4. Run FastAPI

Preferred (if `uv` installed):

```bash
uv run dev
```

Fallback (without `uv`):

```bash
uvicorn app.main:app --reload
```

### 5. Test APIs

Open in browser: <http://127.0.0.1:8000/docs>

🧪 Testing Flow
Register → /register
Login → /login
Search songs → /songs/search
Subscribe → /subscriptions
View subscriptions → /subscriptions/{email}
Remove subscription → /subscriptions (DELETE)
Logout → /logout

---

## 🧰 Dependency Management (uv)

This project is managed by `uv` via `pyproject.toml` and `uv.lock`.

```bash
# sync local environment
uv sync --no-dev

# after dependency changes in pyproject.toml
uv lock

# generate requirements.txt for environments that still need it
uv export --no-emit-workspace --no-emit-project --no-hashes --no-annotate --no-dev > .\requirements.txt
```

---

## ☁️ Backend Deployment Artifacts

Region is standardized to `us-east-1`.

### 1) EC2 (containerized app)

- `Dockerfile` builds the FastAPI backend image with `uv`.
- `deploy/ec2/user_data.sh` bootstraps an EC2 instance, pulls from ECR, and runs the container on port `80`.
- `deploy/apigw/ec2-rest-proxy.yaml` and `deploy/apigw/deploy-apigw-ec2.sh` expose EC2 backend through API Gateway REST API.

### 2) ECS (containerized app)

- `deploy/ecs/task-definition.json` is the baseline Fargate task definition.
- `deploy/ecs/deploy-ecs.sh` builds/pushes image to ECR and updates ECS service.
- `deploy/apigw/ecs-rest-proxy.yaml` and `deploy/apigw/deploy-apigw-ecs.sh` expose ECS backend (usually ALB URL) through API Gateway REST API.

```powershell
./deploy/ecs/deploy-ecs.sh `
	--account-id <AWS_ACCOUNT_ID> `
	--cluster <ECS_CLUSTER_NAME> `
	--service <ECS_SERVICE_NAME> `
	--lab-role-arn <LABROLE_ARN> `
	--bucket <S3_BUCKET_NAME> `
	--region us-east-1
```

### 3) API Gateway + Lambda (serverless)

- `lambda_handler.py` contains the `Mangum` adapter for FastAPI.
- `deploy/lambda/template.yaml` defines REST API routes and Lambda deployment.

```bash
sam build -t deploy/lambda/template.yaml
sam deploy \
	--stack-name music-subscription-lambda \
	--region us-east-1 \
	--capabilities CAPABILITY_IAM \
	--parameter-overrides \
		LabRoleArn=<LABROLE_ARN> \
		S3BucketName=<S3_BUCKET_NAME>
```

### API Gateway for EC2 backend

```powershell
./deploy/apigw/deploy-apigw-ec2.sh `
	--backend-base-url http://<EC2_PUBLIC_DNS_OR_IP> `
	--region us-east-1
```

### API Gateway for ECS backend

```powershell
./deploy/apigw/deploy-apigw-ecs.sh `
	--backend-base-url http://<ECS_ALB_DNS_NAME> `
	--region us-east-1
```

Note: EC2/ECS backend must be reachable from API Gateway over HTTP/HTTPS. If backend sits in private subnet only, use VPC Link pattern instead of public proxy integration.

---

## 📦 Deployment & Packaging

This project is **ready for deployment to AWS** with three independent backend options and a static frontend.

### Quick Links

- **[DEPLOYMENT_PACKAGING.md](DEPLOYMENT_PACKAGING.md)** — Overview of deployment options, cost analysis, and quick-start guide
- **[deployment_guide.md](deployment_guide.md)** — Complete step-by-step instructions for all 3 backends (EC2, ECS, Lambda) + frontend
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** — Executable testing checklist for validating all deployment scenarios
- **[frontend/README.md](frontend/README.md)** — Frontend-specific documentation and hosting options
- **[deploy/frontend/deploy-frontend-s3.sh](deploy/frontend/deploy-frontend-s3.sh)** — Automated script to deploy frontend to S3

### Deployment Options

| Backend | Frontend | Cost | Setup Time | Best For |
|---|---|---|---|---|
| **EC2** | S3 | ~$5–10/mo | ~15 min | Learning, demos |
| **ECS Fargate** | S3 | ~$15–30/mo | ~20 min | Production, auto-scaling |
| **Lambda** | S3 | ~$5–10/mo | ~5 min | Serverless, minimal ops |
| **Local Dev** | Local Server | Free | ~1 min | Testing, development |

### Quick Start

```bash
# 1. Create DynamoDB tables and S3 bucket (shared for all backends)
python q1_create_login.py
python q2_create_music.py
python q3_load_music.py
python create_subscriptions_table.py
python q4_S3_images.py

# 2. Deploy frontend to S3 (after deploying backend)
.\deploy-frontend-s3.ps1 -ApiBaseUrl "http://<your-backend-url>"

# 3. Test in browser
# Open http://<frontend-s3-url>
```

For detailed instructions, see [DEPLOYMENT_PACKAGING.md](DEPLOYMENT_PACKAGING.md).
