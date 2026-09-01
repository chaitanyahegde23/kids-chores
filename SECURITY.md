# Security policy

## Supported version

Security fixes are applied to the latest commit on the `main` branch.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** option in the repository Security tab. Do not open a public issue for a suspected vulnerability and do not include household data, credentials, access tokens, PINs, or session material in reports.

Include a concise description, affected component, reproduction steps using synthetic data, and the potential impact. Maintainers will acknowledge a report as soon as practical and coordinate disclosure after a fix is available.

## Deployment responsibility

Kids Chores is self-hosted software. Operators are responsible for HTTPS, access controls, host patching, backups, unique production credentials, and keeping the application behind a trusted authentication boundary. The four-digit parent PIN is not a substitute for internet-facing authentication.