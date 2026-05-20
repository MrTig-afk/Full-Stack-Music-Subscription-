param(
  [Parameter(Mandatory = $true)] [string]$AccountId,
  [Parameter(Mandatory = $true)] [string]$Cluster,
  [Parameter(Mandatory = $true)] [string]$Service,
  [Parameter(Mandatory = $true)] [string]$LabRoleArn,
  [string]$Region = "us-east-1",
  [string]$Repository = "msapp-api",
  [string]$Bucket = "CHANGE_ME_BUCKET"
)

$ErrorActionPreference = "Stop"
$tag = (Get-Date -Format "yyyyMMddHHmmss")
$ecrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$Repository`:$tag"

aws ecr describe-repositories --repository-names $Repository --region $Region 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  aws ecr create-repository --repository-name $Repository --region $Region | Out-Null
}

aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"
docker build -t $ecrUri .
docker push $ecrUri

$template = Get-Content -Raw "deploy/ecs/task-definition.json"
$template = $template.Replace("REPLACE_WITH_ECR_IMAGE_URI", $ecrUri)
$template = $template.Replace("REPLACE_WITH_LABROLE_ARN", $LabRoleArn)
$template = $template.Replace("REPLACE_WITH_BUCKET", $Bucket)
$outPath = "deploy/ecs/task-definition.rendered.json"
Set-Content -Path $outPath -Value $template

$taskDefArn = aws ecs register-task-definition --cli-input-json file://$outPath --query taskDefinition.taskDefinitionArn --output text --region $Region
aws ecs update-service --cluster $Cluster --service $Service --task-definition $taskDefArn --force-new-deployment --region $Region | Out-Null

Write-Host "Deployed image: $ecrUri"
Write-Host "Task definition: $taskDefArn"
