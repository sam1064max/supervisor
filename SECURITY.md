# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x   | yes       |
| < 0.1   | no        |

## Reporting a vulnerability

Please **do not** file a public issue for security problems.

Email: **sam1064max@gmail.com** (PGP key on request).

We will acknowledge within 3 business days and aim to ship a fix within
30 days for high-severity issues.

## Scope

The Supervisor orchestrates LLM calls and does not store user data. The
relevant attack surface is:

- **Prompt injection** in user input - mitigated by the input guardrail.
- **Unsafe code execution** in the calculator - mitigated by AST whitelist
  (no `eval`, no name lookups, no attribute access, no calls outside the
  function whitelist).
- **Credential leakage** in logs - the library never logs the `llm_api_key`.
- **Excessive resource use** - `max_input_length`, `max_review_cycles`,
  and the per-call `max_tokens` cap.

## Best practices for deployment

- Use a secret store (Vault, AWS Secrets Manager) for API keys - never commit
  `.env` files.
- Set `LOG_LEVEL=INFO` (or `WARNING`) in production to avoid PII leakage.
- Mount a persistent checkpoint store if you need resumability.
- Run the Docker image as a non-root user (it does, by default) and apply
  a read-only root filesystem where possible.
- Use a network policy to limit outbound traffic to known LLM endpoints.
