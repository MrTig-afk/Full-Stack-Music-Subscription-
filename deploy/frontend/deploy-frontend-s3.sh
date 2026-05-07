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
Usage: deploy-frontend-s3.sh [--bucket-suffix suffix] [--api-base-url url] [--region us-east-1]
EOF
}

BUCKET_SUFFIX="$(date +%Y%m%d-%H%M%S)"
API_BASE_URL=""
REGION="us-east-1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket-suffix)
      BUCKET_SUFFIX="$2"
      shift 2
      ;;
    --api-base-url)
      API_BASE_URL="$2"
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

command -v aws >/dev/null || fail "aws cli missing"
command -v sed >/dev/null || fail "sed missing"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BUCKET_NAME="music-subscription-frontend-${BUCKET_SUFFIX}"

log "frontend deploy start"
log "region=$REGION bucket=$BUCKET_NAME"

[[ -d "$FRONTEND_DIR" ]] || fail "frontend dir missing"
for file in index.html app.js styles.css config.js; do
  [[ -f "$FRONTEND_DIR/$file" ]] || fail "missing frontend/$file"
done

log "create bucket"
aws s3 mb "s3://${BUCKET_NAME}" --region "$REGION"

log "enable website hosting"
aws s3 website "s3://${BUCKET_NAME}" --index-document index.html --error-document index.html --region "$REGION"

log "disable block public access"
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false \
  --region "$REGION"

log "apply public read policy"
policy_json="$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
  }]
}
JSON
)"
aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy "$policy_json" --region "$REGION"

if [[ -n "$API_BASE_URL" ]]; then
  log "update frontend config api_base_url=$API_BASE_URL"
  sed -i.bak -E "s|apiBaseUrl: \"[^\"]*\"|apiBaseUrl: \"${API_BASE_URL}\"|" "$FRONTEND_DIR/config.js"
  rm -f "$FRONTEND_DIR/config.js.bak"
fi

log "sync frontend"
aws s3 sync "$FRONTEND_DIR" "s3://${BUCKET_NAME}" --exclude ".git/*" --exclude "*.md" --exclude "README.md" --exclude "CHANGELOG.md" --region "$REGION" --delete

log "frontend deploy done url=http://${BUCKET_NAME}.s3-website-${REGION}.amazonaws.com"