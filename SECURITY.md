# Security policy

Griha is a hackathon prototype that handles **synthetic data only**. It is written as if for real personal and financial data, and the controls are listed in [docs/security.md](docs/security.md), including the honest "not built" rows.

## Reporting a vulnerability

Please do **not** open a public issue for a security problem. Use GitHub's private vulnerability reporting: **Security tab → Report a vulnerability** on this repository. Include what you found, how to reproduce it, and the impact you see.

You can expect an acknowledgement within a few days. This is a student project without a security team, so there is no bounty and no formal SLA, but reports are taken seriously and credited if you wish.

## Scope

In scope: the API, the case-access model (capability keys), encryption and key handling, the audit chain, input handling, and the Docker image.

Out of scope: the demo credentials (`officer@griha.demo`, `admin@griha.demo`, password `griha-demo`) which are published on purpose and only protect synthetic data; denial of service against the small hosted demo; findings that need physical access to the host.

## Supported versions

Only the `main` branch.
