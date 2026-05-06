#!/bin/bash
# user_data_builder.sh — Bootstraps an Amazon Linux 2023 EC2 instance with Docker
# and creates a helper script to build/push exactly what we need.

exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Installing Docker..."
dnf update -y
dnf install -y docker git
systemctl enable docker
systemctl start docker
usermod -aG docker ssm-user
usermod -aG docker ec2-user

# Make sure ssm-user environment can pick up docker group (often requires newgrp, handled below or with a relogin)

echo "Creating build script in ssm-user home..."
cat << 'EOF' > /home/ssm-user/build_and_push.sh
#!/bin/bash
# PASTE IN SSM: This builds the Docker image and pushes it to ECR
set -e

# Run with newgrp if group membership not registered yet
if ! groups | grep -q docker; then
  echo "Applying docker group permissions..."
  exec sg docker -c "bash $0"
  exit
fi

echo "1. Getting AWS Account Info..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
REPO="music-subscription-api"

# Make sure repo actually exists
aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" >/dev/null 2>&1 || aws ecr create-repository --repository-name "$REPO" --region "$REGION" >/dev/null

echo "2. Authenticating Docker to ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

echo "3. Cloning Repository (Using HTTPS for public or prompt user to edit if private/ssh)..."
# We could ask for the URL, OR since it's the Learner Lab, assume they just clone the correct branch from their repo.
echo "⚠️  NOTE: Please enter your repository URL to clone:"
read -p "Repo URL: " REPO_URL
if [ -z "$REPO_URL" ]; then
    echo "No URL provided, exiting."
    exit 1
fi

rm -rf music-app
git clone "$REPO_URL" music-app
cd music-app

echo "4. Building Docker image..."
docker build -t music-subscription-api:latest .

echo "5. Tagging Image..."
docker tag music-subscription-api:latest "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest"

echo "6. Pushing to ECR..."
docker push "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest"

echo "✅ Success! Image pushed! You can now exit and terminate this builder instance."
EOF

chown ssm-user:ssm-user /home/ssm-user/build_and_push.sh
chmod +x /home/ssm-user/build_and_push.sh

echo "User data script completed setup."
