# MCP exposure design

> The MCP surface that browser-using agents talk to. Built on `fastmcp`. Streamable HTTP and stdio transports both supported.

## Why MCP is the primary surface

Two delivery paths exist:

1. **`.claude/skills/` directory drop-in.** Agentskills.io-aware tools (Claude Code, Codex, Cursor, etc.) read SKILL.md files directly. Zero process to install.
2. **MCP server.** A long-lived process exposing browser-control tools. Maintains browser sessions, runs recipes, emits traces.

The drop-in path is the lowest-friction first-touch (no install). The MCP path is the higher-leverage workflow surface — multi-step automation needs a stateful browser session, which markdown alone can't provide.

We ship **both**. The MCP server doesn't replace the drop-in; it complements it. When agentskills.io-aware tools execute a skill, they can either:
- Run the markdown's prose-instructions themselves (vision-driven, slow), OR
- Call our MCP `invoke_skill` tool (deterministic, fast).

The skill's markdown points at the MCP path as the preferred execution mode.

## Tool surface

### Browser session management

#### `start_browser`
Open a new browser session.

```yaml
input:
  headed: bool = false           # ADR-008: default headless
  context_name: str | None       # if set, reuse a persistent context (cookies/auth survive)
  ignore_https_errors: bool = false
  viewport: { width: int, height: int } = {1280, 800}
output:
  session_id: str
  warnings: list[str]            # e.g. ["HEADED_MODE_ENABLED"]
```

Errors out with `permission_denied` if `BROWSER_SKILLS_FORBID_HEADED=1` is set in the server env and `headed=true` was requested.

#### `navigate`
```yaml
input:
  session_id: str
  url: str
  wait_until: "load" | "domcontentloaded" | "networkidle" = "domcontentloaded"
output:
  page_state: PageState          # see matcher-design.md
  status: int                    # HTTP status of main document
```

#### `close_browser`
```yaml
input:
  session_id: str
output:
  trace_id: str | None           # if tracing was enabled, returns export handle
```

### Skill discovery and execution

#### `list_skills`
Return the catalog with metadata; useful for `--list` UIs and for agents that want to read descriptions in bulk.

```yaml
input: {}
output:
  skills:
    - name: str
      version: str
      description: str
      allowed_tools: list[string]
      metadata: dict
```

#### `reload_skills`
Force-invalidate the server's skill cache and re-read every `SKILL.md`
from disk. The cache also auto-invalidates on `mtime` change of any
SKILL.md or the bundle directory itself; this tool is for the case
where the user wants a deterministic "pick up my edit right now"
guarantee independent of filesystem mtime resolution.

```yaml
input: {}
output:
  skill_count: int                     # number of skills loaded
```

#### `list_applicable_skills`
Run the matcher against the current page state.

```yaml
input:
  session_id: str
output:
  candidates: list[SkillMatch]   # ordered by score desc
  rationale: str
  matched_in_ms: int
```

#### `invoke_skill`
Execute a skill against the current page.

```yaml
input:
  session_id: str
  skill_name: str
  vars: dict = {}                # values injected into the recipe (e.g., login creds)
  vision_budget: int | None      # override the skill's default; cannot exceed it
output: SkillResult              # see runner-design.md
```

### Page utilities

#### `screenshot`
```yaml
input:
  session_id: str
  selector: str | None           # if set, screenshot the element; else viewport
output:
  image_b64: str                 # PNG, base64
```

#### `page_state`
Build a `PageState` without invoking matcher or skill; useful for debugging.

```yaml
input:
  session_id: str
output: PageState
```

### Trace operations

#### `export_trace`
```yaml
input:
  trace_id: str
  redact: list[str] = []         # selectors whose contents should be blacked out
output:
  path: str                      # absolute path to the .zip on the server filesystem
  size_bytes: int
```

## Auth and access control

- **stdio transport:** trusted; the process is launched by the user, no external network.
- **streamable HTTP transport (DESIGNED, NOT YET IMPLEMENTED in v0.2):** server-side Bearer-token validation against `BROWSER_SKILLS_MCP_TOKEN` is on the v0.3 roadmap. Until then:
  - `browser-skills mcp install` does **not** offer an HTTP option — it would write a config pointing at an unauthenticated server.
  - `browser-skills mcp serve --transport=streamable-http` does still launch a server, but the user is responsible for putting it behind their own auth (Tailscale, Cloudflare Access, mTLS, etc.) before exposing it.
- **Per-session limits:** max 10 concurrent sessions (`MAX_CONCURRENT_SESSIONS` in `server.py`); new `start_browser` calls error with `too_many_sessions` until ones are closed.

The HTTP transport, when it ships with auth, is still not designed for public exposure. If users want a remote MCP, they tunnel it through their own auth on top.

## Error model

Every tool returns either `{ok: true, ...}` or `{ok: false, error: {code, message, retryable, trace_id?}}`. Error codes are a small enum:

- `session_not_found`
- `skill_not_found`
- `recipe_parse_error`
- `step_timeout`
- `vision_unavailable`
- `permission_denied`
- `navigation_blocked`
- `too_many_sessions`
- `internal`

`retryable=true` tells the agent the failure was transient. Stable failures (skill not found, recipe parse error) are `retryable=false`.

## Installation surface

`browser-skills mcp install` writes the appropriate config to:

- Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS), `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
- Cursor: `~/.cursor/mcp.json`
- Codex CLI: `~/.codex/mcp_servers.json`
- VS Code (Continue / Copilot): `~/.continue/config.json` or VS Code settings JSON
- A generic `browser-skills mcp install --print` prints the JSON snippet for copy-paste into anything else

Each writes a stanza like:

```json
{
  "mcpServers": {
    "browser-skills": {
      "command": "browser-skills",
      "args": ["mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

For HTTP:

```json
{
  "mcpServers": {
    "browser-skills": {
      "url": "http://localhost:8081/mcp",
      "headers": { "Authorization": "Bearer ${BROWSER_SKILLS_MCP_TOKEN}" }
    }
  }
}
```

## What the MCP server does NOT do

- **Doesn't expose raw Playwright.** Users wanting `page.evaluate()` should compose with `playwright-mcp` (microsoft/playwright-mcp). We deliberately don't compete on the primitives layer.
- **Doesn't proxy through Browserbase or any cloud service.** Sessions are local. Users wanting cloud browsers compose with their own provider's MCP.
- **Doesn't persist sessions across server restarts.** `context_name` reuses on-disk Playwright contexts (cookies, localStorage), but the live session ID is lost on restart.

## Testing strategy

- **Unit:** mock Playwright; assert tool inputs/outputs against schema.
- **Integration:** spin up the MCP server in-process, drive it with `fastmcp.Client`, run a full session against `pytest-httpserver` fixtures.
- **Schema-conformance:** generated tool schemas validate against the MCP spec (`tools/list` shape, `tools/call` shape).
- **Concurrency:** 10 simultaneous sessions, each running the same skill against different fixture pages, assert no session bleed.
