# Deployment Packaging Summary

**Current Status:** Frontend and backend are complete and ready for deployment to AWS. All static assets have been validated, CORS is configured, and three deployment pathways are documented.

## What's Been Delivered

### ✅ Frontend Application
- **Location:** `frontend/` directory
- **Files:** `index.html`, `app.js`, `styles.css`, `config.js`
- **Features:**
  - Login/Register with email and password
  - Session management via `sessionStorage`
  - Music search (by title, artist, album, year)
  - Song subscriptions (add/remove)
  - Logout
  - Responsive design (mobile/tablet/desktop)
  - CORS-compatible (separate origin from backend)

### ✅ Backend Services
- **FastAPI app:** `app/main.py` with CORS middleware
- **Routes:**
  - `POST /login` — Authenticate user
  - `POST /register` — Create new account
  - `GET /logout`, `DELETE /logout` — End session
  - `GET /songs/search`, `POST /songs/search` — Query by title/artist/album/year
  - `GET /subscriptions/{email}` — Fetch user's subscriptions
  - `POST /subscriptions` — Add subscription
  - `DELETE /subscriptions` — Remove subscription
  - `GET /health` — Health check
- **Database:** DynamoDB (login, music, subscriptions tables)
- **Storage:** S3 bucket with presigned image URLs
- **Authentication:** Email + password (plaintext in demo; hash in production)

### ✅ Deployment Documentation
1. **[deployment_guide.md](deployment_guide.md)** — Comprehensive step-by-step for all 3 backends + frontend
2. **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** — Executable checklist for end-to-end testing
3. **[frontend/README.md](frontend/README.md)** — Frontend-specific documentation and hosting options
4. **[deploy-frontend-s3.ps1](deploy-frontend-s3.ps1)** — Automated S3 deployment script

### ✅ Docker & Infrastructure
- **Dockerfile** — Multi-stage build for FastAPI app (Python 3.12, uvicorn on port 80)
- **deploy/ec2/user_data.sh** — EC2 bootstrap script (pulls image from ECR, starts container)
- **deploy/ecs/task-definition.json** — ECS Fargate task definition (1 vCPU, 3 GB RAM)
- **deploy/lambda/template.yaml** — SAM template for Lambda + API Gateway (CORS configured)

## Deployment Pathways

### Local Development (Free)
```bash
cd frontend && python -m http.server 5173
# Separately: cd app && uvicorn main:app --reload --host 127.0.0.1 --port 8000
# Frontend: http://127.0.0.1:5173
# Backend: http://127.0.0.1:8000
```

### Option 1: EC2 + S3 Frontend (~$5–10/month)
- **Backend:** Docker container on EC2 instance (t2.small, ~$8/mo)
- **Frontend:** S3 static website (~$1/mo)
- **Deploy Time:** ~15 minutes (instance startup + image pull)
- **Setup:** Manual EC2 instance creation, user_data script
- **Best for:** Learning, demos, low traffic

### Option 2: ECS Fargate + S3 Frontend (~$15–30/month)
- **Backend:** Fargate task with ALB (~$15–30/mo)
- **Frontend:** S3 static website (~$1/mo)
- **Deploy Time:** ~10 minutes (service creation, task startup)
- **Setup:** Manual VPC/ALB/security group setup, then deploy script
- **Best for:** Production-ready, auto-scaling, managed infrastructure

### Option 3: Lambda + S3 Frontend (~$5–10/month)
- **Backend:** Lambda function + API Gateway (~$1–5/mo)
- **Frontend:** S3 static website (~$1/mo)
- **Deploy Time:** ~5 minutes (SAM deploy)
- **Setup:** Fully automated via SAM CloudFormation
- **Best for:** Serverless, minimal ops, pay-per-request

## Quick Start: Deploy to AWS Learner Lab

### Step 1: Create DynamoDB tables & S3 bucket (Shared)
```bash
pip install boto3 tqdm requests
python q1_create_login.py
python q2_create_music.py
python q3_load_music.py
python create_subscriptions_table.py
python q4_S3_images.py
```

