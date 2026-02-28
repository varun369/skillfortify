"""CAMEL-AI project using multiple toolkits and FunctionTool wrapping."""
from camel.agents import ChatAgent
from camel.toolkits import (
    CodeExecutionToolkit,
    FunctionTool,
    GoogleMapsToolkit,
    SearchToolkit,
)
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

search_toolkit = SearchToolkit()
code_toolkit = CodeExecutionToolkit()
maps_toolkit = GoogleMapsToolkit()

tools = [
    FunctionTool(search_toolkit.search_google),
    FunctionTool(code_toolkit.execute),
    FunctionTool(maps_toolkit.get_directions),
]

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

agent = ChatAgent(
    system_message="You are a multi-skilled assistant",
    model=model,
    tools=tools,
)
