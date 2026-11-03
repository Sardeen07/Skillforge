---
module: linux-networking
capability: Linux shell scripting, processes and networking fundamentals
technologies: linux, networking
applies: linux, bash, shell, systemd, tcp, dns, tls, nginx, network
checked_against: Bash manual, man7.org Linux man pages, nginx documentation, RFC 8446 (TLS 1.3)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## bash-strict-mode: Start bash scripts with set -euo pipefail and quote variables
tags: linux, bash, shell script, set -e, pipefail, quoting, error handling
keywords: script continued after error, filenames with spaces
refs: https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html

Use `set -euo pipefail` so failures, unset variables and failed pipeline stages stop the script (know its exceptions: commands in `if` conditions and `||` lists). Always quote expansions (`"$file"`, `"$@"`), use `[[ ]]` for tests, run ShellCheck in CI, and switch to a real language when a script grows past simple glue.

## temp-files-safely: Create temporary files with mktemp and clean up with trap
tags: linux, bash, mktemp, trap, temporary files, race condition, cleanup
keywords: /tmp/myfile collision
refs: https://man7.org/linux/man-pages/man1/mktemp.1.html

Predictable names in `/tmp` race and can be hijacked. Use `tmp=$(mktemp -d)` and `trap 'rm -rf "$tmp"' EXIT` so cleanup happens on every exit path.

## systemd-services: Run long-lived services under systemd with restart and hardening
tags: linux, systemd, service, restart, journald, hardening, daemon
keywords: nohup in cron, process died and nobody noticed
refs: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

Define a unit with `Restart=on-failure`, a dedicated `User=`, `EnvironmentFile=` for configuration, and hardening options (`NoNewPrivileges=yes`, `ProtectSystem=strict`, `PrivateTmp=yes`). Log to stdout/stderr and read with `journalctl -u name`, rather than daemonizing with `nohup` or `&`.

## file-descriptor-limits: Raise file descriptor limits for servers with many connections
tags: linux, ulimit, file descriptors, too many open files, nofile, connections, sockets
keywords: EMFILE too many open files
refs: https://man7.org/linux/man-pages/man2/getrlimit.2.html

Every socket and file is a descriptor; the common default soft limit of 1024 is too low for busy servers. Raise `LimitNOFILE=` in the systemd unit (or container runtime settings), and also check for descriptor leaks (count with `ls /proc/<pid>/fd | wc -l`).

## dns-caching-ttl: Respect DNS TTLs and do not cache resolutions forever
tags: networking, dns, ttl, caching, failover, connection pooling, resolver
keywords: service still hitting old ip after failover
refs: https://www.rfc-editor.org/rfc/rfc1035

Clients that resolve a hostname once at startup and cache it forever (some JVM settings, long-lived pools) keep using old IPs after failovers or load-balancer changes. Honor TTLs (e.g. Java `networkaddress.cache.ttl`), recycle pooled connections periodically, and keep TTLs short for endpoints that move.

## tls-configuration: Enforce modern TLS and verify certificates
tags: networking, tls, ssl, certificates, https, hsts, verification, security
keywords: verify=False, certificate verify failed workaround
refs: https://ssl-config.mozilla.org/

Serve TLS 1.2+ (prefer 1.3) with Mozilla's recommended ciphers, automate certificate renewal (ACME), and enable HSTS. In clients, never disable certificate verification (`verify=False`, `InsecureSkipVerify`) to work around errors; install the correct CA bundle instead.

## reverse-proxy-headers: Configure reverse proxy timeouts, body limits and forwarded headers
tags: networking, nginx, reverse proxy, x-forwarded-for, timeouts, client_max_body_size, load balancer
keywords: 413 request entity too large, 504 gateway timeout, client ip wrong
refs: https://nginx.org/en/docs/http/ngx_http_proxy_module.html

Set `proxy_read_timeout`/`proxy_connect_timeout` to match upstream behavior, `client_max_body_size` for uploads, and forward `X-Forwarded-For`/`X-Forwarded-Proto`/`Host`. Applications must trust forwarded headers only from known proxies, or clients can spoof their IP.

## connection-reuse-keepalive: Reuse connections with keep-alive and tune idle timeouts consistently
tags: networking, keep alive, connection reuse, idle timeout, load balancer, tcp, 502
keywords: intermittent 502 from load balancer
refs: https://www.rfc-editor.org/rfc/rfc9112.html#name-persistence

Opening TCP+TLS per request adds round trips. Reuse connections with keep-alive pools, and make the backend's idle timeout longer than the load balancer's (or the client's pool idle timeout shorter than the server's); otherwise the server closes connections the proxy is about to reuse, producing sporadic 502s.
