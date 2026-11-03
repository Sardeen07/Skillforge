---
module: ci-cd
capability: CI/CD pipelines and GitHub Actions security and speed
technologies: ci-cd, github-actions
applies: ci, cd, pipeline, github actions, workflow, deploy, release
checked_against: GitHub Actions documentation (security hardening, caching), 2025
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## pin-actions-sha: Pin third-party actions to a full commit SHA
tags: github actions, supply chain, pin actions, sha, security, third party actions
keywords: uses: some/action@main, tag moved
refs: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-third-party-actions

Tags and branches of third-party actions can be moved to malicious code (as happened with a popular action in 2025). Pin to a full-length commit SHA with a version comment (`uses: org/action@<sha> # v4.1.0`) and let Dependabot propose updates.

## least-privilege-token: Set minimal GITHUB_TOKEN permissions
tags: github actions, github_token, permissions, least privilege, security, workflow
keywords: write-all token
refs: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication#modifying-the-permissions-for-the-github_token

Declare `permissions: contents: read` at the workflow top and grant extra scopes only to the jobs that need them (`packages: write`, `id-token: write`). Use OIDC federation (`id-token: write`) to get short-lived cloud credentials instead of long-lived secrets.

## untrusted-input-injection: Never interpolate untrusted event data into run scripts
tags: github actions, script injection, pull_request_target, security, expressions, untrusted input
keywords: ${{ github.event.issue.title }} in run
refs: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#understanding-the-risk-of-script-injections

`run: echo "${{ github.event.pull_request.title }}"` lets an attacker inject shell commands through a PR title. Pass such values through `env:` and reference `"$TITLE"`. Avoid `pull_request_target` with a checkout of the PR's code, which runs untrusted code with secrets.

## cache-dependencies-ci: Cache dependencies keyed on the lock file
tags: ci cd, caching, github actions cache, dependencies, build speed, lock file
keywords: ci slow, reinstalling dependencies
refs: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows

Use the setup actions' built-in caching (`actions/setup-node` with `cache: npm`, `setup-python` with `cache: pip`) or `actions/cache` keyed on a hash of the lock file. Cache package downloads, not build outputs that can mask stale state, and install with lock-respecting commands (`npm ci`).

## fast-feedback-pipeline: Order and parallelize jobs for fast feedback
tags: ci cd, pipeline design, parallel jobs, matrix, fail fast, test splitting, concurrency
keywords: ci takes 40 minutes
refs: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variations-of-jobs-in-a-workflow

Run cheap checks (lint, type check, unit tests) first and in parallel, split slow suites across a matrix, use `concurrency` with `cancel-in-progress` for superseded pushes, and run path-filtered jobs only when relevant files change. Keep main-branch CI under about ten minutes.

## build-once-deploy-many: Build an artifact once and promote it across environments
tags: ci cd, artifacts, deployment, promotion, staging, production, immutable builds
keywords: rebuilt for production, works in staging fails in prod
refs: https://12factor.net/build-release-run

Build the image or package once per commit, tag it immutably, and promote the same artifact from staging to production with environment-specific configuration injected at deploy time. Rebuilding per environment means production runs code that was never tested.

## protected-deployments: Gate production deploys with environments and approvals
tags: ci cd, deployment, environments, approvals, branch protection, rollback, release
keywords: anyone can deploy to production
refs: https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment

Use deployment environments with required reviewers and branch restrictions for production, store production secrets only in that environment, require status checks before merge, and keep a tested, one-command rollback path.

## flaky-tests-ci: Quarantine and fix flaky tests instead of auto-retrying everything
tags: ci cd, flaky tests, retries, test reliability, quarantine, nondeterminism
keywords: just re-run the pipeline
refs: https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/re-running-workflows-and-jobs

Blanket retries hide real race conditions and erode trust in CI. Track flaky tests, quarantine them with an owner and deadline, and fix root causes (shared state, time, ordering, network). Reproduce with repeated runs (`--count`, `pytest-repeat`) and randomized order.

## secret-scanning-ci: Scan for secrets and vulnerable dependencies in CI
tags: ci cd, secret scanning, dependency scanning, sast, security, supply chain
keywords: leaked credentials in commit
refs: https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning

Enable secret scanning with push protection, dependency review on pull requests, and a vulnerability scanner for dependencies and container images. Rotate any credential that reaches a commit; deleting the commit does not unleak it.
