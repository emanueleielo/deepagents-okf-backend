# Security Policy

## Supported Versions

The latest released `0.x` version receives security fixes. This project is
pre-1.0 and the API may change between minor versions.

## Reporting a Vulnerability

Please **do not** open a public issue for security problems.

Instead, use GitHub's [private vulnerability reporting](https://github.com/emanueleielo/deepagents-okf-backend/security/advisories/new)
or email **emanueleielo@gmail.com**. You can expect an initial response within a
few days.

## Security notes for this backend

`OKFBackend` reads and writes **real files** under the directory you pass as `root`.

- The backend sandboxes all agent-supplied paths to `root` (path traversal such as
  `../` is rejected). This is covered by tests.
- Still, point `root` at a **dedicated bundle directory**, never at a path that
  contains secrets, credentials, or system files. An agent with write access to a
  shared directory can modify anything inside it.
- For untrusted/hostile workloads prefer an isolated sandbox backend.
