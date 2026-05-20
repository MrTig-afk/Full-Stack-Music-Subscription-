# Full Deployment Guide — EC2 + Lambda + ECS

Run the music subscription app on all three AWS targets from a clean Learner Lab.
Uses the `trial` branch. Tested end-to-end.

---

## The Two Sections You Need to Know

| Section | When to run |
|---|---|
| **One-Time Setup** (Phases 1–4) | First time only. Skip if tables/images/ECR already exist. |
| **Session Start** | Every time you open Learner Lab — credentials always rotate. |

---

## Session Start — Do This Every Time

Every time you open or resume the Learner Lab, credentials expire. This is the first thing you do, no exceptions.

### Step 1 — Paste credentials

In Learner Lab: click **AWS Details → Show** next to *AWS CLI*, copy all three lines.

```bash
cat > ~/.aws/credentials << 'EOF'
[default]
aws_access_key_id = PASTE_YOUR_KEY_HERE
aws_secret_access_key = PASTE_YOUR_SECRET_HERE
aws_session_token = PASTE_YOUR_TOKEN_HERE
EOF
```

> **Terminal tip:** The web terminal does not work well with heredocs. If the `EOF` line gets indented and the command hangs, press Ctrl+C and paste the three values manually into an existing `~/.aws/credentials` file using `nano`.

Verify it worked:

```bash
aws sts get-caller-identity
```

You should see your account ID and `LabRole`.

### Step 2 — Export variables (required for every command below)

```bash
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REPO_URL="https://github.com/MrTig-afk/Full-Stack-Music-Subscription-.git"
export IMAGES_BUCKET="msapp-images-${ACCOUNT_ID}"
export FRONTEND_BUCKET="msapp-frontend-${ACCOUNT_ID}"
export LAB_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/LabRole"
echo "Account: $ACCOUNT_ID"
```

---

## Phase 1 — Clone the Repository

```bash
rm -rf ~/music-app
git clone -b trial $REPO_URL music-app
cd music-app
```

---

## Phase 2 — Build and Push Docker Image to ECR

> **Skip this phase** if the ECR repository `msapp-api` already has an image (i.e., you built it in a previous session). Check: **ECR → Repositories → msapp-api** in the AWS Console.

The Learner Lab shell has no Docker access, so we use a temporary builder EC2.

### 2a — Create ECR repository

```bash
aws ecr create-repository --repository-name msapp-api --region us-east-1
```

`RepositoryAlreadyExistsException` is fine — move on.

### 2b — Launch the builder EC2

```bash
bash deploy/builder/launch_builder.sh
```

Note the **instance ID** and **security group ID** from the output. Wait **2 minutes** for the instance to boot and Docker to install.

### 2c — Connect to the builder

1. Go to **EC2 → Instances** in the AWS Console
2. Select the builder instance
3. Click **Connect → Session Manager → Connect**

> Do not use the CLI SSM plugin — the Learner Lab shell does not have it. Use the browser-based Session Manager only.

### 2d — Build and push inside the builder

```bash
cd ~
git clone -b trial https://github.com/MrTig-afk/Full-Stack-Music-Subscription-.git music-app
cd music-app
sudo bash build_and_push.sh
```

This takes about 3–4 minutes. You should see `latest: digest: sha256:...` at the end.

