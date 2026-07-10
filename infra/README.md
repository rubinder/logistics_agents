# Deploy — AWS (Terraform)

Provisions the public showcase: the dashboard on S3 + CloudFront, the FastAPI service on a small EC2 (with Postgres in a container), and CloudFront proxying the API paths so the browser stays same-origin (no CORS, no mixed content). The Anthropic key lives only in SSM Parameter Store.

```
                    ┌──────────── CloudFront (HTTPS) ────────────┐
   browser ───────▶ │  /            → S3 (static dashboard)       │
                    │  /runs*,/budget,/scenarios,/health → EC2    │
                    └───────────────────┬────────────────────────┘
                                        ▼
                         EC2 (t3.small) · docker compose
                           ├─ api (FastAPI, :80)   ── reads key from SSM
                           └─ postgres
```

## Architecture notes
- **Same-origin proxy, not CORS.** CloudFront serves the dashboard from S3 and proxies the API path patterns to the EC2 origin over HTTP. The browser only ever talks HTTPS to CloudFront, so there is no CORS config and no mixed-content. The dashboard is built with an empty `VITE_API_BASE` (relative fetches).
- **Security group is locked to CloudFront.** The EC2 API port 80 accepts traffic only from CloudFront's `com.amazonaws.global.cloudfront.origin-facing` managed prefix list — not the open internet. No SSH port; shell access is via SSM Session Manager.
- **The key never touches Terraform state.** It is created out-of-band as an SSM `SecureString`; Terraform only grants the instance role `ssm:GetParameter` on that one parameter (+ `kms:Decrypt` scoped to SSM).
- **Spend guards** are env-driven on the instance (`LOGISTICS_BUDGET_CAP_USD`, `LOGISTICS_PER_IP_DAILY`, `LOGISTICS_GLOBAL_DAILY`, `LOGISTICS_TRIGGER_MODEL`) — defaults: $5/month cap, 5/IP/day, 30/day global, Haiku.
- **Redpanda is intentionally omitted** from the deploy (`docker-compose.deploy.yml`) — the API runs the pipeline synchronously and doesn't consume Kafka in the request path.

## Prerequisites
- Terraform ≥ 1.6, AWS CLI, an AWS identity with permissions for S3/CloudFront/EC2/IAM/SSM.
- The EC2 clones the app from GitHub at boot, so the target branch must be pushed (default `milestone-8-aws-deploy`; point `repo_branch` at `main` once the stack is merged).
- If your CLI authenticates via `aws login` (the `~/.aws/login` store), Terraform's provider can't read it directly — bridge it per command:
  `eval "$(aws configure export-credentials --format env)"; terraform …`

## Deploy
```bash
# 1. Store the Anthropic key (server-side only; never in state or the browser).
aws ssm put-parameter --name /logistics-agents/anthropic-api-key \
  --type SecureString --value "sk-ant-..." --region us-east-1 --overwrite

# 2. Provision.
cd infra
terraform init
terraform apply         # ~3 min; CloudFront takes the longest

# 3. Build the dashboard (same-origin) and publish it.
cd ../dashboard && npm ci && npm run build
BUCKET=$(cd ../infra && terraform output -raw s3_bucket)
DIST=$(cd ../infra && terraform output -raw cloudfront_distribution_id)
aws s3 sync dist "s3://$BUCKET" --delete
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*"

# 4. Open it.
cd ../infra && terraform output -raw dashboard_url
```
The EC2 finishes its `docker compose up --build` a few minutes after `apply`; `curl "$(terraform output -raw dashboard_url)/health"` returns `{"status":"ok"}` once it's serving.

## Redeploy the dashboard only
```bash
cd dashboard && npm run build
aws s3 sync dist "s3://$(cd ../infra && terraform output -raw s3_bucket)" --delete
aws cloudfront create-invalidation \
  --distribution-id "$(cd ../infra && terraform output -raw cloudfront_distribution_id)" --paths "/*"
```

## Redeploy the API (after code changes)
Push the branch, then re-run the instance's user-data by tainting it (recreates the box) or SSM into it and `git pull && docker compose --env-file .env -f docker-compose.deploy.yml up -d --build`:
```bash
aws ssm start-session --target "$(terraform output -raw instance_id)"
```

## Tear down (stop all charges)
```bash
cd infra
terraform destroy
# Then delete the key if you no longer need it:
aws ssm delete-parameter --name /logistics-agents/anthropic-api-key --region us-east-1
```

## Cost (approx, us-east-1)
Mostly the EC2: `t3.small` ≈ $15/mo + 20 GB gp3 ≈ $1.6/mo. CloudFront/S3/EIP-while-attached are negligible at demo traffic. `terraform destroy` stops all of it.
