# Deployment Checklist — Music Subscription App

Complete end-to-end deployment checklist for testing all three backend + frontend combinations.

## Pre-Deployment

- [ ] AWS Learner Lab active and green (check [AWS Academy](https://aws.amazon.com/training/awsacademy/))
- [ ] Your `ACCOUNT_ID` noted (run `aws sts get-caller-identity --query Account --output text`)
- [ ] Docker Desktop running (if building image locally)
- [ ] AWS CLI configured with Learner Lab credentials (see [deployment_guide.md#p5](deployment_guide.md#p5-build-and-push-the-docker-image-to-ecr))
- [ ] AWS SAM CLI installed (for Lambda: `sam --version`)
- [ ] Project repo cloned locally

## Shared Setup (do once)

- [ ] **P1:** Start Learner Lab session
- [ ] **P2:** Note Account ID and LabRole ARN
- [ ] **P3:** Create DynamoDB tables and S3 bucket
  - [ ] `q1_create_login.py` → login table with 10 test users
  - [ ] `q2_create_music.py` → music table with GSI `ArtistYearIndex`
  - [ ] `q3_load_music.py` → load 2026a2_songs.json (~1400 songs)
  - [ ] `q4_S3_images.py` → download artist images to S3
  - [ ] `create_subscriptions_table.py` → subscriptions table (empty)
  - [ ] Verify: `aws dynamodb list-tables --region us-east-1` (should show 3 tables)
- [ ] **P4:** Create ECR repository
  - [ ] `aws ecr create-repository --repository-name music-subscription-api --region us-east-1`
- [ ] **P5:** Build and push Docker image
  - [ ] Run `docker build -t music-subscription-api:latest .`
  - [ ] Push to ECR: `docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api:latest`

## Scenario 1: Frontend + EC2 Backend

**Goal:** Test frontend against EC2 Docker container running directly (no API Gateway wrapper).

### Deploy Backend (EC2)

- [ ] **Step 1.1:** Launch EC2 instance
  - [ ] Edit `deploy/ec2/user_data.sh` (replace `CHANGE_ME_ACCOUNT_ID` and `CHANGE_ME_BUCKET`)
  - [ ] Launch `t2.small` instance with user_data script
  - [ ] Attach `LabInstanceProfile` IAM role
  - [ ] Security group: allow HTTP/22 from `0.0.0.0/0`
- [ ] **Step 1.2:** Wait for instance startup (Status Checks 2/2 passed)
  - [ ] Copy EC2 Public DNS: `ec2-XX-XX-XX-XX.compute-1.amazonaws.com`
  - [ ] Test: `http://<EC2_PUBLIC_DNS>/health` → expect `{"status": "ok"}`
- [ ] Note EC2 URL for frontend config

### Deploy Frontend (S3)

- [ ] Create S3 bucket for frontend
  - [ ] `BUCKET_NAME="music-subscription-frontend-$(date +%s)"`
  - [ ] `aws s3 mb s3://$BUCKET_NAME --region us-east-1`
- [ ] Enable static website hosting
  - [ ] `aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document index.html`
- [ ] Apply public read policy
  - [ ] `aws s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false`
  - [ ] Attach public read bucket policy
- [ ] Update frontend config
  - [ ] Edit `frontend/config.js` → set `apiBaseUrl: "http://<EC2_PUBLIC_DNS>"`
- [ ] Upload frontend to S3
  - [ ] `aws s3 sync ./frontend s3://$BUCKET_NAME --exclude ".git/*" --exclude "*.md"`
- [ ] Test frontend
  - [ ] Open `http://$BUCKET_NAME.s3-website-us-east-1.amazonaws.com`
  - [ ] Register new user
  - [ ] Login with test account: `s41396730@student.rmit.edu.au` / `012345`
  - [ ] Query songs (e.g., artist "Taylor Swift")
  - [ ] Subscribe to a song
  - [ ] Verify subscription appears in list
  - [ ] Remove subscription
  - [ ] Logout

### Optional: Add API Gateway proxy for EC2

- [ ] **Step 1.3:** Deploy API Gateway proxy
  - [ ] `pwsh -File .\deploy\apigw\deploy-ec2.ps1 -BackendBaseUrl "http://<EC2_PUBLIC_DNS>"`
  - [ ] Note the API Gateway URL printed
- [ ] Re-deploy frontend pointing at API Gateway
  - [ ] Update `frontend/config.js` → `apiBaseUrl: "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod"`
  - [ ] Re-upload to S3
- [ ] Test through API Gateway proxy

### Cleanup (EC2)

- [ ] Stop or terminate EC2 instance
- [ ] Delete S3 bucket: `aws s3 rm s3://$BUCKET_NAME --recursive && aws s3 rb s3://$BUCKET_NAME`
- [ ] Delete API Gateway stack (if deployed): `aws cloudformation delete-stack --stack-name music-subscription-apigw-ec2 --region us-east-1`

---

## Scenario 2: Frontend + ECS Fargate Backend

**Goal:** Test frontend against ECS Fargate task load-balanced by ALB.

### Deploy Backend (ECS)

- [ ] **Step 2.1:** Create ECS cluster
  - [ ] Console: ECS → Clusters → Create
  - [ ] Name: `music-subscription-cluster`
  - [ ] Infrastructure: **AWS Fargate (serverless)**
- [ ] **Step 2.2:** Create CloudWatch log group
  - [ ] `aws logs create-log-group --log-group-name /ecs/music-subscription-api --region us-east-1`
- [ ] **Step 2.3:** Setup networking (VPC, subnets, ALB, target group, security group)
  - [ ] Get default VPC ID: `aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text`
  - [ ] Get 2 public subnets: `aws ec2 describe-subnets --filters Name=vpc-id,Values=<VPC_ID> --query "Subnets[*].[SubnetId]" --output text`
  - [ ] Create security group: `aws ec2 create-security-group --group-name ecs-music-sg --description "ECS music" --vpc-id <VPC_ID>`
  - [ ] Allow HTTP (port 80): `aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 80 --cidr 0.0.0.0/0`
  - [ ] Create ALB: `aws elbv2 create-load-balancer --name music-subscription-alb --subnets <SUBNET_1> <SUBNET_2> --security-groups <SG_ID> --scheme internet-facing --type application`
  - [ ] Create target group: `aws elbv2 create-target-group --name music-sub-tg --protocol HTTP --port 80 --vpc-id <VPC_ID> --target-type ip --health-check-path /health`
  - [ ] Create listener: `aws elbv2 create-listener --load-balancer-arn <ALB_ARN> --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=<TG_ARN>`
  - [ ] Note ALB DNS name: `music-subscription-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com`
- [ ] **Step 2.4:** Deploy ECS service
  - [ ] Run deploy script: `pwsh -File .\deploy\ecs\deploy.ps1 -AccountId <ACCOUNT_ID> -Cluster music-subscription-cluster -Service music-subscription-service -LabRoleArn "arn:aws:iam::<ACCOUNT_ID>:role/LabRole" -Bucket rmit-music-images-unique-91725 -Region us-east-1`
  - [ ] Or manually create service: `aws ecs create-service --cluster music-subscription-cluster --service-name music-subscription-service --task-definition music-subscription-api --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_1>,<SUBNET_2>],securityGroups=[<SG_ID>],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=<TG_ARN>,containerName=music-subscription-api,containerPort=80"`
- [ ] **Step 2.5:** Verify ECS deployment
  - [ ] Check service is ACTIVE with 1 running task (ECS console)
  - [ ] Test: `http://<ALB_DNS_NAME>/health` → expect `{"status": "ok"}`
  - [ ] Note ALB URL for frontend config

### Deploy Frontend (S3)

- [ ] Create S3 bucket for frontend (same as EC2 scenario)
- [ ] Update frontend config: `apiBaseUrl: "http://<ALB_DNS_NAME>"`
- [ ] Upload to S3 and test as in Scenario 1

### Optional: Add API Gateway proxy for ECS

- [ ] **Step 2.6:** Deploy API Gateway proxy
  - [ ] `pwsh -File .\deploy\apigw\deploy-ecs.ps1 -BackendBaseUrl "http://<ALB_DNS_NAME>"`
  - [ ] Note API Gateway URL
- [ ] Re-deploy frontend pointing at API Gateway

### Cleanup (ECS)

- [ ] Delete API Gateway stack: `aws cloudformation delete-stack --stack-name music-subscription-apigw-ecs --region us-east-1`
- [ ] Scale service to 0: `aws ecs update-service --cluster music-subscription-cluster --service music-subscription-service --desired-count 0 --region us-east-1`
- [ ] Delete service: `aws ecs delete-service --cluster music-subscription-cluster --service music-subscription-service --force --region us-east-1`
- [ ] Delete ALB: `aws elbv2 delete-load-balancer --load-balancer-arn <ALB_ARN>`
- [ ] Delete target group: `aws elbv2 delete-target-group --target-group-arn <TG_ARN>`
- [ ] Delete security group: `aws ec2 delete-security-group --group-id <SG_ID>`
- [ ] Delete cluster: `aws ecs delete-cluster --cluster music-subscription-cluster`
- [ ] Delete log group: `aws logs delete-log-group --log-group-name /ecs/music-subscription-api`
- [ ] Delete S3 bucket: `aws s3 rm s3://$BUCKET_NAME --recursive && aws s3 rb s3://$BUCKET_NAME`

---

## Scenario 3: Frontend + Lambda Backend

**Goal:** Test frontend against Lambda function wrapped by API Gateway REST API.

### Deploy Backend (Lambda)

- [ ] **Step 3.1:** Verify AWS SAM CLI installed
  - [ ] `sam --version` (should print version)
- [ ] **Step 3.2:** Build SAM application
  - [ ] `sam build -t deploy/lambda/template.yaml`
  - [ ] Verify `.aws-sam/build/` directory created
- [ ] **Step 3.3:** Deploy with SAM
  - [ ] `sam deploy --stack-name music-subscription-lambda --region us-east-1 --capabilities CAPABILITY_IAM --resolve-s3 --parameter-overrides LabRoleArn="arn:aws:iam::<ACCOUNT_ID>:role/LabRole" S3BucketName="rmit-music-images-unique-91725"`
  - [ ] Note API Gateway URL from outputs
- [ ] **Step 3.4:** Verify Lambda deployment
  - [ ] Test: `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/health` → expect `{"status": "ok"}`

### Deploy Frontend (S3)

- [ ] Create S3 bucket for frontend (same as previous scenarios)
- [ ] Update frontend config: `apiBaseUrl: "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod"`
- [ ] Upload to S3 and test as in Scenario 1

### Cleanup (Lambda)

- [ ] Delete CloudFormation stack: `sam delete --stack-name music-subscription-lambda --region us-east-1 --no-prompts`
- [ ] Delete S3 bucket: `aws s3 rm s3://$BUCKET_NAME --recursive && aws s3 rb s3://$BUCKET_NAME`

---

## Post-Deployment Testing

**For each scenario, verify all frontend flows work:**

1. **Registration**
   - [ ] Register new user with unique email
   - [ ] Verify "User already exists" error for duplicate email
   - [ ] Verify redirect to login after success
   
2. **Login**
   - [ ] Login with valid test account (e.g., `s41396730@student.rmit.edu.au` / `012345`)
   - [ ] Verify error message for invalid credentials
   - [ ] Verify username displayed on main page

3. **Query**
   - [ ] Query by artist (e.g., "Taylor Swift") → expect results
   - [ ] Query by title + album (e.g., "Love Story" / "Fearless") → expect results
   - [ ] Query by year (e.g., 1974) → expect results
   - [ ] Multi-criteria query (artist + year) → expect AND matching
   - [ ] Verify error if no fields filled

4. **Subscriptions**
   - [ ] Click "Subscribe" on query result → song adds to subscriptions
   - [ ] Verify duplicate subscription prevention
   - [ ] Click "Remove" on subscription → song removed from list
   - [ ] Verify persistence (refresh page → subscriptions still there)

5. **Logout**
   - [ ] Click "Logout" → session cleared, redirected to login page
   - [ ] Verify sessionStorage cleared in browser dev tools (F12)

---

## Cost Checklist

Before closing down, verify you don't leave expensive resources running:

- [ ] All EC2 instances **stopped** or **terminated**
- [ ] All ALBs **deleted**
- [ ] All ECS services **deleted**
- [ ] ECS cluster (empty) **deleted**
- [ ] CloudFront distributions **disabled/deleted** (if created)
- [ ] Lambda stack **deleted** (if deployed)
- [ ] S3 frontend buckets **deleted**
- [ ] NAT Gateways **deleted** (check VPC → NAT Gateways)
- [ ] Stale security groups **deleted**
- [ ] Old ECR images **cleaned up** (keep latest for next session)

---

## Quick Reference: Test Accounts

| Email | Password | User Name |
|---|---|---|
| s41396730@student.rmit.edu.au | 012345 | TestUser1 |
| s3816088@student.rmit.edu.au | 012345 | TestUser2 |
| s3816089@student.rmit.edu.au | 012345 | TestUser3 |

*(These are pre-populated by `q1_create_login.py`)*

---

## Troubleshooting

**Frontend won't connect to backend:**
- [ ] Check browser console (F12) for CORS errors or 404/500s
- [ ] Verify backend `/health` endpoint responds with `{"status": "ok"}`
- [ ] Verify `apiBaseUrl` in `frontend/config.js` matches deployed backend URL
- [ ] If using S3 frontend, verify S3 bucket policy allows `s3:GetObject` for `*`

**Login fails with "Internal Server Error":**
- [ ] Check backend logs (CloudWatch for ECS/Lambda, SSH for EC2)
- [ ] Verify DynamoDB `login` table exists and has test data
- [ ] Verify `LabRole` has DynamoDB permissions

**Songs don't load:**
- [ ] Verify `music` table has data: `aws dynamodb scan --table-name music --select COUNT`
- [ ] Verify image URLs are presigned correctly (no 403 errors in browser Network tab)

**High AWS costs at end of session:**
- [ ] Check Cost Explorer for running ALBs (biggest culprit)
- [ ] Verify all resources in Tear Down sections above were executed
- [ ] Use [Tag Editor](https://console.aws.amazon.com/resource-groups/tag-editor) to find forgotten resources