### Step 2: Build and push Docker image
```powershell
# Set Learner Lab credentials
$env:AWS_ACCESS_KEY_ID = "..."
$env:AWS_SECRET_ACCESS_KEY = "..."
$env:AWS_SESSION_TOKEN = "..."

# Build and push
docker build -t music-subscription-api:latest .
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
docker tag music-subscription-api:latest "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api:latest"
docker push "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api:latest"
```

### Step 3: Deploy backend (choose one)

**Option A: EC2**
```powershell
# Launch EC2 via AWS Console (t2.small, LabInstanceProfile, user_data.sh)
# Wait for status checks to pass
# Copy Public DNS, then deploy frontend to S3 pointing at that DNS
```

**Option B: ECS**
```powershell
pwsh -File .\deploy\ecs\deploy.ps1 `
  -AccountId <ACCOUNT_ID> `
  -Cluster music-subscription-cluster `
  -Service music-subscription-service `
  -LabRoleArn "arn:aws:iam::<ACCOUNT_ID>:role/LabRole" `
  -Bucket rmit-music-images-unique-91725 `
  -Region us-east-1
```

**Option C: Lambda**
```powershell
sam build -t deploy/lambda/template.yaml
sam deploy `
  --stack-name music-subscription-lambda `
  --region us-east-1 `
  --capabilities CAPABILITY_IAM `
  --resolve-s3 `
  --parameter-overrides `
    LabRoleArn="arn:aws:iam::<ACCOUNT_ID>:role/LabRole" `
    S3BucketName="rmit-music-images-unique-91725"
```

### Step 4: Deploy frontend to S3
```powershell
# Get your backend URL from the deployment above (EC2 DNS, ALB DNS, or Lambda API ID)
.\deploy-frontend-s3.ps1 -ApiBaseUrl "http://<backend-url>"
```

### Step 5: Test
- Open the frontend URL printed by the S3 deployment script
- Register a new user
- Login with test account: `s41396730@student.rmit.edu.au` / `012345`
- Query songs, subscribe, remove subscriptions, logout
- See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for detailed testing flow

## Cost Control

**Budget-aware deployment:**
- Start with **Lambda** (cheapest, fully serverless, pay-per-request)
- Use **S3** for frontend (negligible cost, ~$1/month)
- **Avoid ALBs** unless testing ECS (they cost $10–20/month sitting idle)
- **Verify cleanup** before leaving lab session:
  ```bash
  aws cloudformation list-stacks --region us-east-1 --query 'StackSummaries[?StackStatus!=`DELETE_COMPLETE`]' --output table
  aws ec2 describe-instances --region us-east-1 --query 'Reservations[*].Instances[?State.Name==`running`]' --output table
  aws elbv2 describe-load-balancers --region us-east-1 --output table
  ```

## Configuration Reference

### Frontend API Base URL Options

**Priority order:**
1. **Query parameter:** `?apiBase=https://...` (stored in localStorage)
2. **localStorage:** Previously saved via query parameter
3. **config.js:** Default in `frontend/config.js` (must rebuild to change)

**Values for different backends:**

| Backend | URL |
|---|---|
| Local dev (backend) | `http://127.0.0.1:8000` |
| EC2 direct | `http://ec2-XX-XX-XX-XX.compute-1.amazonaws.com` |
| EC2 via API GW | `https://api-id.execute-api.us-east-1.amazonaws.com/prod` |
| ECS via ALB | `http://music-subscription-alb-XXX.us-east-1.elb.amazonaws.com` |
| ECS via API GW | `https://api-id.execute-api.us-east-1.amazonaws.com/prod` |
| Lambda via API GW | `https://api-id.execute-api.us-east-1.amazonaws.com/prod` |

### CORS Configuration

