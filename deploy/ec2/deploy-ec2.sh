#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat <<'EOF'
Usage: deploy-ec2.sh --account-id <id> [--bucket name] [--repository music-subscription-api] [--region us-east-1] [--instance-type t3.small]
EOF
}

ACCOUNT_ID=""
BUCKET="CHANGE_ME_BUCKET"
REPOSITORY="msapp-api"
REGION="us-east-1"
INSTANCE_TYPE="t3.small"
ROLE_NAME="LabInstanceProfile"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --account-id)
      ACCOUNT_ID="$2"
      shift 2
      ;;
    --bucket)
      BUCKET="$2"
      shift 2
      ;;
    --repository)
      REPOSITORY="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --instance-type)
      INSTANCE_TYPE="$2"
      shift 2
      ;;
    --role-name)
      ROLE_NAME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown arg: $1"
      ;;
  esac
done

[[ -n "$ACCOUNT_ID" ]] || { usage; fail "Missing --account-id"; }
command -v aws >/dev/null || fail "aws cli missing"

TAG="latest"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPOSITORY}:${TAG}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE_FILE="$ROOT_DIR/deploy/ec2/user_data.sh"

log "ec2 deploy start"
log "region=$REGION image=$IMAGE_URI bucket=$BUCKET instance_type=$INSTANCE_TYPE"

AMI_ID="$(aws ssm get-parameters --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64 --region "$REGION" --query 'Parameters[0].Value' --output text)"
VPC_ID="$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)"
SUBNET_ID="$(aws ec2 describe-subnets --region "$REGION" --filters Name=vpc-id,Values="$VPC_ID" --query 'Subnets[0].SubnetId' --output text)"

SG_ID="$(aws ec2 create-security-group --region "$REGION" --group-name "msapp-ec2-$(date +%s)" --description "msapp ec2 backend" --vpc-id "$VPC_ID" --query GroupId --output text)"
aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null

rendered_user_data="$(mktemp)"
trap 'rm -f "$rendered_user_data"' EXIT

user_data_content="$(< "$TEMPLATE_FILE")"
user_data_content="${user_data_content//CHANGE_ME_ACCOUNT_ID/$ACCOUNT_ID}"
user_data_content="${user_data_content//CHANGE_ME_BUCKET/$BUCKET}"
user_data_content="${user_data_content//CHANGE_ME_IMAGE_TAG/$TAG}"
printf '%s' "$user_data_content" > "$rendered_user_data"

INSTANCE_ID="$(aws ec2 run-instances \
  --region "$REGION" \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --iam-instance-profile Name="$ROLE_NAME" \
  --subnet-id "$SUBNET_ID" \
  --security-group-ids "$SG_ID" \
  --user-data "file://$rendered_user_data" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=msapp-ec2-backend}]' \
  --query 'Instances[0].InstanceId' \
  --output text)"

log "wait for instance id=$INSTANCE_ID"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

PUBLIC_DNS="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$REGION" --query 'Reservations[0].Instances[0].PublicDnsName' --output text)"
log "ec2 deploy done instance_id=$INSTANCE_ID public_dns=$PUBLIC_DNS health=http://${PUBLIC_DNS}/health"