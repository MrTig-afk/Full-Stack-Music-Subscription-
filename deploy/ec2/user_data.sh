#!/bin/bash
set -euxo pipefail

# Variables to customize before launching EC2
AWS_REGION="us-east-1"
ACCOUNT_ID="CHANGE_ME_ACCOUNT_ID"
REPOSITORY="music-subscription-api"
IMAGE_TAG="latest"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY}:${IMAGE_TAG}"

# Install Docker
yum update -y
amazon-linux-extras install docker -y || true
yum install -y docker
systemctl enable docker
systemctl start docker

# Login and pull image from ECR (LabRole instance profile should grant access)
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker pull "${IMAGE_URI}"

# Run backend on port 80
cat >/etc/music-subscription.env <<EOF
AWS_REGION=us-east-1
LOGIN_TABLE_NAME=login
MUSIC_TABLE_NAME=music
SUBSCRIPTIONS_TABLE_NAME=subscriptions
S3_BUCKET_NAME=CHANGE_ME_BUCKET
EOF

docker rm -f music-subscription-api || true
docker run -d \
  --name music-subscription-api \
  --restart unless-stopped \
  --env-file /etc/music-subscription.env \
  -p 80:80 \
  "${IMAGE_URI}"
