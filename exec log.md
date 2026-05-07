# 1. AWS LearnerLab CloudShell

## Install `mise` for python version management

```bash
curl https://mise.run | sh
touch ~/.bashrc
echo 'eval "$(mise activate bash)"' >> ~/.bashrc
source ~/.bashrc
```

## Install `uv` for tooling

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Set python 3.12 as global default

```bash
$ mise use -g python@3.12
$ which python
# something/something/.local/share/mise/installs/python/3.12/bin/python
```

## Clone Repo

```bash
git clone https://github.com/MrTig-afk/Full-Stack-Music-Subscription-.git music-app && cd music-app
```

```bash
uv sync --no-dev
```

## Create tables and upload music data

```bash
chmod +x reset_music_table.sh
./reset_music_table.sh
```

## Check tables

```bash
aws dynamodb list-tables --region us-east-1
aws dynamodb scan --table-name login --select COUNT --region us-east-1
aws dynamodb scan --table-name music --select COUNT --region us-east-1
aws dynamodb scan --table-name subscriptions --select COUNT --region us-east-1
```

## Edit q4_S3_images.py

Update the BUCKET_NAME to be something unique, but still lowercase and only having dashes `-` like `rmit-music-images-unique-myname`

For this, replace the end bit with your name in lowercase or something and paste in shell:

```bash
export S3_BUCKET_NAME=rmit-music-images-unique-myname
```

## Upload S3 images

```bash
uv run ./q4_S3_images.py
```

## Check S3 uploaded

aws s3 ls s3://(S3_BUCKET_NAME goes here)

# 2. EC2 instance shell for buliding and pushing docker image

Launch a EC2 instance with default settings, called "mybuilder" or something

After it is up and you are in the EC2 Shell

```bash
mkdir -p ~/.aws
```

## Edit this file

```bash
nano ~/.aws/credentials
```

## Paste AWS credentials from the Learner Lab's "AWS Details" into this file

Save and exit the file

## In the builder ec2 shell

```bash
dnf install -y git
git clone https://github.com/MrTig-afk/Full-Stack-Music-Subscription-.git music-app
cd music-app
```

```bash
chmod +x deploy/builder/user_data_builder.sh
sudo ./deploy/builder/user_data_builder.sh
```

## Save and exit the file

```bash
chmod +x ~/build_and_push.sh
~/build_and_push.sh
```

## Terminate the Instance

# 3. Cloudshell again

## Following deployment_guide.md steps for frontend - EC2 + nginx

New EC2 instance with specified parameters

Copy public ipv4 dns from instances list

# 4. Connect to the EC2 shell for frontend instance

## Install nginx

```bash
sudo dnf update -y
sudo dnf install -y nginx git

sudo systemctl start nginx
sudo systemctl enable nginx
```

## Clone repo here

```bash
git clone https://github.com/MrTig-afk/Full-Stack-Music-Subscription-.git music-app
```

## Add static frontend files to nginx for exposure

```bash
sudo cp music-app/frontend/* /usr/share/nginx/html/
sudo chown -R nginx:nginx /usr/share/nginx/html/
```

Leave this running, but store the public dns to open later and point to any backend

# 5. CloudShell again

set env vars

```bash
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export S3_BUCKET="rmit-music-images-unique-myname"
export REGION="us-east-1"
export BACKEND_PORT="80"
```

Use `echo` to get the value at any time

Open the dialog to create a new instance, with the specified settings from `deployment_guide.md`. Then, edit `deploy/ec2/user_data.sh` with the appropriate copied values, and paste the whole thing into the user data field when initializing the EC2 instance. Do not connect to the shell.

Wait for all status checks to pass after init.

Get the `public ipv4 dns` for this `backend ec2` from instances list.

Set `export EC2_PUBLIC_DNS=<value>` in the CloudShell (this is for backend)

```bash
curl -s http://$EC2_PUBLIC_DNS/health | jq .
# Expected: {"status":"ok"}
```

## Access the running frontend instance and point it to this backend

In the browser: `http://<EC2_FRONTEND_DNS>?apiBase=http://<EC2_BACKEND_DNS>`
Do your testing

## Stop backend EC2 afterwards if you want

# 6. CloudShell

## ECS deployment

## Create a ECS cluster in the Console as per deployment guide Step 2.2

### Make log group in cloudwatch

```bash
aws logs create-log-group --log-group-name /ecs/$TASK_DEFINITION --region $REGION
```

### Get and store VPC and the subnet IDs for the ECS cluster

```bash
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
SUBNET_IDS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID --query "Subnets[0:2].SubnetId" --output text)
```

### Create the security grp

```bash
SG_ID=$(aws ec2 create-security-group --group-name ecs-music-sg --description "ECS backend" --vpc-id $VPC_ID --query GroupId --output text --region $REGION)
```

### Then put default role in that group

```bash
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION
```

### app load balancer init (top of the lucidchart)

```bash
ALB_ARN=$(aws elbv2 create-load-balancer --name music-sub-alb --subnets $SUBNET_IDS --security-groups $SG_ID --scheme internet-facing --type application --query "LoadBalancers[0].LoadBalancerArn" --output text --region $REGION)
TG_ARN=$(aws elbv2 create-target-group --name music-sub-tg --protocol HTTP --port 80 --vpc-id $VPC_ID --target-type ip --health-check-path /health --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION)
aws elbv2 create-listener --load-balancer-arn $ALB_ARN --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TG_ARN --region $REGION
```

expect response of the form:

```json
{
    "Listeners": [
        {
            "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:660273085484:listener/app/music-sub-alb/42704d1e049303ef/46c90d99e341473d",
            "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:660273085484:loadbalancer/app/music-sub-alb/42704d1e049303ef",
            "Port": 80,
            "Protocol": "HTTP",
            "DefaultActions": [
                {
                    "Type": "forward",
                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:660273085484:targetgroup/music-sub-tg/8c8eafffd03da8ba",
                    "ForwardConfig": {
                        "TargetGroups": [
                            {
                                "TargetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:660273085484:targetgroup/music-sub-tg/8c8eafffd03da8ba",
                                "Weight": 1
                            }
                        ],
                        "TargetGroupStickinessConfig": {
                            "Enabled": false
                        }
                    }
                }
            ]
        }
    ]
}
```

## Store the DNS of this load balancer

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query "LoadBalancers[0].DNSName" --output text --region $REGION)

# print it out, copy into notepad
echo $ALB_DNS
```

# 7. Connecto to the Docker Image Builder EC2 from earlier

```bash
cd ~/music-app
bash deploy/ecs/deploy-ecs.sh \
  --account-id "$ACCOUNT_ID" \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --lab-role-arn "arn:aws:iam::$ACCOUNT_ID:role/LabRole" \
  --bucket "$S3_BUCKET" \
  --region "$REGION"
```
