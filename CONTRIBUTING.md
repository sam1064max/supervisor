# Contributing

Thanks for taking the time to contribute.

## Development setup

```bash
git clone https://github.com/sam1064max/supervisor.git
cd supervisor
uv sync --all-extras --dev
```

You will need Python 3.10+ and [`uv`](https://docs.astral.sh/uv/). No API
keys are required for development - the `fake` provider is the default.

## Workflow

1. Branch from `main` (`git switch -c feat/my-change`).
2. Make your change.
3. Add or update tests.
4. Run the quality gates locally:

   ```bash
   make ci    # or: uv run ruff check . && uv run black --check . && \
   #           uv run mypy src tests && uv run pytest --cov=src
   ```

5. Open a pull request. The CI workflow will re-run all gates.

## Coding conventions

- **Type hints** are mandatory for public functions. Mypy is strict.
- **No `eval`** in any code path; the calculator uses an AST whitelist.
- **Logs** go through `structlog` via `logging_setup.get_logger`.
- **Public API** is exported from `src/supervisor/__init__.py`.
- **Tests** mirror the source layout in `tests/unit/`, `tests/integration/`,
  `tests/failure/`, `tests/regression/`, `tests/edge/`.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>
```

- `feat` - new user-visible functionality
- `fix` - bug fix
- `chore` - maintenance (deps, tooling)
- `docs` - documentation only
- `refactor` - code change that neither fixes a bug nor adds a feature
- `test` - add or update tests
- `build` - build system / CI

## Architecture decisions

Non-trivial decisions go in `docs/adr/`. Use the existing ADRs as a template
(Mermaid diagram + status + consequences).

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug.yml). Do not
include secrets in the report.