**FastAPI backend** (app/main.py):
```python
CORSMiddleware(
    app,
    allow_origins=origins,  # From env var FRONTEND_ORIGINS
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Lambda API Gateway** (deploy/lambda/template.yaml):
```yaml
Cors:
  AllowMethods: "'GET,POST,DELETE,OPTIONS'"
  AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
  AllowOrigin: "'*'"
```

## Testing Accounts

Pre-populated in DynamoDB `login` table:

| Email | Password | User Name |
|---|---|---|
| s41396730@student.rmit.edu.au | 012345 | TestUser1 |
| s3816088@student.rmit.edu.au | 012345 | TestUser2 |
| s3816089@student.rmit.edu.au | 012345 | TestUser3 |

## Troubleshooting

**"Frontend can't connect to backend"**
- Check browser console (F12 → Network tab) for CORS errors or 404/500
- Verify backend `/health` endpoint: `curl https://<backend>/health`
- Verify `apiBaseUrl` in `frontend/config.js` matches deployed backend

**"Login fails with 500"**
- Check backend logs: CloudWatch for ECS/Lambda, CloudShell for EC2
- Verify DynamoDB `login` table has test data: `aws dynamodb scan --table-name login --select COUNT`
- Verify IAM role has DynamoDB permissions

**"Images not loading"**
- Check S3 presigned URLs in browser Network tab (should be `https://s3.amazonaws.com/...?X-Amz-Signature=...`)
- Verify S3 bucket policy allows `s3:GetObject` from backend role

**"High AWS costs"**
- Check CloudFormation stacks: `aws cloudformation list-stacks --region us-east-1 | grep music`
- Check running instances: `aws ec2 describe-instances --region us-east-1 --filters Name=instance-state-name,Values=running`
- Check ALBs (biggest cost culprit): `aws elbv2 describe-load-balancers --region us-east-1`
- Delete unused resources immediately

## Next Steps

1. **Verify locally first:** Run `python -m http.server 5173` in frontend and `uvicorn app.main:app` separately
2. **Choose a deployment:** Lambda is cheapest and fastest to deploy
3. **Follow the checklist:** Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for step-by-step testing
4. **Document your setup:** Keep notes on URLs, ARNs, and credentials in a secure location
5. **Test all three backends:** Each has different scaling and cost characteristics

## Files & Locations

```
.
├── frontend/                    # Static web app
│   ├── index.html              # UI structure
│   ├── app.js                  # Application logic
│   ├── styles.css              # Responsive styling
│   ├── config.js               # Configuration (API base URL)
│   └── README.md               # Frontend documentation
│
├── app/                        # FastAPI backend
│   ├── main.py                 # App entrypoint + CORS
│   ├── db.py                   # DynamoDB + S3 helpers
│   ├── schemas.py              # Pydantic models
│   └── routers/                # Endpoint modules
│       ├── auth.py             # Login/Register
│       ├── music.py            # Song search
│       └── subscriptions.py     # User subscriptions
│
├── deploy/                     # Deployment configurations
│   ├── ec2/                    # EC2 deployment
│   │   └── user_data.sh        # Bootstrap script
│   ├── ecs/                    # ECS Fargate deployment
│   │   ├── deploy.ps1          # Deploy script
│   │   └── task-definition.json
│   ├── lambda/                 # Lambda deployment
│   │   └── template.yaml       # SAM template
│   └── apigw/                  # API Gateway proxy
│       ├── deploy-ec2.ps1
│       └── deploy-ecs.ps1
│
├── Dockerfile                  # Container image
├── requirements.txt            # Python dependencies
├── deployment_guide.md         # Full deployment documentation
├── DEPLOYMENT_CHECKLIST.md     # Executable testing checklist
├── deploy-frontend-s3.ps1      # Frontend S3 deployment script
└── q1-q4_*.py                  # DynamoDB table creation scripts
```

---

**Status: Ready for AWS deployment.** All code is syntactically valid, documented, and tested locally. Use the deployment scripts and checklist to get up and running in the Learner Lab.
