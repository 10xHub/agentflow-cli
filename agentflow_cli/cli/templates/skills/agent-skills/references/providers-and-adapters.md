# Providers and Adapters

Use this when changing OpenAI, Google Gemini, Vertex AI, reasoning, response conversion, or third-party tool adapters.

## Providers

`Agent` supports OpenAI and Google provider flows through provider-specific internal modules:

- OpenAI: `agentflow/agentflow/core/graph/agent_internal/openai.py`
- Google: `agentflow/agentflow/core/graph/agent_internal/google.py`
- Provider inference/helpers: `agentflow/agentflow/core/graph/agent_internal/providers.py`

Provider docs live in:

- `agentflow-docs/docs/providers/openai.md`
- `agentflow-docs/docs/providers/google.md`

## Environment Variables

OpenAI:

- `OPENAI_API_KEY`

Google Gemini API:

- `GEMINI_API_KEY`
- `GOOGLE_API_KEY` fallback

Vertex AI:

- `GOOGLE_GENAI_USE_VERTEXAI=true`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_APPLICATION_CREDENTIALS`

## Reasoning

Reasoning config is provider-specific:

- OpenAI style: effort and summary options where supported.
- Google style: effort mapped to thinking budget or explicit `thinking_budget`.

Check provider capability and converter behavior before adding new reasoning fields.

## LLM Converters

Runtime converter exports:

- `BaseConverter`
- `GoogleGenAIConverter`
- `OpenAIConverter`
- `OpenAIResponsesConverter`
- `ModelResponseConverter`
- `reasoning_utils`

Converters normalize provider-native responses into Agentflow `Message`, content blocks, usage, reasoning, and tool call structures.

## Tool Adapters

Third-party adapters:

- `LangChainAdapter`: registers LangChain tools and exposes LLM-compatible schemas.
- `ComposioAdapter`: integrates Composio tools where dependency is installed.

Tool execution precedence in `ToolNode` is MCP, Composio, LangChain, then local tools, with remote tool checks before local execution where configured.

## Rules

- Use official provider SDKs through existing provider modules.
- Do not leak provider-native response shapes past converter boundaries unless stored in `Message.raw`.
- Keep optional provider/tool dependencies optional and guarded.
- Update provider docs and tests when adding provider-specific behavior.
- Verify multimodal and tool-call behavior for each provider separately.

## Source Map

- Agent internals: `agentflow/agentflow/core/graph/agent_internal`
- LLM adapters: `agentflow/agentflow/runtime/adapters/llm`
- Tool adapters: `agentflow/agentflow/runtime/adapters/tools`
- Provider docs: `agentflow-docs/docs/providers`
- Agent docs: `agentflow-docs/docs/reference/python/agent.md`
