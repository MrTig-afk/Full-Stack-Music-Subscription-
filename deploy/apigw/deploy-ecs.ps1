param(
  [Parameter(Mandatory = $true)] [string]$BackendBaseUrl,
  [string]$Region = "us-east-1",
  [string]$StackName = "msapp-apigw-ecs",
  [string]$StageName = "prod"
)

$ErrorActionPreference = "Stop"

aws cloudformation deploy `
  --template-file deploy/apigw/ecs-rest-proxy.yaml `
  --stack-name $StackName `
  --region $Region `
  --parameter-overrides `
    BackendBaseUrl=$BackendBaseUrl `
    StageName=$StageName

$apiUrl = aws cloudformation describe-stacks `
  --stack-name $StackName `
  --region $Region `
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" `
  --output text

Write-Host "API Gateway URL: $apiUrl"
