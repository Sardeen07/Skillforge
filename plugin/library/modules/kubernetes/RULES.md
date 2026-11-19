---
module: kubernetes
capability: Kubernetes workloads: reliability, resources and security
technologies: kubernetes
applies: kubernetes, k8s, pod, deployment, helm, probes, ingress
checked_against: Kubernetes 1.31 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## resource-requests-limits: Set CPU and memory requests, and memory limits
tags: kubernetes, resources, requests, limits, oomkilled, cpu throttling, scheduling
keywords: OOMKilled, noisy neighbor, pods evicted
refs: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

Requests drive scheduling; without them pods overcommit nodes and get evicted first. Set requests from observed usage, set a memory limit (exceeding it gets the container OOM-killed), and be cautious with CPU limits, which throttle latency-sensitive services even when the node is idle. Size runtimes to the limit (e.g. JVM `MaxRAMPercentage`, Node `--max-old-space-size`).

## probes-correctly: Configure readiness, liveness and startup probes for their purposes
tags: kubernetes, probes, readiness probe, liveness probe, startup probe, health checks, restarts
keywords: restart loop, traffic sent to unready pod
refs: https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/

Readiness gates traffic (fail it when dependencies needed to serve are unavailable or during shutdown); liveness restarts a stuck process (check only the process itself, never downstream dependencies, or one database blip restarts every pod); a startup probe protects slow-starting apps from liveness kills.

## graceful-termination-k8s: Handle SIGTERM and allow endpoint removal before exit
tags: kubernetes, graceful shutdown, sigterm, prestop, terminationgraceperiodseconds, rolling update
keywords: 502 errors during deploy
refs: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination

Removing a pod from Service endpoints happens concurrently with SIGTERM, so a pod that exits immediately still receives some traffic. Add a short `preStop` sleep (or delay in the app), stop accepting new work, finish in-flight requests within `terminationGracePeriodSeconds`, then exit.

## rollout-safety: Use rolling updates with PodDisruptionBudgets and multiple replicas
tags: kubernetes, rolling update, poddisruptionbudget, replicas, high availability, anti affinity, zero downtime
keywords: outage during node drain
refs: https://kubernetes.io/docs/tasks/run-application/configure-pdb/

Run at least two replicas spread across nodes/zones (topology spread constraints or anti-affinity), set `maxUnavailable: 0`/`maxSurge` for zero-downtime rollouts, and add a PodDisruptionBudget so node drains cannot take all replicas down at once.

## secrets-handling-k8s: Treat Kubernetes Secrets as base64, not encryption
tags: kubernetes, secrets, encryption at rest, rbac, external secrets, vault, sealed secrets
keywords: secret committed in yaml
refs: https://kubernetes.io/docs/concepts/security/secrets-good-practices/

Secrets are only base64-encoded. Enable encryption at rest, restrict `get/list` on secrets with RBAC, never commit secret manifests in plain text (use External Secrets, Sealed Secrets or SOPS), and prefer mounting as files over environment variables, which leak into crash dumps and child processes.

## pod-security: Run pods with a restricted security context
tags: kubernetes, security context, run as non root, read only root filesystem, capabilities, pod security standards
keywords: privileged container
refs: https://kubernetes.io/docs/concepts/security/pod-security-standards/

Apply the `restricted` Pod Security Standard: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true` (with writable `emptyDir` where needed), drop all capabilities, and use a `RuntimeDefault` seccomp profile. Disable `automountServiceAccountToken` for pods that do not call the API.

## network-policies: Default-deny network policies between namespaces
tags: kubernetes, network policy, segmentation, zero trust, ingress, egress, security
keywords: any pod can reach the database
refs: https://kubernetes.io/docs/concepts/services-networking/network-policies/

By default every pod can reach every other pod. Add a default-deny policy per namespace and allow only required flows (frontend → API → database), including egress where your CNI supports it.

## image-tags-immutable: Deploy immutable image references
tags: kubernetes, image tags, latest, digest, imagepullpolicy, reproducible deploys, rollback
keywords: different pods run different code
refs: https://kubernetes.io/docs/concepts/containers/images/#image-names

With `:latest` or reused tags, pods started at different times run different code and rollbacks are impossible. Deploy unique tags (commit SHA) or digests, and roll back by redeploying the previous reference.

## autoscaling-hpa: Autoscale on a metric that reflects load, with sane bounds
tags: kubernetes, autoscaling, hpa, horizontal pod autoscaler, metrics, scaling, keda
keywords: hpa not scaling, flapping replicas
refs: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

HPA on CPU requires CPU requests to be set. For queue workers or I/O-bound services, scale on a metric that tracks demand (queue depth, requests per second) via custom/external metrics or KEDA. Set min/max replicas and stabilization windows to avoid flapping, and make sure downstream capacity (database connections) scales with it.

## k8s-config-and-rollouts: Roll pods when ConfigMaps or Secrets change
tags: kubernetes, configmap, secrets, rollout, deployment, configuration change, checksum annotation
keywords: config change not picked up by pods
refs: https://kubernetes.io/docs/concepts/configuration/configmap/#mounted-configmaps-are-updated-automatically

Environment variables from a ConfigMap are read only at container start, and mounted files update eventually but most apps never reload them. Trigger a rollout when configuration changes: a checksum annotation of the config in the pod template (Helm), `kubectl rollout restart`, or immutable, versioned ConfigMap names.
