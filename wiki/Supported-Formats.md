# Supported Formats -- 22 Agent Frameworks

SkillFortify auto-detects and analyzes agent skills across 22 agent frameworks as of v0.3.0. All formats are parsed into a unified internal representation for consistent analysis, trust scoring, lockfile generation, and SBOM output. You do not need to specify which framework your project uses -- SkillFortify detects it automatically.

Run `skillfortify frameworks` to see the full table in your terminal.

---

## Framework Reference

### Tier 1: Major AI Platforms

| # | Framework | Format ID | Detection Pattern |
|---|-----------|-----------|-------------------|
| 1 | **Claude Code Skills** | `claude` | `.claude/skills/*.md` |
| 2 | **MCP Configs** | `mcp` | `mcp.json`, `mcp_config.json` |
| 3 | **MCP Servers** | `mcp_server` | Server files using MCP SDK |
| 4 | **OpenClaw** | `openclaw` | `.claw/*.yaml` |
| 5 | **OpenAI Agents SDK** | `openai_agents` | `@function_tool`, `Agent()` |
| 6 | **Google ADK** | `google_adk` | Google ADK imports |
| 7 | **Anthropic Agent SDK** | `anthropic_sdk` | `@tool`, `MCPServer` |

### Tier 2: Orchestration Frameworks

| # | Framework | Format ID | Detection Pattern |
|---|-----------|-----------|-------------------|
| 8 | **LangChain** | `langchain` | `BaseTool`, `@tool` |
| 9 | **CrewAI** | `crewai` | `crew.yaml` |
| 10 | **AutoGen** | `autogen` | `@register_for_llm` |
| 11 | **Semantic Kernel** | `semantic_kernel` | `@kernel_function` |
| 12 | **LlamaIndex** | `llamaindex` | `FunctionTool`, `ReActAgent` |
| 13 | **PydanticAI** | `pydanticai` | `@agent.tool` |
| 14 | **Haystack** | `haystack` | `Pipeline`, `Tool` |

### Tier 3: Agent Frameworks

| # | Framework | Format ID | Detection Pattern |
|---|-----------|-----------|-------------------|
| 15 | **Agno (Phidata)** | `agno` | `Agent()`, `Toolkit` |
| 16 | **CAMEL-AI** | `camel` | `ChatAgent`, `RolePlaying` |
| 17 | **MetaGPT** | `metagpt` | `Role`, `Action`, `@register_tool` |
| 18 | **Composio** | `composio` | `Action`, `App`, `@action` |
| 19 | **Mastra** | `mastra` | `createTool()` (TypeScript) |

### Tier 4: Workflow Builders

| # | Framework | Format ID | Detection Pattern |
|---|-----------|-----------|-------------------|
| 20 | **n8n** | `n8n` | `*.workflow.json` |
| 21 | **Flowise** | `flowise` | Chatflow JSON files |
| 22 | **Dify Plugins** | `dify` | `manifest.yaml` |

---

## System Auto-Discovery (23 IDE Profiles)

When you run `skillfortify scan` with no arguments, SkillFortify probes 23 known IDE and AI tool locations on your system:

| IDE/Tool | Location Probed |
|----------|----------------|
| Claude Code | `~/.claude/` |
| Cursor | `~/.cursor/` |
| VS Code | Platform-specific config directory |
| Windsurf/Codeium | `~/.codeium/` |
| Gemini CLI | `~/.gemini/` |
| OpenCode | `~/.opencode/` |
| Cline | `~/.cline/` |
| Continue | `~/.continue/` |
| GitHub Copilot | `~/.copilot/` |
| n8n | `~/.n8n/` |
| Roo Code | `~/.roo/` |
| Trae | `~/.trae/` |
| Kiro | `~/.kiro/` |
| Kode | `~/.kode/` |
| Jules | `~/.jules/` |
| Junie | `~/.junie/` |
| Codex CLI | `~/.codex/` |
| SuperVS | `~/.supervs/` |
| Zencoder | `~/.zencoder/` |
| CommandCode | `~/.commandcode/` |
| Factory | `~/.factory/` |
| Qoder | `~/.qoder/` |
| VS Code (Linux) | `~/.config/Code/` |

Each location is checked for MCP configuration files and skill directories. If an AI tool is installed but has no skills configured, it appears in the discovery table with "(no skills detected)".

---

## Mixed-Framework Projects

A project can contain skills in multiple frameworks. All are detected and analyzed together:

```bash
my-project/
  .claude/skills/deploy.md     # Claude Code skill
  mcp.json                     # MCP server configs
  tools/search.py              # LangChain tool
  crew.yaml                    # CrewAI config

skillfortify scan ./my-project
# All four frameworks detected
```

---

## Unified Analysis

Regardless of the original format, all skills go through the same analysis pipeline:

1. **Parsing**: Format-specific parser extracts capabilities, resources, and metadata
2. **Normalization**: Parsed data is converted to a unified skill representation
3. **Capability inference**: Formal analysis determines what the skill can access
4. **Finding detection**: Capabilities are compared against declarations and patterns
5. **Trust scoring**: Trust signals are evaluated for the skill
6. **Reporting**: Results are presented in the unified output format

A CRITICAL finding on a Claude Code skill means the same thing as a CRITICAL finding on a LangChain tool.

---

## Adding Support for New Formats

SkillFortify is designed to be extensible. If you use an agent framework not currently supported:

1. **Request support**: Open an issue on [GitHub](https://github.com/varun369/skillfortify/issues)
2. **Contribute a parser**: See [CONTRIBUTING.md](https://github.com/varun369/skillfortify/blob/main/CONTRIBUTING.md)

---

## Further Reading

- **[Getting Started](Getting-Started)** -- First scan walkthrough with output explanation
- **[CLI Reference](CLI-Reference)** -- Full command options including system scan and dashboard
- **[SkillFortifyBench](SkillFortifyBench)** -- How frameworks are represented in the benchmark

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
