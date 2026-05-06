#!/bin/bash
# PASTE THIS ENTIRE BLOC IN AWS CLOUDSHELL
# This script launches a temporary EC2 builder and waits for it,
# then provides the exact SSH/SSM command to enter the builder.
set -e

echo "🔎 Finding the latest Amazon Linux 2023 AMI ID..."
AMI_ID=$(aws ssm get-parameters --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64 --region us-east-1 --query 'Parameters[0].Value' --output text)

echo "🛠️ Creating a temporary Security Group for the builder..."
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
SG_ID=$(aws ec2 create-security-group \
  --group-name "docker-builder-sg-$(date +%s)" \
  --description "Security group for temporary Docker builder" \
  --vpc-id $VPC_ID \
  --query GroupId \
  --output text \
  --region us-east-1 || true) # Ignore if it somehow fails, though names are unique

# No ingress rules needed if we use SSM (Session Manager) to connect! No open ports needed!
# Which is highly secure.

echo "🚀 Launching the builder EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t3.small \
    --iam-instance-profile Name=LabInstanceProfile \
    --security-group-ids $SG_ID \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=music-image-builder}]' \
    --user-data file://deploy/builder/user_data_builder.sh \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region us-east-1)

echo "⏳ Waiting for instance $INSTANCE_ID to become running (takes about 30 seconds)..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region us-east-1

echo "✅ Instance $INSTANCE_ID is running!"
echo "🐳 The instance is currently installing Docker in the background (takes ~2 minutes)."
echo ""
echo "========================================================="
echo "   NEXT STEPS (Copy & Paste these into CloudShell):"
echo "========================================================="
echo ""
echo "# 1. Connect to the builder instance via Session Manager:"
echo "aws ssm start-session --target $INSTANCE_ID --region us-east-1"
echo ""
echo "# 2. Once inside the Session Manager shell, run the build script:"
echo "bash build_and_push.sh"
echo ""
echo "# 3. When finished, EXIT the instance and TERMINATE it:"
echo "exit"
echo "aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region us-east-1"
echo "aws ec2 delete-security-group --group-id $SG_ID --region us-east-1"
echo "========================================================="
