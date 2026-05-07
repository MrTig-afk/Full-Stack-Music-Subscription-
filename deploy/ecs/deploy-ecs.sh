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
Usage: deploy-ecs.sh --account-id <id> --cluster <name> --service <name> --lab-role-arn <arn> [--region us-east-1] [--repository music-subscription-api] [--bucket name]
EOF
}

ACCOUNT_ID=""
CLUSTER=""
SERVICE=""
LAB_ROLE_ARN=""
REGION="us-east-1"
REPOSITORY="music-subscription-api"
BUCKET="CHANGE_ME_BUCKET"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --account-id)
      ACCOUNT_ID="$2"
      shift 2
      ;;
    --cluster)
      CLUSTER="$2"
      shift 2
      ;;
    --service)
      SERVICE="$2"
      shift 2
      ;;
    --lab-role-arn)
      LAB_ROLE_ARN="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --repository)
      REPOSITORY="$2"
      shift 2
      ;;
    --bucket)
      BUCKET="$2"
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

[[ -n "$ACCOUNT_ID" && -n "$CLUSTER" && -n "$SERVICE" && -n "$LAB_ROLE_ARN" ]] || {
  usage
  fail "Missing required args"
}

command -v aws >/dev/null || fail "aws cli missing"
command -v docker >/dev/null || fail "docker missing"
TAG="$(date +%Y%m%d%H%M%S)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPOSITORY}:${TAG}"

log "ecs deploy start"
log "region=$REGION cluster=$CLUSTER service=$SERVICE repo=$REPOSITORY bucket=$BUCKET"

log "ensure ecr repo"
if ! aws ecr describe-repositories --repository-names "$REPOSITORY" --region "$REGION" >/dev/null 2>&1; then
  aws ecr create-repository --repository-name "$REPOSITORY" --region "$REGION" >/dev/null
fi

log "ecr login"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

log "docker build"
docker build -t "$ECR_URI" .

log "docker push"
docker push "$ECR_URI"

rendered_task_def="deploy/ecs/task-definition.rendered.json"
log "render task definition"
template_file="$ROOT_DIR/deploy/ecs/task-definition.json"
template_content="$(< "$template_file")"
template_content="${template_content//REPLACE_WITH_ECR_IMAGE_URI/$ECR_URI}"
template_content="${template_content//REPLACE_WITH_LABROLE_ARN/$LAB_ROLE_ARN}"
template_content="${template_content//REPLACE_WITH_BUCKET/$BUCKET}"
printf '%s' "$template_content" > "$rendered_task_def"

log "register task definition"
TASK_DEF_ARN="$(aws ecs register-task-definition --cli-input-json "file://${rendered_task_def}" --query taskDefinition.taskDefinitionArn --output text --region "$REGION")"

log "update service"
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --task-definition "$TASK_DEF_ARN" --force-new-deployment --region "$REGION" >/dev/null

log "ecs deploy done task_def=$TASK_DEF_ARN image=$ECR_URI"