name: Pull request
about: Contribute code or docs
---

## Summary

<!-- 1-2 sentences. -->

## Related issues

<!-- Link any related issues. -->

## Checklist

- [ ] `uv run ruff check .` is clean
- [ ] `uv run black --check .` is clean
- [ ] `uv run mypy src tests` is clean
- [ ] `uv run pytest --cov=src` passes (coverage >= 80%)
- [ ] New behaviour is covered by tests
- [ ] Docs updated (README, ADRs, or `docs/`)
- [ ] Conventional commit title
