---
module: realtime
capability: Real-time features with WebSockets and Server-Sent Events
technologies:
applies: websocket, sse, server sent events, real time, live updates, push, socket io
checked_against: RFC 6455, WHATWG HTML (Server-sent events), MDN Web Docs
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-18; each rule cites the reference it was checked against
review: pending human review
---

## choose-sse-or-websocket: Prefer Server-Sent Events for one-way server push
tags: realtime, sse, server sent events, websocket, live updates, notifications, push
keywords: live dashboard updates, notifications to browser
refs: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events

If only the server pushes (notifications, progress, live dashboards), Server-Sent Events work over plain HTTP, reconnect automatically and resume with `Last-Event-ID`, and pass through proxies and HTTP/2. Use WebSockets when the client must send frequent messages on the same channel (chat, collaborative editing, games).

## websocket-auth-and-origin: Authenticate WebSocket connections and check Origin
tags: realtime, websocket, authentication, origin, cross site websocket hijacking, cookies, security
keywords: websocket accepts any connection
refs: https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html

Browsers attach cookies to WebSocket handshakes from any site, so a cookie-authenticated socket without an `Origin` check can be hijacked cross-site. Verify `Origin` against an allowlist during the handshake, authenticate (session or short-lived token sent in the first message rather than the URL, which gets logged), and authorize every subscribe or action message, not only the connection.

## reconnect-with-backoff-and-resume: Reconnect clients with backoff and resume missed messages
tags: realtime, websocket, reconnect, backoff, jitter, resume, message ids, reliability
keywords: thousands of clients reconnect at once after deploy
refs: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close_event

Connections drop on deploys, network changes and sleep. Reconnect with exponential backoff plus jitter (or all clients stampede the server at once), send the last received message id on reconnect, and have the server replay what was missed or tell the client to refetch state.

## heartbeats-and-timeouts: Detect dead connections with heartbeats
tags: realtime, websocket, ping pong, heartbeat, idle timeout, load balancer, half open connections
keywords: connections silently dead, proxy closes idle websocket
refs: https://www.rfc-editor.org/rfc/rfc6455.html#section-5.5.2

TCP does not tell you when the far side vanishes, and proxies close idle connections (often after 60 seconds). Send pings or application heartbeats more often than the shortest idle timeout in the path, close connections that miss several, and free their subscriptions.

## backpressure-slow-consumers: Bound per-connection send buffers
tags: realtime, websocket, backpressure, slow consumer, memory, buffer, broadcast
keywords: server memory grows with slow clients
refs: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/bufferedAmount

A client that reads slower than you broadcast makes the server buffer without limit. Cap each connection's outbound queue (check `bufferedAmount`, or the server library's equivalent), then drop, coalesce (send only the latest state) or disconnect when it is exceeded.

## scale-out-pubsub: Fan out across server instances with a shared broker
tags: realtime, scaling, pub sub, redis, sticky sessions, horizontal scaling, websocket
keywords: messages only reach users on the same server
refs: https://socket.io/docs/v4/adapter/

With several server instances, a message published on one only reaches sockets connected to it. Publish through a shared broker (Redis Pub/Sub or Streams, NATS, Kafka, a managed service) that every instance subscribes to, and keep connection state out of process memory so instances can be replaced.
