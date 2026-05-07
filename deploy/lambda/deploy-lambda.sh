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
Usage: deploy-lambda.sh --lab-role-arn <arn> --s3-bucket-name <bucket> [--stack-name music-subscription-lambda] [--region us-east-1]
EOF
}

LAB_ROLE_ARN=""
S3_BUCKET_NAME=""
STACK_NAME="music-subscription-lambda"
REGION="us-east-1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lab-role-arn)
      LAB_ROLE_ARN="$2"
      shift 2
      ;;
    --s3-bucket-name)
      S3_BUCKET_NAME="$2"
      shift 2
      ;;
    --stack-name)
      STACK_NAME="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
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

[[ -n "$LAB_ROLE_ARN" && -n "$S3_BUCKET_NAME" ]] || { usage; fail "Missing required args"; }
command -v sam >/dev/null || fail "sam cli missing"
command -v aws >/dev/null || fail "aws cli missing"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE_FILE="$ROOT_DIR/deploy/lambda/template.yaml"

log "lambda deploy start"
log "region=$REGION stack=$STACK_NAME bucket=$S3_BUCKET_NAME"

sam build -t "$TEMPLATE_FILE"

sam deploy \
  --template-file "$ROOT_DIR/.aws-sam/build/template.yaml" \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides LabRoleArn="$LAB_ROLE_ARN" S3BucketName="$S3_BUCKET_NAME"

API_URL="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)"
log "lambda deploy done api_url=$API_URL"