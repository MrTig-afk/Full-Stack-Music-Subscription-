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
Usage: deploy-apigw-ec2.sh --backend-base-url <url> [--region us-east-1] [--stack-name music-subscription-apigw-ec2] [--stage-name prod]
EOF
}

BACKEND_BASE_URL=""
REGION="us-east-1"
STACK_NAME="msapp-apigw-ec2"
STAGE_NAME="prod"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-base-url)
      BACKEND_BASE_URL="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --stack-name)
      STACK_NAME="$2"
      shift 2
      ;;
    --stage-name)
      STAGE_NAME="$2"
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

[[ -n "$BACKEND_BASE_URL" ]] || { usage; fail "Missing --backend-base-url"; }
command -v aws >/dev/null || fail "aws cli missing"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE_FILE="$ROOT_DIR/deploy/apigw/ec2-rest-proxy.yaml"

log "apigw ec2 deploy start"
log "region=$REGION stack=$STACK_NAME stage=$STAGE_NAME backend=$BACKEND_BASE_URL"

aws cloudformation deploy \
  --template-file "$TEMPLATE_FILE" \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --parameter-overrides BackendBaseUrl="$BACKEND_BASE_URL" StageName="$STAGE_NAME"

API_URL="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)"
log "apigw ec2 deploy done api_url=$API_URL"