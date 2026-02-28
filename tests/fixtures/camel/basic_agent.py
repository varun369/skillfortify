"""Basic CAMEL-AI ChatAgent with a single tool."""
from camel.agents import ChatAgent
from camel.toolkits import FunctionTool, SearchToolkit
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

search_toolkit = SearchToolkit()
tools = [FunctionTool(search_toolkit.search_google)]

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

agent = ChatAgent(
    system_message="You are a helpful research assistant",
    model=model,
    tools=tools,
)
