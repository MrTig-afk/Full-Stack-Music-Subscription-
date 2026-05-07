#!/bin/bash
# reset_music_table.sh — Drops all DynamoDB tables and reruns all 4 DDL scripts
# cleanly from scratch. Run from the project root in AWS CloudShell.
set -e

REGION="us-east-1"
TABLES=("login" "music" "subscriptions")

echo "==> Deleting tables in parallel..."
for TABLE in "${TABLES[@]}"; do
    if aws dynamodb describe-table --table-name "$TABLE" --region "$REGION" &>/dev/null; then
        echo "    Deleting '$TABLE'..."
        aws dynamodb delete-table --table-name "$TABLE" --region "$REGION" --output text --query TableDescription.TableStatus
    else
        echo "    '$TABLE' does not exist, skipping."
    fi
done

echo "==> Waiting for all deletions to complete..."
for TABLE in "${TABLES[@]}"; do
    aws dynamodb wait table-not-exists --table-name "$TABLE" --region "$REGION" && echo "    '$TABLE' gone."
done

echo "==> Q1: Creating login table + seeding users..."
uv run q1_create_login.py

echo "==> Q2: Creating music table..."
uv run q2_create_music.py

echo "==> Q3: Loading songs..."
uv run q3_load_music.py

echo "==> Creating subscriptions table..."
uv run create_subscriptions_table.py

echo ""
echo "==> All done. Final item counts:"
for TABLE in "${TABLES[@]}"; do
    COUNT=$(aws dynamodb scan --table-name "$TABLE" --region "$REGION" --select COUNT --output text --query Count)
    echo "    $TABLE: $COUNT items"
done
