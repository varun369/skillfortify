"""Basic LlamaIndex FunctionTool definitions — test fixture."""

from llama_index.core.tools import FunctionTool


def multiply(a: int, b: int) -> int:
    """Multiply two numbers together."""
    return a * b


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


multiply_tool = FunctionTool.from_defaults(fn=multiply)
add_tool = FunctionTool.from_defaults(
    fn=add,
    name="addition",
    description="Add two integers",
)
