---
module: grpc
capability: gRPC services and Protocol Buffers schema evolution
technologies: grpc
applies: grpc, protobuf, protocol buffers, proto, rpc, microservices
checked_against: gRPC documentation (grpc.io) and Protocol Buffers language guide (proto3)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-18; each rule cites the reference it was checked against
review: pending human review
---

## proto-field-numbers-forever: Never reuse or renumber Protocol Buffers fields
tags: grpc, protobuf, schema evolution, field numbers, reserved, backward compatibility, breaking change
keywords: renumbered field broke clients
refs: https://protobuf.dev/programming-guides/proto3/#updating

Field numbers, not names, identify fields on the wire. Never change a field's number or type; when deleting a field, mark its number and name `reserved` so no one reuses them. Add fields with new numbers, and run a breaking-change checker (buf breaking) in CI.

## grpc-deadlines: Set a deadline on every gRPC call and propagate it
tags: grpc, deadlines, timeouts, cancellation, context, propagation, resilience
keywords: rpc hangs forever
refs: https://grpc.io/docs/guides/deadlines/

gRPC calls have no deadline by default, so a stuck server holds the client forever. Set a deadline on every call, pass the incoming request's context to outgoing calls so the remaining budget propagates, and check for cancellation in long server handlers.

## grpc-status-codes: Return precise status codes and retry only safe ones
tags: grpc, status codes, error handling, retries, unavailable, deadline exceeded, idempotency
keywords: every error is UNKNOWN
refs: https://grpc.io/docs/guides/status-codes/

Map failures to specific codes (`INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `PERMISSION_DENIED`, `UNAVAILABLE`) instead of `UNKNOWN`, attach details with rich error models when useful, and configure retries (service config retry policy) only for `UNAVAILABLE` and for idempotent methods.

## grpc-channel-reuse: Reuse channels and configure keepalive and load balancing
tags: grpc, channel, connection reuse, keepalive, load balancing, http2, performance
keywords: new channel per request
refs: https://grpc.io/docs/guides/performance/

A channel is an HTTP/2 connection pool and is expensive to create: create one per target and reuse it. Behind L4 load balancers a single long-lived HTTP/2 connection pins all traffic to one backend; use client-side load balancing (round_robin with DNS or xDS) or an L7 proxy, and set keepalive within server limits.

## grpc-large-payloads-streaming: Stream large data instead of raising message size limits
tags: grpc, streaming, message size, resource exhausted, large payloads, memory
keywords: RESOURCE_EXHAUSTED received message larger than max
refs: https://grpc.io/docs/guides/performance/

gRPC limits received messages to 4 MB by default. Rather than raising the limit to move files or big result sets in one message, use server or client streaming with chunks, or put the payload in object storage and send a reference.
