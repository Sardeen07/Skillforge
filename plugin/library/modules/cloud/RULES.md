---
module: cloud
capability: Cloud (AWS, GCP, Azure) security, cost and serverless
technologies: cloud
applies: aws, gcp, azure, cloud, s3, lambda, iam, serverless, storage
checked_against: AWS Well-Architected Framework, Google Cloud Architecture Framework, Azure Well-Architected Framework
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## iam-least-privilege: Grant least-privilege IAM to workloads, never wildcard policies
tags: cloud, aws, gcp, azure, iam, least privilege, policies, roles, security
keywords: Action: "*", admin role for app
refs: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege

Give each workload its own role with only the actions and resources it uses (`s3:GetObject` on one bucket prefix, not `s3:*` on `*`). Use IAM Access Analyzer / Recommender to trim unused permissions, and require MFA and short sessions for human access.

## no-long-lived-keys: Use workload identities instead of long-lived access keys
tags: cloud, aws, gcp, azure, access keys, workload identity, oidc, instance profile, secrets
keywords: AWS_ACCESS_KEY_ID in env, service account key json
refs: https://cloud.google.com/iam/docs/best-practices-service-accounts

Attach roles to compute (instance profiles, IRSA/EKS Pod Identity, GKE Workload Identity, Azure Managed Identity) and use OIDC federation from CI. Static keys leak through repos, logs and laptops; if one is unavoidable, scope it narrowly and rotate it automatically.

## private-storage-default: Keep object storage private and block public access
tags: cloud, aws, s3, gcs, azure blob, public bucket, data leak, presigned url
keywords: bucket open to the internet
refs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html

Enable account-level Block Public Access (S3) / public access prevention (GCS) / disable anonymous blob access (Azure). Share individual objects with short-lived presigned URLs, serve public assets through a CDN with origin access control, and enable default encryption and access logging.

## secrets-manager: Store secrets in a managed secret store
tags: cloud, secrets manager, key vault, secret manager, rotation, environment variables, security
keywords: password in parameter plain text
refs: https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html

Keep credentials in AWS Secrets Manager / SSM SecureString, Google Secret Manager or Azure Key Vault, fetch them at runtime with the workload identity, cache them briefly, and enable rotation. Do not put secrets in infrastructure code, container images or plain environment configuration in source control.

## serverless-cold-starts-and-limits: Design serverless functions for statelessness, timeouts and concurrency limits
tags: cloud, serverless, aws lambda, cloud functions, azure functions, cold start, concurrency, database connections
keywords: lambda exhausts database connections, cold start slow
refs: https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html

Initialize clients outside the handler so warm invocations reuse them, keep packages small for faster cold starts, set timeouts below the upstream's, and cap concurrency (reserved concurrency) so bursts cannot exhaust a database; front relational databases with a proxy (RDS Proxy). Make handlers idempotent: event sources retry.

## multi-az-resilience: Spread critical workloads across availability zones and test recovery
tags: cloud, high availability, multi az, disaster recovery, backups, rto, rpo, resilience
keywords: single zone outage took us down
refs: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html

Run stateless tiers in at least two zones behind a load balancer, use multi-AZ options for managed databases, define RPO/RTO targets, automate backups (with cross-region copies for critical data), and regularly test restores; an untested backup is not a backup.

## cost-visibility: Tag resources, set budgets and remove idle spend
tags: cloud, cost optimization, finops, tagging, budgets, rightsizing, idle resources
keywords: surprise cloud bill
refs: https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html

Tag every resource with owner, environment and service, set budgets with alerts, review the biggest line items monthly, rightsize from utilization data, delete idle resources (unattached volumes, old snapshots, stopped instances with storage), and use lifecycle policies to move cold objects to cheaper storage classes. Watch data-transfer and NAT costs, which surprise teams most.

## network-segmentation-cloud: Place databases in private subnets and restrict security groups
tags: cloud, vpc, private subnet, security groups, firewall, network segmentation, bastion
keywords: database publicly accessible
refs: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html

Keep databases and internal services in private subnets without public IPs, allow inbound traffic only from the specific security groups that need it (never `0.0.0.0/0` on database or SSH ports), use VPC endpoints for cloud APIs, and use SSM Session Manager / IAP instead of open SSH.

## audit-logging-cloud: Enable audit logs and alert on sensitive changes
tags: cloud, cloudtrail, audit logs, cloud audit logs, activity log, detection, security monitoring
keywords: who deleted the bucket
refs: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/best-practices-security.html

Enable organization-wide audit logging (CloudTrail, Cloud Audit Logs, Azure Activity Log) to a separate, write-protected account or project, and alert on high-risk events: root/owner logins, IAM policy changes, disabled logging, public access changes.

## managed-services-default: Prefer managed services for undifferentiated infrastructure
tags: cloud, managed services, rds, cloud sql, operations, maintenance, architecture
keywords: running our own database on vm
refs: https://cloud.google.com/architecture/framework

Self-running databases, queues and Kubernetes control planes costs on-call time for patching, backups and failover. Prefer managed equivalents unless you need control they do not offer, and understand their limits (connection caps, maintenance windows, failover time).
