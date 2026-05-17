#!/bin/bash

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

REPO_NAME="music-subscription-api"

IMAGE_URI=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest

echo "Logging into ECR..."

aws ecr get-login-password --region $REGION | \
docker login --username AWS --password-stdin \
$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

echo "Building Docker image..."

docker build -t music_subscription_api .

echo "Tagging image..."

docker tag music_subscription_api:latest $IMAGE_URI

echo "Pushing image to ECR..."

docker push $IMAGE_URI

echo "Done!"