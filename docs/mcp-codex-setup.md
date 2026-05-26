# Engram Codex MCP Setup Guide

Engram integrates with custom Model Context Protocol (MCP) clients such as Cursor, Claude Desktop, or Codex. It exposes its persistent local memory, active tasks, phases, and structured startup contexts directly to AI agents via a fast, local-first STDIO transport.

This guide details how to install the MCP adapter, initialize a project, register the server, and troubleshoot common issues.

---

## 1. Installation

To enable MCP capabilities, install Engram with the optional `mcp` extra.

From the root directory of your Engram installation:

```bash
uv pip install -e ".[mcp]"
```

Or, if installing as a standard package:

```bash
uv pip install -e .
```

*Note: The `[mcp]` extra installs the standard `mcp` Python SDK (version `>=1.0,<2.0`), which provides the fast STDIO server runner.*

---

## 2. Project Initialization

Engram is project-bound. It resolves memory database entries and active tasks using the working directory from which the MCP server is launched. Before connecting your agent, initialize the directory as an Engram project:

```bash
engram init --name "engram"
```

This binds the current directory to Engram's database. If this directory has already been initialized, `engram init` will safely re-bind or report the existing project connection.

---

## 3. Codex Custom MCP Configuration

The custom MCP screen in Codex allows registering STDIO servers. Connect Engram by supplying the following parameters:

### Configuration Fields

| Field Name | Value to Configure | Description |
| :--- | :--- | :--- |
| **Name** | `engram` | A unique identifier for the MCP server. |
| **Transport** | `STDIO` | The standard input/output transport channel. |
| **Command** | `engram-mcp` | The executable entrypoint for the Engram MCP server. |
| **Arguments** | *None* | Leave empty. |
| **Working Directory** | `d:\MASTER\03_CODE\Repos\engram` | **Must** be set to your exact initialized project root. |

> [!IMPORTANT]
> The **Working Directory** must be the exact absolute path to your initialized project root directory where you ran `engram init`. Engram uses this path on startup to resolve the active project.

---

## 4. Verification and Testing

Once the server is registered in your agent client, you can verify that it is connected and operating correctly. Ask your agent the following test queries:

### Test 1: Verify Project Binding
Ask your agent to invoke the `engram_project_current` tool:
```text
Verify my current Engram project connection.
```
**Expected Response:** A JSON object confirming `ok: true` and listing the project metadata:
```json
{
  "ok": true,
  "project": {
    "id": "sai937593-engram",
    "name": "engram",
    "summary": "Local-first agentic persistent memory system",
    "repo_path": "d:/MASTER/03_CODE/Repos/engram"
  }
}
```

### Test 2: Verify Startup Context
Ask your agent to read the `engram://startup` resource:
```text
Retrieve the startup context for this project.
```
**Expected Response:** The structured markdown representation of the current project frame, active tasks, guardrails, and memory candidates.

---

## 5. Troubleshooting

If you encounter errors during setup or execution, refer to the solutions below.

### 5.1 Error: `PROJECT_NOT_BOUND`
* **Symptoms:** The MCP server launches, but calling any tool or resource returns an error object with code `PROJECT_NOT_BOUND` (e.g. `"code": "PROJECT_NOT_BOUND"`).
* **Cause:** The working directory configured in Codex does not match any project initialized in Engram's SQLite database, or no project has been initialized yet.
* **Resolution:**
  1. Open a terminal in the target repository directory.
  2. Run `engram init --name "engram"`.
  3. Verify that the **Working Directory** field in your Codex custom MCP configuration is set to that exact directory path.
  4. Restart the MCP server in your agent client.

### 5.2 Error: Missing `engram-mcp` Executable
* **Symptoms:** Codex fails to connect, and logs indicate the command `engram-mcp` could not be found or executed.
* **Cause:** The virtual environment containing Engram's console scripts is not active, or the path to its executable is not in the system's `PATH`.
* **Resolution:**
  * **Option A (Recommended):** Provide the full absolute path to the executable inside your virtual environment. For example:
    * **Windows:** `d:\MASTER\03_CODE\Repos\engram\.venv\Scripts\engram-mcp.exe`
    * **macOS/Linux:** `/path/to/engram/.venv/bin/engram-mcp`
  * **Option B:** Run the server using `uv run`:
    * **Command:** `uv`
    * **Arguments:** `run engram-mcp`
  * **Option C:** Ensure the active virtual environment's bin/Scripts directory is added to your system environment variables.

### 5.3 Error: `Missing optional MCP dependency`
* **Symptoms:** The server starts but immediately crashes with a `RuntimeError` message:
  `Missing optional MCP dependency. Install it with: uv pip install "engram[mcp]"`
* **Cause:** Engram was installed without the optional `[mcp]` dependencies.
* **Resolution:** Run the installation command in your active python environment:
  ```bash
  uv pip install -e ".[mcp]"
  ```
