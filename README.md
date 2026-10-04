# YNAB MCP Server

An MCP (Model Context Protocol) server for the [YNAB (You Need A Budget)](https://www.ynab.com/) API, built with [FastMCP](https://gofastmcp.com/).

This fork is **read-only**: it exposes only the YNAB API's `GET` endpoints as MCP tools, so AI assistants like Claude can read your YNAB plans, accounts, transactions, and more, but cannot create, change, or delete anything. Any write endpoints YNAB adds to its API later stay excluded too. As a second guard, the server's HTTP client refuses to send any non-`GET` request to YNAB.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) package manager
- A YNAB account with API access

## Setup

### Get Your YNAB API Token

1. Log in to your YNAB account at [app.ynab.com](https://app.ynab.com)
2. Go to **Account Settings** → **Developer Settings**
3. Click **New Token** under "Personal Access Tokens"
4. Give your token a name and click **Generate**
5. Copy the token (you won't be able to see it again!)

## Add the Server to Your MCP Client

> **Note:** The `ynab-mcp-tools` package on PyPI is the upstream version, which
> includes write tools. To get the read-only server, run it from a clone of this
> fork, as shown below. `uv run --locked` also pins dependencies to `uv.lock`.

Clone this repository, then use its absolute path in place of
`/path/to/ynab-mcp-server` below.

### With Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": ["run", "--locked", "--directory", "/path/to/ynab-mcp-server", "ynab-mcp-server"],
      "env": {
        "YNAB_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

### With Claude Code

Use [Claude Code](https://code.claude.com/docs/en/mcp)'s MCP CLI. The `--`
separates Claude's options from the server command.

For all projects (**user** scope):

```bash
claude mcp add ynab --scope user \
  -e "YNAB_API_TOKEN=your-token-here" \
  -- uv run --locked --directory /path/to/ynab-mcp-server ynab-mcp-server
```

For the current directory only, omit `--scope user` or use `--scope local`. Use `claude mcp list` to verify and `claude mcp remove ynab --scope user` (or `local`) to uninstall.

### With Cursor

Add the following to your Cursor MCP settings (`~/.cursor/mcp.json` for global or `.cursor/mcp.json` in your project):

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": ["run", "--locked", "--directory", "/path/to/ynab-mcp-server", "ynab-mcp-server"],
      "env": {
        "YNAB_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

### With OpenCode

Add the following to your OpenCode configuration file (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "ynab": {
      "type": "local",
      "command": ["uv", "run", "--locked", "--directory", "/path/to/ynab-mcp-server", "ynab-mcp-server"],
      "enabled": true,
      "environment": {
        "YNAB_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

## Available Tools

The server exposes every `GET` endpoint in YNAB's API as an MCP tool. YNAB now calls budgets "plans". The tools include:

### User

- `getUser` - Get authenticated user information

### Plans

- `getPlans` - List all plans
- `getPlanById` - Get a single plan with all related entities
- `getPlanSettingsById` - Get plan settings
- `getPlanMonths` / `getPlanMonth` - List plan months, or get one

### Accounts

- `getAccounts` / `getAccountById`

### Categories

- `getCategories` / `getCategoryById`
- `getMonthCategoryById` - Get a category for a specific month

### Transactions

- `getTransactions` / `getTransactionById`
- `getTransactionsByAccount`, `getTransactionsByCategory`, `getTransactionsByPayee`, `getTransactionsByMonth`

### Payees

- `getPayeeById`
- `getPayeeLocations`, `getPayeeLocationById`, `getPayeeLocationsByPayee`

`getPayees` (list all payees) is excluded because its response is too large for the context window.

### Scheduled Transactions

- `getScheduledTransactions` / `getScheduledTransactionById`

### Money Movements

- `getMoneyMovements`, `getMoneyMovementsByMonth`
- `getMoneyMovementGroups`, `getMoneyMovementGroupsByMonth`

## Example Usage

Once connected, you can ask Claude things like:

- "Show me my YNAB budgets"
- "What's my current balance in my checking account?"
- "List my transactions from last week"
- "What were my biggest spending categories last month?"
- "How much have I spent on dining out this month?"

## Creating Custom Skills for Your YNAB Workflow

YNAB workflows are personal. Everyone has their own conventions for handling transactions, categorizing expenses, and managing duplicates. This repo includes a skill system that lets you encode your personal conventions so Claude can learn and apply them consistently.

### Step 1: Explore Your Budget

Start by asking Claude to do something useful with your YNAB data:

```
"Show me all my unapproved transactions"
"Help me categorize my uncategorized transactions"
"Find duplicate transactions in my budget"
```

Work through the task interactively. As you do, you'll naturally develop conventions. For example:

- "Venmo transactions always have a matching withdrawal in my checking account - I delete the Venmo one and keep the bank record"
- "Transactions from 'AMZN' should be categorized as 'Shopping' unless the memo mentions 'Kindle'"
- "Any transaction over $500 should be flagged for review"

### Step 2: Create a Skill to Encode Your Conventions

Once you've established patterns you want to reuse, create a skill to encode them. This repo includes the `skill-creator` skill in `.skills/skill-creator/` to help you build custom skills.

Ask Claude:

```
"Load the skill-creator skill and help me create a ynab skill that encodes
the conventions we just used for processing transactions"
```

The skill-creator will guide you through:

1. Identifying the reusable patterns from your workflow
2. Creating a SKILL.md file with your conventions
3. Structuring the skill for future use

### Step 3: Use Your Skills

Once created, your skills live in `.skills/` and Claude will automatically apply them when relevant. You can:

- Add more conventions as you discover them
- Share skills with others who have similar YNAB setups
- Build on the included examples

### Included Skills

- `.skills/skill-creator/` - Claude's official guide for creating new skills, included for convenience

## Resources

- [Development Guide](https://github.com/rgarcia/ynab-mcp-server/blob/main/DEVELOPMENT.md)
- [YNAB API Documentation](https://api.ynab.com/)
- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## License

MIT
