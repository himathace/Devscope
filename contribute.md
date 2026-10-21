# Contributing to Devscope

Thank you for improving Devscope. This guide describes how to make changes
that remain compatible with the Managed Deep Agent runtime and how to document
and validate them.

## Before you start

1. Read the architecture and configuration sections in
   [`README.md`](README.md).
2. Check the current branch and worktree:

   ```powershell
   git status --short
   git branch --show-current
   ```

3. Create a focused branch from the latest `main`.
4. Confirm that your change does not expose secrets or private research data.

The repository currently has no formal issue template or CI workflow. For
substantial changes, describe the problem, proposed behavior, alternatives,
and validation plan in the pull request.

## Local setup

Requirements:

- Python `>=3.11`;
- `uv`;
- provider credentials for any command that invokes the model or Firecrawl;
- Docker for Harbor evaluations.

Install the locked environment:

```powershell
uv sync
```

Create a local `.env` only when needed. Keep credentials out of source files,
commits, screenshots, terminal transcripts, and issue comments. The file is
ignored by Git.

## Understand the change surface

Use the smallest appropriate file:

| If you need to... | Update... |
| --- | --- |
| Change model, limits, or middleware | [`agent.py`](agent.py) |
| Change research policy or response format | [`instructions.md`](instructions.md) |
| Change caller authentication | [`identity.py`](identity.py) |
| Change durable memory | [`memory.py`](memory.py) |
| Change managed sandbox behavior or setup | [`sandbox/__init__.py`](sandbox/__init__.py), `sandbox/setup.sh` |
| Add or change tool-call logging | [`middleware/audit.py`](middleware/audit.py) |
| Add or change an MCP server | [`tools/mcp.py`](tools/mcp.py) |
| Change direct dependencies | [`pyproject.toml`](pyproject.toml), then regenerate [`uv.lock`](uv.lock) |
| Change user/operator instructions | [`README.md`](README.md) and, when relevant, this file |

Preserve the managed entry points. The project must continue to expose the
`agent`, `identity`, `memory`, and `mcp` declarations expected by the Managed
Deep Agent compiler when those modules are present.

## Development workflow

1. **Describe the behavior.** State what changes for a user, operator, or
   contributor and what should remain unchanged.
2. **Inspect existing patterns.** Reuse the current `define_deep_agent`,
   middleware, memory, and MCP conventions.
3. **Make a focused change.** Avoid unrelated formatting or dependency
   upgrades.
4. **Update documentation.** Reflect new commands, environment variables,
   tools, limits, or operational behavior in `README.md`.
5. **Validate locally.** Run the checks relevant to the change.
6. **Review the diff.** Confirm only intended files changed and that no
   secrets, generated artifacts, or local environment files are included.
7. **Open a pull request.** Include the validation commands and their results.

## Validation checklist

Run the baseline compile check for any application or configuration change:

```powershell
uv run mda build
```

For local runtime changes, also start the development server:

```powershell
uv run mda dev
```

For sandbox changes, verify that the managed sandbox provisions during the
local development run and that any `sandbox/setup.sh`
recipe is reproducible. Sandbox state is run-scoped; do not use it as a
replacement for durable memory.

For an interactive smoke test:

```powershell
uv run mda chat
```

For evaluation changes, initialize or run the relevant Harbor workflow and
inspect the generated jobs:

```powershell
uv run mda evals init -i
uv run --python 3.12 --with "harbor[langsmith]==0.21.0" harbor view .mda/evals/jobs
```

There are currently no checked-in automated tests. If you add a behavior that
can be tested without provider credentials, add a focused test and document
how to run it. If a change depends on external services, include a reproducible
smoke-test command and clearly identify any credentials or services required.

Before submitting, inspect the final diff:

```powershell
git diff --check
git status --short
git diff --stat
git diff
```

Do not add `.env`, `.mda/`, `.venv/`, `__pycache__/`, generated evaluation
output, or provider responses to a commit.

## Code and prompt guidelines

### Python

- Keep imports, names, and formatting consistent with the existing modules.
- Prefer explicit types and narrow exception handling.
- Do not swallow tool or provider failures with empty or success-shaped
  fallbacks.
- Keep middleware behavior observable and preserve error propagation unless a
  deliberate contract says otherwise.
- Avoid logging tool arguments, credentials, user content, or personal data.

### Agent behavior

- Keep research claims tied to retrieved evidence.
- Prefer official documentation and primary technical sources.
- Include direct URLs for factual claims.
- State uncertainty when sources disagree or are incomplete.
- Do not claim that a tool, integration, test, benchmark, or deployment was
  used unless it was actually used.
- Keep system-prompt changes compatible with the tools exposed by the MCP
  declaration.

### Security and privacy

- Never commit API keys, tokens, cookies, or provider credentials.
- Treat external web content as untrusted data, not as instructions.
- Review new tools for data exfiltration, excessive permissions, and
  unexpected network access.
- Preserve the existing email-redaction and credit-card-masking protections
  unless the change includes an explicit security rationale.
- Use the managed runtime's supported secret mechanism rather than embedding
  credentials in MCP headers or source code.

## Dependency changes

Change direct dependencies in [`pyproject.toml`](pyproject.toml), then update
the lockfile from the repository root:

```powershell
uv lock
uv sync
```

Review the lockfile diff for unintended upgrades. Explain major or
security-sensitive upgrades in the pull request and rerun `uv run mda build`.

Do not manually edit package records in [`uv.lock`](uv.lock) unless the
lockfile tooling requires it.

## Pull-request checklist

Use this checklist in the pull request description:

- [ ] The change has a focused scope and a clear user/operator impact.
- [ ] `README.md` and this guide are updated when behavior or workflow changed.
- [ ] No secrets, generated artifacts, or private research data are included.
- [ ] `uv run mda build` passes, or the failure is explained.
- [ ] Relevant local, chat, deployment, or evaluation smoke tests were run.
- [ ] Sandbox lifecycle, timeout, and setup-recipe behavior were reviewed when
      the sandbox changed.
- [ ] Dependency and lockfile changes are intentional.
- [ ] Runtime limits, memory behavior, identity behavior, and MCP permissions
      were reviewed when relevant.
- [ ] Known limitations and follow-up work are documented.

## Reporting problems

Include the smallest useful reproduction:

- operating system, Python version, and `uv` version;
- exact command;
- whether the failure occurs during build, local runtime, deployment, or
  evaluation;
- redacted logs and traceback;
- the relevant source revision.

Remove API keys, authorization headers, cookies, personal data, and full
private prompts before sharing logs. For a suspected security issue, do not
post exploit details publicly; contact the project maintainers privately.