If you get `repository does not exist`:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr create-repository --repository-name msapp-api --region us-east-1
sudo docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/msapp-api:latest
```

### 2e — Exit and terminate the builder

```bash
exit
```

Back in the Learner Lab shell (replace with your actual IDs from step 2b):

```bash
aws ec2 terminate-instances --instance-ids <BUILDER_INSTANCE_ID> --region us-east-1
aws ec2 delete-security-group --group-id <BUILDER_SG_ID> --region us-east-1
```

> If the security group delete fails with `DependencyViolation`, wait 2 minutes for the instance to terminate fully, then retry.

---

## Phase 3 — Create DynamoDB Tables and Upload S3 Images

> **Skip this phase** if the tables `login`, `music`, `subscriptions` already exist and `msapp-images-<ACCOUNT_ID>` is populated. Check: **DynamoDB → Tables** and **S3 → Buckets** in the AWS Console.

```bash
cd ~/music-app
pip install boto3 requests tqdm
python q1_create_login.py
python q2_create_music.py
python q3_load_music.py
python create_subscriptions_table.py
S3_BUCKET_NAME=$IMAGES_BUCKET python q4_S3_images.py
```

`q4_S3_images.py` downloads 137 artist images and uploads them to S3. Takes about 2–3 minutes.

---

## Phase 4 — Create Frontend S3 Bucket

> **Skip this phase** if `msapp-frontend-<ACCOUNT_ID>` already exists.

```bash
aws s3 mb s3://${FRONTEND_BUCKET} --region us-east-1
aws s3 website s3://${FRONTEND_BUCKET} --index-document index.html --error-document index.html
CONF="BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
aws s3api put-public-access-block --bucket ${FRONTEND_BUCKET} --public-access-block-configuration "$CONF"
```

Set public read policy (run each line separately — the terminal splits long lines):

```bash
P1='{"Version":"2012-10-17"'
P2=',"Statement":[{"Effect":"Allow"'
P3=',"Principal":"*","Action":"s3:GetObject"'
P4=',"Resource":"arn:aws:s3:::'"${FRONTEND_BUCKET}"'/*"}]}'
echo "${P1}${P2}${P3}${P4}" > /tmp/p.json
aws s3api put-bucket-policy --bucket ${FRONTEND_BUCKET} --policy file:///tmp/p.json
```

---

## Target A — EC2

### A1 — Launch the app EC2 instance

1. Go to **EC2 → Launch Instance**:

| Field | Value |
|---|---|
| Name | `msapp-ec2` |
| AMI | Amazon Linux 2023 (default) |
| Instance type | `t2.micro` |
| Key pair | No key pair needed |
| Security group | Create new → add rule: **HTTP, port 80, source `0.0.0.0/0`** |
| IAM Instance Profile | `LabInstanceProfile` |
| User data | Paste full contents of `deploy/ec2/user_data.sh` |

Get the user data:

```bash
cat ~/music-app/deploy/ec2/user_data.sh
```

Copy the full output, paste it into the **User data** field when launching.

### A2 — If you forgot port 80

Find the security group ID: **EC2 → Instances → Security tab**, then:

```bash
aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 80 --cidr 0.0.0.0/0 --region us-east-1
```

### A3 — Get the public DNS

```bash
aws ec2 describe-instances --instance-ids <INSTANCE_ID> --query 'Reservations[0].Instances[0].PublicDnsName' --output text --region us-east-1
```

Save this as `EC2_DNS`.

### A4 — Test the backend (wait 3–4 minutes first)

```bash
curl http://<EC2_DNS>/health
```

Expected: `{"status":"ok"}`

### A5 — Deploy frontend

```bash
OLD=$(grep apiBaseUrl ~/music-app/frontend/config.js | grep -o '"[^"]*"' | tail -1 | tr -d '"')
NEW="http://<EC2_DNS>"
sed -i "s|${OLD}|${NEW}|" ~/music-app/frontend/config.js
aws s3 sync ~/music-app/frontend/ s3://${FRONTEND_BUCKET}/
```

### A6 — Access the app

```
http://msapp-frontend-<ACCOUNT_ID>.s3-website-us-east-1.amazonaws.com
```

---

## Target B — Lambda

### B1 — Install SAM CLI

```bash
pip install --user aws-sam-cli
export PATH=$PATH:~/.local/bin
sam --version
```

Expected: `SAM CLI, version 1.x.x`

> Add to `~/.bashrc` so you don't need to re-run the export each session:
> ```bash
> echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
> ```

### B2 — Deploy

```bash
cd ~/music-app
bash deploy/lambda/deploy-lambda.sh --lab-role-arn $LAB_ROLE_ARN --s3-bucket-name $IMAGES_BUCKET
```

Takes 2–3 minutes. At the end you'll see:

```
Successfully created/updated stack - msapp-lambda in us-east-1
[...] lambda deploy done api_url=https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod/
```

Copy the `api_url` — that's your Lambda API endpoint. It never changes.

### B3 — Test

```bash
curl https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod/health
```

Expected: `{"status":"ok"}`

### B4 — Deploy frontend

```bash
OLD=$(grep apiBaseUrl ~/music-app/frontend/config.js | grep -o '"[^"]*"' | tail -1 | tr -d '"')
NEW="https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod"
sed -i "s|${OLD}|${NEW}|" ~/music-app/frontend/config.js
aws s3 sync ~/music-app/frontend/ s3://${FRONTEND_BUCKET}/
```

### B5 — Access the app

```
http://msapp-frontend-<ACCOUNT_ID>.s3-website-us-east-1.amazonaws.com
```

---

## Target C — ECS Fargate

### C1 — Create ECS cluster and log group

```bash
aws ecs create-cluster --cluster-name msapp-cluster --region us-east-1
aws logs create-log-group --log-group-name /ecs/msapp-api --region us-east-1
```

`ClusterAlreadyExistsException` or `ResourceAlreadyExistsException` are fine.

### C2 — Render and register the task definition

```bash
IMAGE="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/msapp-api:latest"
ROLE="arn:aws:iam::${ACCOUNT_ID}:role/LabRole"
BUCKET="msapp-images-${ACCOUNT_ID}"

