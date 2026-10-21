# Devscope

Devscope is a managed Deep Agent for software-development research. It is
implemented with
[`managed-deepagents`](https://github.com/langchain-ai/managed-deepagents-sdk)
and is designed to run locally through the Managed Deep Agent CLI or remotely
on LangSmith's managed LangGraph runtime.

The agent's job is to investigate technical questions, find current and
relevant sources, compare evidence, and return actionable findings with direct
citations. Its system prompt prioritizes official documentation and primary
technical sources, while the configured MCP integration provides Firecrawl
search and scraping capabilities.

> **Project status:** This repository is a proof of concept. There are
> currently no application test files, CI workflows, or checked-in evaluation
> tasks. Review the configuration notes below before deploying it for
> production use.

## Contents

- [What the agent does](#what-the-agent-does)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Request lifecycle](#request-lifecycle)
- [Runtime protections](#runtime-protections)
- [Managed sandbox](#managed-sandbox)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Install and run locally](#install-and-run-locally)
- [Build and deploy](#build-and-deploy)
- [Evaluations](#evaluations)
- [Operations](#operations)
- [Extending the agent](#extending-the-agent)
- [Known limitations and risks](#known-limitations-and-risks)
- [Contributing](#contributing)
- [Related documentation](#related-documentation)

## What the agent does

The agent is instructed to:

1. Understand the user's technical question, including relevant frameworks,
   APIs, languages, and versions.
2. Search the Firecrawl Developer Index first for programming questions.
3. Use web search for broader research and scrape important sources before
   drawing conclusions.
4. Use mapping and crawling selectively when a documentation site has multiple
   relevant pages.
5. Compare evidence, identify disagreement, and distinguish verified facts
   from assumptions or recommendations.
6. Return an executive summary, findings, implementation recommendations,
   useful code examples, trade-offs, limitations, and source URLs.

The behavior above is defined in [`instructions.md`](instructions.md), which
is loaded as the agent's system prompt. The prompt also describes a managed
durable-memory location at `/memories/agent/`.

## Architecture

```text
Caller
  |
  | x-api-key authenticated request
  v
Managed Deep Agent identity
  |
  v
define_deep_agent(name="devscope")
  |
  +--> Gemini model: google_genai:gemini-3.1-flash-lite
  |
  +--> Middleware
  |      +--> tool-call audit output
  |      +--> model-call limits
  |      +--> tool-call limits
  |      +--> email redaction
  |      +--> credit-card masking
  |
  +--> Firecrawl MCP server
  |      +--> search / developer search
  |      +--> scrape
  |      +--> map / crawl / crawl-status
  |      +--> parse
  |
  +--> Managed durable memory
         /memories/agent/

  +--> Managed sandbox
         run-scoped workspace with reusable state across turns
```

### Main components

- **Agent definition:** [`agent.py`](agent.py) registers the deployment name,
  model, and middleware stack.
- **Identity:** [`identity.py`](identity.py) authenticates callers with
  LangSmith workspace API keys and applies managed thread ownership.
- **Prompt:** [`instructions.md`](instructions.md) defines the research
  workflow, source-quality rules, output format, and memory guidance.
- **Memory:** [`memory.py`](memory.py) mounts a managed `MemoryLayer`, making
  the agent's durable memory available across runs.
- **MCP integration:** [`tools/mcp.py`](tools/mcp.py) declares the remote
  Firecrawl MCP server and the tools exposed to the agent.
- **Audit middleware:** [`middleware/audit.py`](middleware/audit.py) logs the
  start and successful completion of each tool call and re-raises failures.
- **Sandbox:** [`sandbox/__init__.py`](sandbox/__init__.py) declares the
  run-scoped managed sandbox used by the agent. The runtime owns its name,
  reuse across turns, and lifecycle.
- **Packaging:** [`pyproject.toml`](pyproject.toml) declares the Python
  version and dependencies; [`uv.lock`](uv.lock) pins the resolved
  dependency graph.

## Repository layout

```text
devscope/
├── agent.py               # Agent name, model, and middleware configuration
├── identity.py            # LangSmith API-key identity configuration
├── instructions.md        # System prompt and research policy
├── memory.py              # Managed durable-memory declaration
├── sandbox/
│   └── __init__.py        # Managed sandbox declaration and runtime defaults
├── middleware/
│   └── audit.py           # Tool-call logging middleware
├── tools/
│   └── mcp.py             # Firecrawl MCP server declaration
├── pyproject.toml         # Project metadata and direct dependencies
├── uv.lock                # Locked dependency resolution
├── .env                   # Local secrets; ignored and never committed
├── .gitignore             # Secret, build, cache, and local-output exclusions
└── README.md              # Project and operator documentation
```

`.mda/` is generated by the Managed Deep Agent CLI and is ignored by Git.
It contains compiled builds and local evaluation artifacts. `.venv/` and
Python caches are also local-only. There are no tracked `skills/` or `evals/`
directories in this checkout.

## Request lifecycle

1. A caller authenticates with a LangSmith workspace API key.
2. Managed identity associates the caller with private threads and managed
   downstream credentials.
3. The managed runtime invokes the `devscope` agent with the Gemini model.
4. The system prompt directs the model to research, compare evidence, and cite
   sources.
5. If research tools are needed, the model calls an enabled Firecrawl MCP
   tool. [`log_tool_calls`](middleware/audit.py) prints the tool name before
   execution and after successful completion.
6. Input middleware redacts email addresses and masks credit-card numbers.
7. Model and tool call limits stop runaway activity for both the current run
   and the caller's thread.
8. The managed runtime provisions or reuses the run's sandbox and applies its
   configured command timeout.
9. The response is returned through the local LangGraph server or managed
   Agent Server.

## Runtime protections

The middleware configured in [`agent.py`](agent.py) currently applies these
limits:

| Protection | Per thread | Per run | Behavior at limit |
| --- | ---: | ---: | --- |
| Model calls | 10 | 5 | End |
| Tool calls | 20 | 10 | End |

Input privacy middleware is configured as follows:

- Email addresses are **redacted**.
- Credit-card values are **masked**.

The audit middleware intentionally prints tool names and failure notices to
standard output. It does not persist a structured audit record and does not
log tool arguments. A tool exception is re-raised so the runtime can report the
failure instead of returning a success-shaped fallback.

## Managed sandbox

The [`sandbox/`](sandbox/) package enables a managed LangSmith sandbox for
run-scoped work. The managed runtime owns the sandbox name, reuses the
sandbox across turns in the same run, and handles its lifecycle. Delete the
directory to run the project without a sandbox.

The current defaults are:

| Setting | Value | Meaning |
| --- | ---: | --- |
| Idle timeout | 600 seconds (10 minutes) | Reclaim an idle sandbox after this period |
| Default command timeout | 600 seconds (10 minutes) | Maximum duration for a sandbox command unless overridden |

To provision a recipe snapshot, add `sandbox/setup.sh`.
`mda deploy` and `mda dev` bake the recipe once, and new threads clone the
snapshot without rerunning the script. Keep setup scripts reproducible and do
not place credentials in them.

## Requirements

- Python `>=3.11` (the project lockfile also resolves the configured
  `python-version` value of `3.14`).
- [`uv`](https://docs.astral.sh/uv/) for dependency management and command
  execution.
- A LangSmith account and API key for deployment and managed runtime access.
- A model-provider credential for the configured Google Gemini model.
- A Firecrawl API key if the MCP integration is enabled.
- Docker, `uv`, and the required LangSmith/model credentials for Harbor
  evaluations.

The direct dependencies are:

- `managed-deepagents==0.9.3`
- `firecrawl>=4.53.2`
- `python-dotenv>=1.2.4`
- `colorama>=0.4.6`

## Configuration

Create a local `.env` file at the repository root. It is ignored by
[`.gitignore`](.gitignore); never commit real credentials.

At minimum, configure the credentials required by the target runtime. Typical
variables include:

```dotenv
LANGSMITH_API_KEY=...
LANGSMITH_WORKSPACE_ID=...
GOOGLE_API_KEY=...
FIRECRAWL_API_KEY=...
```

The exact model-provider variable must match the Google GenAI integration
installed in the environment. `LANGSMITH_WORKSPACE_ID` is needed when the
LangSmith API key requires an explicit workspace selection.

Important configuration behavior:

- `mda deploy` loads `.env` and forwards supported provider credentials as
  deployment secrets. A value exported only in the shell may not be forwarded
  by the deployment workflow.
- [`identity.py`](identity.py) uses `auth.langsmith_api_key()`, so direct
  callers authenticate with the `x-api-key` mechanism supported by the managed
  runtime.
- [`tools/mcp.py`](tools/mcp.py) calls `load_dotenv()` and requires
  `FIRECRAWL_API_KEY` to exist at import time. The current checked-in MCP
  declaration still places a masked `"******"` value in the Authorization
  header. Verify and replace that placeholder with the runtime's supported
  secret-header mechanism before relying on Firecrawl in a deployment.

Do not put credentials in `instructions.md`, source control, log output, or
research responses.

## Install and run locally

From the repository root:

```powershell
uv sync
uv run mda dev
```

`mda dev` compiles the project and starts the local LangGraph development
server. The CLI resolves the local server for this Python project; a global
`langgraph` installation is not required.

For an interactive terminal session, use:

```powershell
uv run mda chat
```

To compile without starting a server:

```powershell
uv run mda build
```

The generated build is written under `.mda/build` and should not be committed.
When the sandbox is enabled, `mda dev` also provisions the managed sandbox
according to [`sandbox/__init__.py`](sandbox/__init__.py).

## Build and deploy

Deploy the current project to LangSmith:

```powershell
uv run mda deploy
```

Useful deployment variants:

```powershell
uv run mda deploy --name devscope-dev --deployment-type dev
uv run mda deploy --workspace-id $env:LANGSMITH_WORKSPACE_ID
uv run mda deploy --no-wait
```

The deploy command compiles the source, generates the managed LangGraph
application, uploads it to LangSmith, and prints the Agent Server and
dashboard URLs. When the sandbox is enabled, the deployment includes its
managed sandbox declaration and any `sandbox/setup.sh`
recipe snapshot. The deploy name in [`agent.py`](agent.py) is `devscope`; use a
distinct deployment name when maintaining separate environments.

To remove a deployment and the managed resources created for it:

```powershell
uv run mda delete --yes
```

Deletion is destructive: deployment resources, the associated tracing
project, Context Hub resources, managed sandboxes created by the project, and
agent memory/thread history may not be recoverable.

## Evaluations

Initialize the Harbor evaluation workspace:

```powershell
uv run mda evals init -i
```

The CLI guides the author through tasks under `evals/<task>/` and generates
`.mda/evals/`. A task may include an `identity.json` fixture with a non-empty
`user.id`; keep authored fixtures under the task directory rather than under
generated `.mda/evals/`.

Running evaluations requires Docker and the required LangSmith/model/tool
credentials. The Harbor command is generated by the CLI prompt and should be
run from the repository root. Inspect completed jobs with:

```powershell
uv run --python 3.12 --with "harbor[langsmith]==0.21.0" harbor view .mda/evals/jobs
```

This proof of concept retains Managed Deep Agent's custom Harbor adapter.
Migration to Harbor's built-in LangGraph agent is not currently implemented.

## Operations

Tail logs for a deployed agent:

```powershell
uv run mda logs
uv run mda logs --lines 200 --level error
```

In an interactive terminal, `mda logs` follows new output until interrupted.
When redirected or piped, it prints recent output and exits.

Before opening a bug report, capture:

- the command and deployment type;
- Python and `uv` versions;
- the relevant `mda` output;
- whether the problem reproduces with `uv run mda build`;
- the model/tool provider involved;
- a redacted error excerpt.

Never include API keys, cookies, personal data, or unredacted user prompts in
an issue or log attachment.

## Extending the agent

### Change the model or middleware

Edit [`agent.py`](agent.py). Preserve the `define_deep_agent(...)` entry point
and keep middleware order intentional: middleware can observe or transform
calls made by middleware earlier in the list.

### Change research behavior

Edit [`instructions.md`](instructions.md). Keep source-quality rules,
uncertainty handling, and direct URLs aligned with the actual tools available
to the agent. Do not claim a workflow step is supported unless the
corresponding tool is exposed in [`tools/mcp.py`](tools/mcp.py).

### Add or change memory

Edit [`memory.py`](memory.py) using the managed `MemoryLayer` declaration.
Treat memory as persistent state: avoid storing secrets, credentials, or
unnecessary personal data. Document any changed retention or scope behavior
in the pull request.

### Add or change the sandbox

Edit [`sandbox/__init__.py`](sandbox/__init__.py) to change sandbox lifecycle
or command-timeout defaults. Add `sandbox/setup.sh` only
when the sandbox needs a reproducible recipe snapshot; the script is baked
during `mda deploy` or `mda dev` and is not rerun for every new thread.
Validate sandbox changes with `uv run mda build` and a local `uv run mda dev`
smoke test. Do not put credentials or private data in the setup script.

### Add MCP servers or tools

Edit [`tools/mcp.py`](tools/mcp.py) and expose a named `mcp` declaration.
Use deployment-supported secret handling for credentials, keep the enabled
tool list minimal, and update this README with the new server, tools, and
required environment variables.

### Add middleware

Add focused middleware under [`middleware/`](middleware/) and register it in
[`agent.py`](agent.py). Follow the existing failure behavior: report failures
clearly and re-raise them unless the intended contract explicitly requires a
handled tool message.

## Known limitations and risks

- The repository has no automated unit, integration, or end-to-end tests.
- There is no CI workflow checked into the repository.
- A clean `mda build` reports that the managed memory directory is empty.
  This is a warning about the absence of initial memory content, not a build
  failure; add curated initial memory only if the agent needs it.
- The Firecrawl MCP authorization header is currently a masked placeholder,
  even though `FIRECRAWL_API_KEY` is required at import time. This must be
  resolved and tested before production deployment.
- Tool auditing is console output only; it is not a durable, queryable audit
  trail.
- Sandbox state is run-scoped and subject to managed-runtime lifecycle rules;
  it should not be treated as durable memory. Use [`memory.py`](memory.py) for
  durable agent memory.
- The configured model identifier is provider- and account-dependent. Model
  availability and quota must be verified in the deployment environment.
- The system prompt asks the agent to use mapping and crawling, but only the
  tools explicitly included in the MCP declaration are available at runtime.
- The default runtime limits may truncate complex research tasks. Adjust them
  deliberately and validate cost, latency, and answer quality.
- `uv.lock` contains the resolved environment, but changing Python versions or
  dependencies requires regenerating and reviewing the lockfile.

## Contributing

Read [`contribute.md`](contribute.md) for the development workflow, change
guidelines, validation checklist, and pull-request expectations.

## Related documentation

- [Managed Deep Agents quickstart](https://docs.langchain.com/langsmith/python/managed-deep-agents-quickstart)
- [Managed Deep Agents SDK](https://github.com/langchain-ai/managed-deepagents-sdk)
- [uv documentation](https://docs.astral.sh/uv/)
- [LangSmith](https://smith.langchain.com/)
- [Firecrawl MCP](https://docs.firecrawl.dev/mcp)
