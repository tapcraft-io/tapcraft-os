# LLM-Based Workflow Generation

Tapcraft uses AI (OpenAI GPT-4) to automatically generate workflow graphs and Temporal code from natural language prompts.

## How It Works

```
User: "Fetch unread emails and send a count to Slack"
    ↓
LLM analyzes available app operations and primitives
    ↓
Generates structured GraphSpec (nodes + edges)
    ↓
Code generator creates Temporal workflow code
    ↓
Worker executes the workflow
```

## Setup

### 1. Get an OpenAI API Key

Sign up at https://platform.openai.com/ and create an API key.

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Required for LLM-based generation
OPENAI_API_KEY=sk-...

# Optional: Choose model (default: gpt-4o)
TAPCRAFT_GRAPH_MODEL=gpt-4o

# Database
DATABASE_URL=sqlite+aiosqlite:///./tapcraft.db

# Temporal
TEMPORAL_ADDRESS=localhost:7233
TASK_QUEUE=default
```

### 3. Run the Test

```bash
# Install dependencies
poetry install

# Run LLM workflow generation test
poetry run python test_llm_workflow.py
```

## What the LLM Does

The LLM graph generator (`LLMGraphGenerator`):

1. **Receives context** about:
   - User's natural language prompt
   - Available app operations (from database)
   - Built-in primitives (HTTP, delay, log)

2. **Generates structured output** (`GraphSpec`):
   - Workflow name and description
   - Complete node list (triggers, operations, primitives)
   - Edge connections showing flow
   - Reasoning about design choices

3. **Returns machine-readable graph** that:
   - Maps to database models (Node, Edge)
   - Generates Temporal workflow code
   - Executes on the worker

## Example Prompts

### Simple Email to Slack
```
Prompt: "Every morning, fetch my unread emails and send a count to Slack #general channel"

Generated Graph:
  Trigger (cron) → Fetch Unread Emails → Send Slack Message
```

### Email Archive to Notion
```
Prompt: "Get unread emails, create a Notion page for each one, then mark them as read"

Generated Graph:
  Trigger → Fetch Unread → Create Notion Page → Mark as Read
```

### Multi-App Orchestration
```
Prompt: "Fetch emails, save important ones to Notion, send summary to Slack, mark all read"

Generated Graph:
  Trigger → Fetch Emails → Create Notion Page → Send Slack Message → Mark as Read
```

## LLM Architecture

### Models

**`GraphSpec`** (Pydantic model for structured output):
```python
class GraphSpec(BaseModel):
    name: str                      # "Daily Email Digest"
    description: str               # Full workflow description
    nodes: List[NodeSpec]          # All workflow steps
    edges: List[EdgeSpec]          # Connections
    entry_node_temp_id: str        # Where to start
    reasoning: Optional[str]       # LLM's thought process
    estimated_complexity: str      # simple/medium/complex
```

**`NodeSpec`** (Individual workflow step):
```python
class NodeSpec(BaseModel):
    temp_id: str                   # "trigger", "fetch_emails"
    kind: str                      # "trigger", "app_operation", "primitive"
    label: str                     # "Fetch Unread Emails"
    app_operation_id: Optional[int]  # Links to database operation
    primitive_type: Optional[str]    # "http_request", "delay"
    config: Dict[str, Any]          # Node-specific configuration
    ui_position: Dict[str, int]     # Canvas position {"x": 100, "y": 100}
```

### System Prompt

The LLM is instructed to:

1. **Start with a trigger** - Every workflow needs an entry point
2. **Use available operations** - Only reference operations from the database
3. **Create linear flows** - For v1, simple A → B → C patterns
4. **Use primitives when needed** - HTTP, delay, log for generic tasks
5. **Provide reasoning** - Explain design choices

### Constraints

The LLM is given:
- **Available apps** with their operations and config schemas
- **Built-in primitives** (HTTP request, delay, log)
- **Workflow rules** (deterministic, activity-based side effects)

## Code Generation

After the LLM generates the graph, `CodeGeneratorService`:

1. Walks nodes in topological order
2. Generates `@workflow.defn` class
3. Maps each node to:
   - `workflow.execute_activity()` for app operations
   - Built-in workflow calls for primitives
4. Adds retry policies and timeouts
5. Returns valid Temporal Python code

## Fallback Mode

If `OPENAI_API_KEY` is not set:
- Uses simple keyword matching
- Creates basic linear workflows
- Still functional, just less intelligent

## Costs

Using GPT-4o for workflow generation:
- ~500-1000 tokens per workflow (input)
- ~300-800 tokens per workflow (output)
- Cost: $0.01-0.05 per workflow

Recommendation: Start with `gpt-4o-mini` for testing:
```bash
TAPCRAFT_GRAPH_MODEL=gpt-4o-mini
```

## API Usage

### Create Workflow via API

```bash
curl -X POST http://localhost:8000/agent/workflows?workspace_id=1 \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "Fetch emails and send to Slack",
    "available_apps": null
  }'
```

Response:
```json
{
  "workflow": { "id": 1, "name": "Email To Slack", ... },
  "graph": { "id": 1, "nodes": [...], "edges": [...] },
  "code_preview": "...",
  "agent_session_id": 1
}
```

### Get Generated Code

```bash
curl http://localhost:8000/agent/workflows/1/code
```

## Troubleshooting

### "pydantic_ai.exceptions.UserError"
- Check that `OPENAI_API_KEY` is set correctly
- Verify API key has credits

### "Rate limit exceeded"
- Adjust `AGENT_RATE_LIMIT_RPM` in `.env`
- Add delays between generations

### "Model not found"
- Verify model name (gpt-4o, gpt-4o-mini)
- Check OpenAI account has access to model

## Next Steps

Future enhancements:
- **Conditional logic** - Support branching (if/else)
- **Loops** - Iterate over collections
- **Error handling** - Explicit error paths
- **Code refinement** - LLM-assisted code generation
- **Multi-agent** - Different LLMs for planning vs coding