cp deploy/ecs/task-definition.json /tmp/task-def.json
sed -i "s|REPLACE_WITH_ECR_IMAGE_URI|${IMAGE}|" /tmp/task-def.json
sed -i "s|REPLACE_WITH_LABROLE_ARN|${ROLE}|g" /tmp/task-def.json
sed -i "s|REPLACE_WITH_BUCKET|${BUCKET}|" /tmp/task-def.json
```

Register it:

```bash
aws ecs register-task-definition --cli-input-json file:///tmp/task-def.json --region us-east-1 --query 'taskDefinition.taskDefinitionArn' --output text
```

Note the revision number at the end (e.g. `msapp-api:1`). Use that number in C4.

### C3 — Set up networking

```bash
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text --region us-east-1)
SUBNET_ID=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=${VPC_ID} --query 'Subnets[0].SubnetId' --output text --region us-east-1)
SG_ID=$(aws ec2 create-security-group --group-name msapp-ecs-sg --description "msapp ECS" --vpc-id ${VPC_ID} --query GroupId --output text --region us-east-1)
aws ec2 authorize-security-group-ingress --group-id ${SG_ID} --protocol tcp --port 80 --cidr 0.0.0.0/0 --region us-east-1
```

Write network config to file:

```bash
N1='{"awsvpcConfiguration":{"subnets":["'
N2='"],"securityGroups":["'
N3='"],"assignPublicIp":"ENABLED"}}'
echo "${N1}${SUBNET_ID}${N2}${SG_ID}${N3}" > /tmp/netconfig.json
cat /tmp/netconfig.json
```

### C4 — Create the ECS service

> Replace `msapp-api:1` with your actual revision number if it differs.

```bash
L1="aws ecs create-service --cluster msapp-cluster"
L2=" --service-name msapp-service --task-definition msapp-api:1"
L3=" --desired-count 1 --launch-type FARGATE"
L4=" --network-configuration file:///tmp/netconfig.json"
L5=" --region us-east-1"
echo "${L1}${L2}${L3}${L4}${L5}" > /tmp/cs.sh
bash /tmp/cs.sh
```

### C5 — Get the public IP

Wait about 2 minutes, then find the IP via the AWS Console:

1. Go to **ECS → Clusters → msapp-cluster → Tasks**
2. Click the running task
3. Find **Public IP** in the network section

Test:

```bash
curl http://<ECS_PUBLIC_IP>/health
```

Expected: `{"status":"ok"}`

> The ECS task IP is temporary — it changes every time the task is stopped and restarted.

### C6 — Deploy frontend

```bash
OLD=$(grep apiBaseUrl ~/music-app/frontend/config.js | grep -o '"[^"]*"' | tail -1 | tr -d '"')
NEW="http://<ECS_PUBLIC_IP>"
sed -i "s|${OLD}|${NEW}|" ~/music-app/frontend/config.js
aws s3 sync ~/music-app/frontend/ s3://${FRONTEND_BUCKET}/
```

### C7 — Access the app

```
http://msapp-frontend-<ACCOUNT_ID>.s3-website-us-east-1.amazonaws.com
```

---

## Resuming After the Lab Timer Expires

**Credentials expire. Everything else persists.** No data, tables, images, or infrastructure is lost.

### Step 1 — Always: paste new credentials and re-export variables

```bash
cat > ~/.aws/credentials << 'EOF'
[default]
aws_access_key_id = PASTE_YOUR_KEY_HERE
aws_secret_access_key = PASTE_YOUR_SECRET_HERE
aws_session_token = PASTE_YOUR_TOKEN_HERE
EOF
```

```bash
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export FRONTEND_BUCKET="msapp-frontend-${ACCOUNT_ID}"
export IMAGES_BUCKET="msapp-images-${ACCOUNT_ID}"
export LAB_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/LabRole"
echo "Account: $ACCOUNT_ID"
```

---

### Step 2A — Resume EC2

#### Find the instance — list all and pick the running one

```bash
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicDnsName]' --output table --region us-east-1
```

You'll see a table like:
```
| i-04fb9396f78293dd5 | running | ec2-34-228-39-167.compute-1.amazonaws.com |
```

Set the values from what you see (replace with your actual output):

```bash
INST="i-XXXXXXXXXXXXXXXXX"
EC2_DNS="ec2-XX-XX-XX-XX.compute-1.amazonaws.com"
```

- If state is `running` → skip to "Check if frontend needs updating" below
- If state is `stopped` → start it first:

```bash
aws ec2 start-instances --instance-ids $INST --region us-east-1
aws ec2 wait instance-running --instance-ids $INST --region us-east-1
```

Then get the new DNS (it changes when an instance restarts):

```bash
EC2_DNS=$(aws ec2 describe-instances --instance-ids $INST --query 'Reservations[0].Instances[0].PublicDnsName' --output text --region us-east-1)
echo $EC2_DNS
```

#### Test the backend is up

```bash
curl http://${EC2_DNS}/health
```

Expected: `{"status":"ok"}`

#### Check if frontend needs updating

```bash
grep apiBaseUrl ~/music-app/frontend/config.js
```

If the active `apiBaseUrl` line (the one without `*`) does **not** match `http://${EC2_DNS}`, update it:

