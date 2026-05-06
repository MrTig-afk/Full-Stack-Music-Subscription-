# AWS Academy Learner Lab Reference

Source: AWS Academy Learner Lab access documentation provided in chat.

This note is a working reference for using the AWS Academy sandbox from this workspace. It focuses on what matters day to day: where the lab is restricted, what survives between sessions, what can and cannot be left running, and how to access AWS from a browser-based terminal.

## Lab model

- Sandbox is long-lived.
- Ending a session does not wipe account resources.
- Starting a new session later usually restores prior state.
- EC2 instances started by the lab are stopped at session end and restarted on the next session start.
- SageMaker notebook instances are stopped at session end but are not automatically restarted next session.
- SageMaker Canvas apps can stay running unless deleted.

## Budget rules

- Watch remaining lab budget in the lab UI.
- Budget data updates slowly, typically every 8 to 12 hours.
- Budget display may lag recent activity.
- Exceeding budget can disable the lab account and delete progress and resources.
- Treat always-on compute as the main cost risk.

## Region limits

- Normal service access is restricted to `us-east-1` and `us-west-2`.
- Using another region can trigger access errors.
- This project should stay on `us-east-1` unless a service note says otherwise.

## High-risk resource limits

### EC2

- Only on-demand instances.
- Supported sizes: nano, micro, small, medium, large.
- Maximum 9 running EC2 instances per region.
- Maximum 32 vCPU total across running EC2 instances per region.
- Launching 20 or more running instances can deactivate the account and delete resources.
- AWS Marketplace AMIs are not supported.
- Use AMIs available in `us-east-1` or `us-west-2`.

### EBS

- Maximum volume size: 100 GB.
- Supported types: gp2, gp3, sc1, standard.
- PIOPS is not supported.

### ECS

- Supported instance types: nano, micro, small, medium, large.
- Fargate is available.
- If using ECS task definitions, set LabRole for task role and execution role.

### Lambda

- Use LabRole when the function needs AWS access.
- Maximum 10 concurrent running Lambda execution environments.

### SageMaker

- Supported instance types are limited to specific small-to-medium sizes.
- Maximum 2 notebook instances.
- Maximum 2 SageMaker apps.
- Stop or delete unused notebooks, spaces, and Canvas apps.

### RDS

- Supported engines include Aurora, Oracle, SQL Server, MySQL, PostgreSQL, MariaDB.
- Supported instance sizes: nano, micro, small, medium.
- Maximum storage 100 GB.
- PIOPS is not supported.
- Enhanced monitoring is not supported.
- Stopped RDS instances may restart automatically after seven days.

## Pre-created IAM assets

- `LabRole` exists already.
- `LabInstanceProfile` exists already.
- Many AWS services can assume `LabRole`.
- For EC2 browser terminal access, attach `LabInstanceProfile` to the instance.
- For Lambda, attach `LabRole` if the function needs AWS permissions.

## Browser terminal access

### CloudShell

- Available from the AWS console.
- AWS CLI credentials are preconfigured.
- Python 3 and `boto3` are available.
- Z shell can be used for Q suggestions.

### EC2 terminal in browser

- Launch EC2 with `LabInstanceProfile`.
- Use EC2 Instance Connect or Systems Manager Session Manager where applicable.
- On Amazon Linux 2, AWS CLI is already installed.

## EC2 connection notes

- In `us-east-1`, the `vockey` key pair is available.
- For Windows or Linux SSH, use the lab-provided PEM/PPK download.
- Public IPs change when stopped and started unless an Elastic IP is attached.

## Service notes that matter for this project

- API Gateway can assume LabRole.
- DynamoDB can assume LabRole.
- ECR read access is available to the console user.
- ECS can assume LabRole.
- CloudFormation can assume LabRole.
- ELB can assume LabRole.
- S3 can assume LabRole.
- SSM can assume LabRole.

## Cost-control habits

- Stop EC2 when not in use.
- Delete resources you do not need between sessions.
- Prefer CloudFormation stacks for repeatable infra, then delete the stack when done.
- Check Tag Editor or Trusted Advisor to find forgotten resources.
- Treat NAT Gateway, EC2, RDS, ECS, and EKS as the main budget drains.

## Practical workflow for this repo

- Keep infra in `us-east-1`.
- Use CloudFormation or scripted deployment for repeatable environments.
- For containerized backends, keep container port and host mapping aligned on port 80.
- For API Gateway proxies, the public API is HTTPS, but the backend URL can still be HTTP.
- For Lambda, use the Mangum adapter and avoid port-based assumptions.

## Fast reminders

- Session end does not erase resources.
- EC2 can restart next session.
- SageMaker notebook instances do not auto-restart.
- Budget updates lag.
- 20+ concurrent EC2 instances is a hard safety tripwire.
