# Serverless Expense Tracker

Personal finance tracker on AWS: log in, record transactions by category, view
monthly spending charts, and get an email when a budget is exceeded.

**Stack:** Python 3.12 Lambda · API Gateway · Aurora Serverless v2 (PostgreSQL,
via RDS Data API) · Cognito · SNS + EventBridge · React + Vite + Recharts ·
S3 + CloudFront · AWS SAM · GitHub Actions

## Run tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Deploy

```bash
sam build -t infra/template.yaml
sam deploy --guided --stack-name expense-tracker --capabilities CAPABILITY_IAM
```

Then:
1. Run `infra/db/schema.sql` in the RDS console Query editor.
2. Create a user with `aws cognito-idp admin-create-user` (there's no sign-up page).
3. Fill in `frontend/.env` from the stack outputs, then `npm run build` and sync
   `dist/` to the `FrontendBucketName` bucket.

After the first deploy, pushes to `master` deploy automatically. The workflows
need the repo secrets `AWS_DEPLOY_ROLE_ARN` (an IAM role trusted via GitHub
OIDC) and `ALERT_EMAIL`.