```bash
OLD=$(grep apiBaseUrl ~/music-app/frontend/config.js | grep -o '"[^"]*"' | tail -1 | tr -d '"')
NEW="http://${EC2_DNS}"
sed -i "s|${OLD}|${NEW}|" ~/music-app/frontend/config.js
aws s3 sync ~/music-app/frontend/ s3://${FRONTEND_BUCKET}/
```

---

### Step 2B — Resume Lambda

Lambda API Gateway URL is permanent — it never changes between sessions.

```bash
aws cloudformation describe-stacks --stack-name msapp-lambda --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text
```

That's it. If the frontend was last pointed at Lambda, it still works — nothing to update.

---

### Step 2C — Resume ECS

The ECS cluster and service persist, but **the task gets a new public IP every time it restarts**.

#### Check if a task is running

```bash
aws ecs list-tasks --cluster msapp-cluster --region us-east-1
```

- If you see a task ARN → it's running, proceed to get the IP.
- If the list is empty → the service will auto-launch a task. Wait ~2 minutes then re-run the command.

#### Get the current task IP via CLI

```bash
TASK=$(aws ecs list-tasks --cluster msapp-cluster --region us-east-1 --query 'taskArns[0]' --output text)
echo $TASK
```

```bash
ENI=$(aws ecs describe-tasks --cluster msapp-cluster --tasks $TASK --region us-east-1 --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
echo $ENI
```

```bash
ECS_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region us-east-1)
echo $ECS_IP
```

> Alternatively: **ECS → Clusters → msapp-cluster → Tasks → click task → Public IP** in the console.

#### Update the frontend

```bash
OLD=$(grep apiBaseUrl ~/music-app/frontend/config.js | grep -o '"[^"]*"' | tail -1 | tr -d '"')
NEW="http://${ECS_IP}"
sed -i "s|${OLD}|${NEW}|" ~/music-app/frontend/config.js
aws s3 sync ~/music-app/frontend/ s3://${FRONTEND_BUCKET}/
```

