---
title: "Use bounded asynchronous overload responses"
status: accepted
category: decisions
created: 2026-07-13
updated: 2026-07-13
tags: [http, reliability, security, performance, windows]
related:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-19-bounded-overload-responses.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0041
type: decision
deciders: [maintainers]
---

# ADR-0041: Use bounded asynchronous overload responses

## Context

The control API bounds normal HTTP concurrency with a semaphore. The original
saturation path wrote a fixed 503 response and closed the accepted socket on
the server's accept loop. On Windows, closing a TCP socket while the peer's
request bytes remain unread can replace the response with an abortive reset.
The same path also allowed each rejected connection to hold the accept loop in
socket I/O for up to half a second.

Draining input synchronously would improve response delivery but would turn
slow rejected clients into accept-loop head-of-line blocking. Creating an
unbounded thread for every rejected connection would move rather than solve
the resource-exhaustion risk.

## Decision

Keep normal request capacity and overload-response capacity independent and
hard-bounded. When normal capacity is exhausted, acquire one of four overload
slots without waiting and dispatch a daemon worker. If no overload slot is
available, close the new connection immediately.

An overload worker sends the fixed 503 response, half-closes the response side,
and drains peer input before closing. Both the drain volume and total wall time
are bounded: no more than the configured request-body cap plus 64 KiB of
framing, and 250 ms. Socket failures still close the request and release
capacity. Failure to start the worker restores its slot before the normal
server error boundary handles the accepted socket.

## Consequences

- Ordinary saturated clients receive the documented response reliably on
  Windows instead of intermittently observing a connection reset.
- Slow or trickling rejected clients cannot block the accept loop or retain an
  overload worker beyond the fixed deadline.
- Normal work remains isolated from overload-response work.
- A burst beyond both hard caps is deliberately shed with an immediate close;
  best-effort diagnostics never override resource safety.
- Four additional short-lived daemon threads are the maximum overload cost,
  with no queued rejected work.

## Alternatives

- **Drain the request on the accept loop.** Rejected because each slow client
  could serialize acceptance for the drain timeout.
- **Close immediately after sending 503.** Rejected because unread request data
  can turn the close into a Windows TCP reset and discard the response.
- **Create one unrestricted thread per rejected connection.** Rejected because
  an overload path must not introduce unbounded thread or memory growth.
- **Parse and consume the declared HTTP body completely.** Rejected because a
  malicious length or trickle could retain overload capacity; bounded
  best-effort draining is sufficient.
- **Queue rejected connections in a general executor.** Rejected because a
  default executor queue is not a strict admission-control boundary.
