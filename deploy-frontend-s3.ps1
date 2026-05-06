#!/usr/bin/env powershell
<#
.SYNOPSIS
    Deploy Music Subscription frontend to AWS S3 static website hosting.

.DESCRIPTION
    This script automates frontend deployment to S3 including:
    - S3 bucket creation
    - Static website hosting configuration
    - Public read access policy
    - Frontend file upload
    - Configuration URL display

.PARAMETER BucketNameSuffix
    Optional suffix for bucket name (default: auto-generated timestamp)

.PARAMETER ApiBaseUrl
    Backend API URL (default: from frontend/config.js)

.PARAMETER Region
    AWS region (default: us-east-1)

.EXAMPLE
    .\deploy-frontend-s3.ps1 -ApiBaseUrl "http://ec2-XX-XX-XX-XX.compute-1.amazonaws.com"

.EXAMPLE
    .\deploy-frontend-s3.ps1 -ApiBaseUrl "https://api-id.execute-api.us-east-1.amazonaws.com/prod"
#>

param(
    [string]$BucketNameSuffix = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [string]$ApiBaseUrl = "",
    [string]$Region = "us-east-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "🚀 Music Subscription Frontend Deployment to S3" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Validate environment
# ============================================================================

Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

# Check AWS CLI
try {
    $null = aws sts get-caller-identity --region $Region --output text --query Account
    Write-Host "  ✓ AWS CLI configured" -ForegroundColor Green
} catch {
    Write-Host "  ✗ AWS CLI not configured or Learner Lab session expired" -ForegroundColor Red
    exit 1
}

# Check frontend directory exists
if (-not (Test-Path "./frontend")) {
    Write-Host "  ✗ frontend/ directory not found" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ frontend/ directory exists" -ForegroundColor Green

# Check key frontend files
@("index.html", "app.js", "styles.css", "config.js") | ForEach-Object {
    if (-not (Test-Path "./frontend/$_")) {
        Write-Host "  ✗ frontend/$_ not found" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  ✓ All frontend files present" -ForegroundColor Green

Write-Host ""

# ============================================================================
# Create S3 bucket
# ============================================================================

$BucketName = "music-subscription-frontend-$BucketNameSuffix"
Write-Host "🪣 Creating S3 bucket..." -ForegroundColor Yellow
Write-Host "   Bucket name: $BucketName"

try {
    aws s3 mb "s3://$BucketName" --region $Region 2>&1 | ForEach-Object {
        if ($_ -match "error|Error") {
            Write-Host "  ✗ Failed to create bucket: $_" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "  ✓ Bucket created" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to create bucket: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Enable static website hosting
# ============================================================================

Write-Host ""
Write-Host "🌐 Configuring static website hosting..." -ForegroundColor Yellow

try {
    aws s3 website "s3://$BucketName" `
        --index-document index.html `
        --error-document index.html `
        --region $Region
    Write-Host "  ✓ Static website hosting enabled" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to enable static website hosting: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Disable block-all-public-access
# ============================================================================

Write-Host ""
Write-Host "🔐 Updating public access settings..." -ForegroundColor Yellow

try {
    aws s3api put-public-access-block `
        --bucket $BucketName `
        --public-access-block-configuration `
        BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false `
        --region $Region
    Write-Host "  ✓ Block public access disabled" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to disable block public access: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Apply public read bucket policy
# ============================================================================

Write-Host ""
Write-Host "📋 Applying bucket policy..." -ForegroundColor Yellow

$Policy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Principal = "*"
            Action = "s3:GetObject"
            Resource = "arn:aws:s3:::$BucketName/*"
        }
    )
} | ConvertTo-Json

try {
    $Policy | aws s3api put-bucket-policy `
        --bucket $BucketName `
        --policy file:///dev/stdin `
        --region $Region 2>&1 | ForEach-Object {
        if ($_ -match "error|Error") {
            Write-Host "  ✗ Failed to apply policy: $_" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "  ✓ Public read policy applied" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to apply policy: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Update config.js if API URL provided
# ============================================================================

if ($ApiBaseUrl) {
    Write-Host ""
    Write-Host "⚙️  Updating frontend config..." -ForegroundColor Yellow
    Write-Host "   API Base URL: $ApiBaseUrl"
    
    $ConfigPath = "./frontend/config.js"
    $ConfigContent = Get-Content $ConfigPath -Raw
    
    # Escape backslashes and quotes for regex
    $EscapedUrl = [regex]::Escape($ApiBaseUrl)
    
    # Replace the apiBaseUrl value
    $UpdatedContent = $ConfigContent -replace `
        '(apiBaseUrl:\s*")[^"]*(")', `
        "`$1$ApiBaseUrl`$2"
    
    Set-Content -Path $ConfigPath -Value $UpdatedContent
    Write-Host "  ✓ config.js updated" -ForegroundColor Green
}

# ============================================================================
# Upload frontend files to S3
# ============================================================================

Write-Host ""
Write-Host "📤 Uploading frontend files to S3..." -ForegroundColor Yellow

try {
    aws s3 sync ./frontend "s3://$BucketName" `
        --exclude ".git/*" `
        --exclude "*.md" `
        --exclude "README.md" `
        --exclude "CHANGELOG.md" `
        --region $Region `
        --delete
    Write-Host "  ✓ Frontend files uploaded" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to upload files: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Display deployment summary
# ============================================================================

Write-Host ""
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$WebsiteUrl = "http://$BucketName.s3-website-$Region.amazonaws.com"
Write-Host "Frontend URL:" -ForegroundColor Cyan
Write-Host "  $WebsiteUrl" -ForegroundColor Yellow
Write-Host ""

Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Bucket Name: $BucketName" -ForegroundColor Gray
Write-Host "  Region: $Region" -ForegroundColor Gray
if ($ApiBaseUrl) {
    Write-Host "  API Base URL: $ApiBaseUrl" -ForegroundColor Gray
}
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open the frontend URL in your browser" -ForegroundColor Gray
Write-Host "  2. Test registration, login, queries, and subscriptions" -ForegroundColor Gray
Write-Host "  3. Check browser console (F12) for any errors" -ForegroundColor Gray
Write-Host ""

Write-Host "Cleanup:" -ForegroundColor Cyan
Write-Host "  To delete this deployment, run:" -ForegroundColor Gray
Write-Host "    aws s3 rm s3://$BucketName --recursive" -ForegroundColor Gray
Write-Host "    aws s3 rb s3://$BucketName" -ForegroundColor Gray
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
