# Quick Reference Card

## Local Development (5 minutes)

```bash
# Terminal 1: Frontend
cd frontend
python -m http.server 5173
# → http://127.0.0.1:5173/

# Terminal 2: Backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000/docs (Swagger)

# Test with: http://127.0.0.1:5173/?apiBase=http://127.0.0.1:8000
```

## AWS Learner Lab Setup (Prerequisites)

```bash
# 1. Create tables & bucket
python q1_create_login.py
python q2_create_music.py
python q3_load_music.py
python create_subscriptions_table.py
python q4_S3_images.py

# 2. Verify
aws dynamodb list-tables --region us-east-1
aws s3 ls | grep rmit-music-images

# 3. Build Docker image
docker build -t music-subscription-api:latest .
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
docker tag music-subscription-api:latest "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api:latest"
docker push "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api:latest"
```

## Deployment Options (Choose One)

### Option A: Lambda (Fastest ⚡)
```bash
sam build -t deploy/lambda/template.yaml
sam deploy \
  --stack-name music-subscription-lambda \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    LabRoleArn="arn:aws:iam::<ACCOUNT_ID>:role/LabRole" \
    S3BucketName="rmit-music-images-unique-91725"

# Get API URL from output → https://<api-id>.execute-api.us-east-1.amazonaws.com/prod
```

### Option B: ECS Fargate (Scalable 🚀)
```powershell
# First: Setup VPC/ALB/security group (see deployment_guide.md)
# Then:
pwsh -File .\deploy\ecs\deploy.ps1 `
  -AccountId <ACCOUNT_ID> `
  -Cluster music-subscription-cluster `
  -Service music-subscription-service `
  -LabRoleArn "arn:aws:iam::<ACCOUNT_ID>:role/LabRole" `
  -Bucket rmit-music-images-unique-91725 `
  -Region us-east-1

# Get ALB DNS name from CloudFormation outputs
```

### Option C: EC2 (Simple 📦)
```bash
# Launch EC2 via console:
# - AMI: Amazon Linux 2023
# - Type: t2.small
# - IAM: LabInstanceProfile
# - Security group: Allow HTTP 80 + SSH 22
# - User data: deploy/ec2/user_data.sh (edit ACCOUNT_ID and BUCKET)

# Get Public DNS after Status Checks = 2/2 passed
```

## Deploy Frontend to S3

```powershell
.\deploy-frontend-s3.ps1 -ApiBaseUrl "http://<your-backend-url>"

# Example backend URLs:
# Lambda: https://<api-id>.execute-api.us-east-1.amazonaws.com/prod
# ECS: http://music-subscription-alb-XXX.us-east-1.elb.amazonaws.com
# EC2: http://ec2-XX-XX-XX-XX.compute-1.amazonaws.com
```

## Test Frontend

1. Open frontend S3 URL in browser
2. Register: `testuser@example.com` / `password123`
3. Login: Use test account `s41396730@student.rmit.edu.au` / `012345`
4. Query: Artist "Taylor Swift"
5. Subscribe: Click result
6. Remove: Click subscription
7. Logout

**Browser dev tools (F12):**
- Check Network tab for CORS errors
- Check Console for JavaScript errors
- Check Application → Session Storage for credentials

## Health Checks

```bash
# Test backend
curl https://<backend-url>/health
# → {"status": "ok"}

# Test frontend loads
curl https://<s3-bucket>.s3-website-us-east-1.amazonaws.com/
# → Should return HTML (status 200)

# Check DynamoDB has data
aws dynamodb scan --table-name music --select COUNT --region us-east-1
# → Should show Count: ~1400
```

## API Testing (curl)

```bash
# Login
curl -X POST "https://<backend>/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"s41396730@student.rmit.edu.au","password":"012345"}'

# Search songs
curl "https://<backend>/songs/search?artist=Taylor%20Swift"

# Get subscriptions
curl "https://<backend>/subscriptions/s41396730@student.rmit.edu.au"

# Add subscription
curl -X POST "https://<backend>/subscriptions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email":"s41396730@student.rmit.edu.au",
    "title":"Love Story",
    "artist":"Taylor Swift",
    "year":"2008",
    "album":"Fearless",
    "img_url":"Taylor_Swift.jpg"
  }'

# Remove subscription
curl -X DELETE "https://<backend>/subscriptions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email":"s41396730@student.rmit.edu.au",
    "title":"Love Story",
    "album":"Fearless"
  }'
```

## Cleanup (Prevent Costs)

```bash
# Delete Lambda stack
sam delete --stack-name music-subscription-lambda --region us-east-1 --no-prompts

# Delete S3 frontend bucket
aws s3 rm s3://<bucket-name> --recursive
aws s3 rb s3://<bucket-name>

# Stop EC2 instance
aws ec2 stop-instances --instance-ids <instance-id> --region us-east-1

# Delete ECS resources
aws ecs delete-service --cluster music-subscription-cluster --service music-subscription-service --force
aws elbv2 delete-load-balancer --load-balancer-arn <alb-arn>
aws elbv2 delete-target-group --target-group-arn <tg-arn>
aws ec2 delete-security-group --group-id <sg-id>
aws ecs delete-cluster --cluster music-subscription-cluster

# Delete CloudFormation stacks
aws cloudformation delete-stack --stack-name music-subscription-apigw-ec2
aws cloudformation delete-stack --stack-name music-subscription-apigw-ecs
```

## Key Files & Locations

| File | Purpose |
|------|---------|
| `frontend/config.js` | Frontend API base URL (edit before deploying) |
| `app/main.py` | Backend CORS config (env var: FRONTEND_ORIGINS) |
| `Dockerfile` | Container image definition |
| `deploy-frontend-s3.ps1` | Automated S3 deployment |
| `deployment_guide.md` | Complete deployment docs (600+ lines) |
| `DEPLOYMENT_CHECKLIST.md` | Executable testing checklist |
| `DEPLOYMENT_PACKAGING.md` | Strategy & cost analysis |

## Test Accounts

```
Email: s41396730@student.rmit.edu.au
Password: 012345
User: TestUser1

Email: s3816088@student.rmit.edu.au
Password: 012345
User: TestUser2

Email: s3816089@student.rmit.edu.au
Password: 012345
User: TestUser3
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| CORS error | Verify backend CORS middleware is active, check `FRONTEND_ORIGINS` env var |
| 404 on `/health` | Backend not running or wrong URL in frontend config |
| Login fails with 500 | Check backend logs, verify DynamoDB `login` table has data |
| Images not loading | Check S3 presigned URLs valid, verify S3 bucket name correct |
| Can't deploy Lambda | Verify `LabRole` ARN is correct, check Learner Lab session is active |
| Frontend won't load | Check S3 bucket public policy, verify S3 website hosting enabled |
| High costs at end | Check for running ALBs (cost culprit), verify all resources cleaned up |

## Documentation Links

- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** — What was built
- **[DEPLOYMENT_PACKAGING.md](DEPLOYMENT_PACKAGING.md)** — Deployment strategy
- **[deployment_guide.md](deployment_guide.md)** — Step-by-step (600+ lines)
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** — Testing checklist
- **[frontend/README.md](frontend/README.md)** — Frontend docs
- **[README.md](README.md)** — Project overview

---

**Pro Tip:** Start with Lambda for fastest deployment (5 min), then scale to ECS or EC2 if needed.