Test:

```bash
curl http://${ECS_IP}/health
```

---

### What a full Lab Reset means (the "Reset" button)

If anyone clicks **Reset** in Learner Lab — that wipes the entire AWS account. Everything is gone: ECR, S3, DynamoDB, EC2, ECS, Lambda, CloudFormation stacks. You restart from Phase 1. **Do not click Reset unless you intend a full wipe.**

### Quick reference: what persists vs what changes

| Resource | After timer expires | After task/instance restart |
|---|---|---|
| AWS credentials | **Expire — re-paste** | **Expire — re-paste** |
| ECR image | Persists | Persists |
| DynamoDB tables | Persists | Persists |
| S3 buckets | Persists | Persists |
| Lambda API URL | Persists — same URL forever | Persists |
| EC2 public DNS | Same if instance kept running | **Changes if instance stopped/started** |
| ECS task public IP | **Changes on every task restart** | **Changes on every task restart** |

---

## Troubleshooting

**Heredoc hangs in web terminal**
The terminal indents the `EOF` line and the command never closes. Press Ctrl+C. Use the P1/P2/P3 variable concatenation pattern shown in Phase 4 instead.

**`sam: command not found`**
Run: `export PATH=$PATH:~/.local/bin`

**`InvalidParameterException` on ECS service create**
Check actual task definition revision: `aws ecs list-task-definitions --region us-east-1 --query 'taskDefinitionArns[-1]' --output text`
Update `msapp-api:1` in L2 to match.

**ECS task stuck in PENDING**
Check CloudWatch Logs: **CloudWatch → Log groups → /ecs/msapp-api**. Most likely cause: ECR image URI mismatch. Verify with `cat /tmp/task-def.json`.

**EC2 health check fails after 5+ minutes**
Go to **EC2 → Instances → select instance → Actions → Monitor and troubleshoot → Get system log**. Look for Docker pull errors.

**Lambda returns 5xx**
Check: **CloudWatch → Log groups → `/aws/lambda/msapp-lambda-BackendFunction-XXXX`**

**Frontend shows old data / wrong API**
```bash
grep apiBaseUrl ~/music-app/frontend/config.js
```
Re-run the `sed` + `aws s3 sync` for the current target.

**Security group `msapp-ecs-sg` already exists**
```bash
aws ec2 describe-security-groups --filters Name=group-name,Values=msapp-ecs-sg --query 'SecurityGroups[0].GroupId' --output text --region us-east-1
```
Use that ID as `SG_ID` and skip the create command.

---

## AWS Resource Reference

| Resource | Name | Persists after timer? |
|---|---|---|
| ECR Repository | `msapp-api` | Yes |
| Docker Image | `msapp-api:latest` | Yes |
| DynamoDB Tables | `login`, `music`, `subscriptions` | Yes |
| S3 Images Bucket | `msapp-images-<ACCOUNT_ID>` | Yes |
| S3 Frontend Bucket | `msapp-frontend-<ACCOUNT_ID>` | Yes |
| EC2 Instance | `msapp-ec2` | Yes (if not terminated) |
| Lambda Stack | `msapp-lambda` | Yes |
| API Gateway | `msapp-rest-api` | Yes (same URL always) |
| ECS Cluster | `msapp-cluster` | Yes |
| ECS Service | `msapp-service` | Yes |
| ECS Task Public IP | changes per task | **No — changes on restart** |

---

## Cleanup

Run only when done with the assignment.

```bash
# ECS
aws ecs update-service --cluster msapp-cluster --service msapp-service --desired-count 0 --region us-east-1
aws ecs delete-service --cluster msapp-cluster --service msapp-service --region us-east-1
aws ecs delete-cluster --cluster msapp-cluster --region us-east-1

# Lambda
aws cloudformation delete-stack --stack-name msapp-lambda --region us-east-1

# EC2 — terminate from console or:
aws ec2 terminate-instances --instance-ids <INSTANCE_ID> --region us-east-1
```
