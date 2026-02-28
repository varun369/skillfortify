"""Haystack pipeline with OpenAPI connector -- test fixture."""

from haystack import Pipeline
from haystack.components.connectors import OpenAPIServiceConnector
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.converters import OpenAPIServiceToFunctions
from haystack.utils import Secret

connector = OpenAPIServiceConnector()
converter = OpenAPIServiceToFunctions()
llm = OpenAIChatGenerator(
    api_key=Secret.from_env_var("OPENAI_API_KEY"),
    model="gpt-4o",
)

pipe = Pipeline()
pipe.add_component("converter", converter)
pipe.add_component("llm", llm)
pipe.add_component("connector", connector)
pipe.connect("converter", "llm")
pipe.connect("llm", "connector")
