"""LlamaIndex QueryEngineTool definition — test fixture."""

from llama_index.core.tools import QueryEngineTool, ToolMetadata

query_tool = QueryEngineTool(
    query_engine=None,
    metadata=ToolMetadata(
        name="document_search",
        description="Search indexed documents for answers",
    ),
)

summary_tool = QueryEngineTool(
    query_engine=None,
    metadata=ToolMetadata(
        name="summary",
        description="Summarise long documents",
    ),
)
