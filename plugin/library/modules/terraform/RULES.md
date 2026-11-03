---
module: terraform
capability: Terraform state, modules and safe changes
technologies: terraform
applies: terraform, hcl, state, module, plan, infrastructure as code
checked_against: Terraform 1.9 documentation (developer.hashicorp.com)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## remote-state-locking: Use remote state with locking and encryption
tags: terraform, state, remote backend, state locking, s3 backend, encryption, collaboration
keywords: terraform.tfstate committed, state conflict
refs: https://developer.hashicorp.com/terraform/language/state/remote

Store state in a remote backend with locking (S3 with native lockfile or DynamoDB, GCS, Azure Storage, HCP Terraform), enable encryption and versioning, and restrict access: state contains resource attributes and often secrets. Never commit `terraform.tfstate`.

## plan-review-apply: Apply only reviewed saved plans
tags: terraform, plan, apply, code review, ci, drift, destroy
keywords: apply destroyed production database
refs: https://developer.hashicorp.com/terraform/cli/commands/plan#out-filename

Run `terraform plan -out=tfplan` in CI, review the plan (especially replacements, `-/+`, and destroys), and apply that exact saved plan. Add `lifecycle { prevent_destroy = true }` to stateful resources such as databases and buckets.

## pin-versions-terraform: Pin Terraform and provider versions and commit the lock file
tags: terraform, provider versions, required_providers, lock file, reproducibility, upgrades
keywords: provider upgrade broke plan
refs: https://developer.hashicorp.com/terraform/language/files/dependency-lock

Set `required_version` and version constraints in `required_providers`, commit `.terraform.lock.hcl`, and upgrade providers deliberately (`terraform init -upgrade`) in a dedicated change with a reviewed plan.

## modules-small-composable: Write small modules with typed variables and outputs
tags: terraform, modules, variables, validation, outputs, reuse, composition
keywords: one giant main.tf
refs: https://developer.hashicorp.com/terraform/language/modules/develop

Group resources that change together into modules with typed, documented variables (with `validation` blocks) and explicit outputs. Pin module sources to versions. Avoid deep module nesting and do not wrap single resources in modules for their own sake.

## separate-state-per-environment: Split state by environment and blast radius
tags: terraform, environments, workspaces, state separation, blast radius, directories
keywords: staging change touched production
refs: https://developer.hashicorp.com/terraform/language/state/workspaces#when-not-to-use-multiple-workspaces

Keep production and non-production in separate state files (separate directories or root modules, with separate credentials), and split large estates by lifecycle (network, data, apps) so one plan cannot change everything and plans stay fast.

## no-secrets-in-tf: Keep secrets out of Terraform code and outputs
tags: terraform, secrets, sensitive, variables, state, vault, security
keywords: password in tfvars committed
refs: https://developer.hashicorp.com/terraform/language/values/variables#suppressing-values-in-cli-output

Do not hardcode secrets in `.tf` or committed `.tfvars`; read them from a secret manager data source or generate them and store them there. Mark variables and outputs `sensitive = true` (this hides CLI output but not state), and use ephemeral resources/write-only arguments where your version supports them.

## refactor-with-moved: Refactor with moved and import blocks instead of manual state surgery
tags: terraform, refactoring, moved block, import block, state mv, resource address
keywords: renaming resource destroys it
refs: https://developer.hashicorp.com/terraform/language/modules/develop/refactoring

Renaming a resource or moving it into a module makes Terraform plan a destroy and create. Declare `moved { from = ... to = ... }` blocks so the plan shows a move, and bring existing infrastructure under management with `import` blocks reviewed in a plan rather than ad-hoc CLI state commands.
