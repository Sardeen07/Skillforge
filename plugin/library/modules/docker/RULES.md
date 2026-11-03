---
module: docker
capability: Container images: size, security and build speed
technologies: docker
applies: docker, dockerfile, container, image, compose, build
checked_against: Docker documentation (build best practices, 2025)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## multi-stage-builds: Use multi-stage builds to keep runtime images small
tags: docker, multi stage build, image size, build tools, distroless, slim image
keywords: image is 2GB, compilers in production image
refs: https://docs.docker.com/build/building/multi-stage/

Compile and install build dependencies in a builder stage, then `COPY --from=builder` only the artifacts into a minimal runtime image (`-slim`, Alpine where libc compatibility allows, or distroless). Smaller images pull faster and contain fewer vulnerable packages.

## layer-caching-order: Order Dockerfile instructions for cache hits
tags: docker, layer caching, build speed, dockerfile order, dependencies, copy
keywords: npm install runs on every build
refs: https://docs.docker.com/build/cache/

Copy dependency manifests first and install dependencies before copying the rest of the source (`COPY package*.json ./` → `RUN npm ci` → `COPY . .`), so code changes do not invalidate the dependency layer. Use BuildKit cache mounts (`RUN --mount=type=cache,target=/root/.cache/pip`) for package caches.

## non-root-user: Run containers as a non-root user
tags: docker, security, non root, user, privileges, container escape, least privilege
keywords: container runs as root
refs: https://docs.docker.com/build/building/best-practices/#user

Create and switch to an unprivileged user (`USER 10001`) in the image, keep files the process does not need to write owned by root and read-only, and drop capabilities at runtime. Never mount the Docker socket into application containers.

## no-secrets-in-images: Never bake secrets into images or build args
tags: docker, secrets, build args, env, image layers, security, buildkit secrets
keywords: api key in dockerfile, ARG password
refs: https://docs.docker.com/build/building/secrets/

Anything in `ENV`, `ARG` or a copied file remains readable in image layers and history, even if deleted in a later layer. Use BuildKit secret mounts (`RUN --mount=type=secret,id=npmrc`) at build time and inject runtime secrets via the orchestrator. Add a `.dockerignore` that excludes `.env`, `.git` and credentials.

## pin-base-images: Pin base images and rebuild regularly
tags: docker, base image, tags, digest, reproducibility, vulnerabilities, latest tag
keywords: FROM node:latest broke build
refs: https://docs.docker.com/build/building/best-practices/#pin-base-image-versions

`:latest` changes underneath you. Pin a specific version tag (and a digest for full reproducibility), automate updates (Dependabot/Renovate), rebuild regularly to pick up security patches, and scan images in CI.

## pid1-signals: Use exec form and handle signals as PID 1
tags: docker, pid 1, signals, sigterm, entrypoint, exec form, graceful shutdown, tini
keywords: container takes 10 seconds to stop
refs: https://docs.docker.com/reference/dockerfile/#entrypoint

The shell form (`CMD npm start`) runs your process under `/bin/sh`, which does not forward SIGTERM, so containers are killed after the grace period. Use exec form (`CMD ["node", "server.js"]`), make the app handle SIGTERM, and use `--init`/tini when the process does not reap child processes.

## healthchecks-and-one-process: Run one concern per container and expose health
tags: docker, healthcheck, single process, compose, depends_on, readiness
keywords: supervisord in container, app starts before database
refs: https://docs.docker.com/reference/compose-file/services/#healthcheck

Run one main process per container and compose services instead of supervisors. Define health checks and, in Compose, use `depends_on: { db: { condition: service_healthy } }`; applications should still retry connections at startup.

## dockerignore: Add a .dockerignore to shrink build context and avoid leaks
tags: docker, dockerignore, build context, secrets, node_modules, git
keywords: sending build context 1.5GB
refs: https://docs.docker.com/build/concepts/context/#dockerignore-files

Exclude `.git`, `node_modules`, virtual environments, build outputs, local `.env` files and credentials from the build context. This speeds up builds, avoids cache invalidation from irrelevant files and prevents secrets from being copied into images by `COPY . .`.
