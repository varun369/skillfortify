"""Basic Haystack pipeline with generator component -- test fixture."""

from haystack import Pipeline
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder

template = """Answer the question: {{ question }}"""

pipe = Pipeline()
pipe.add_component("prompt_builder", PromptBuilder(template=template))
pipe.add_component("llm", OpenAIGenerator(model="gpt-4o"))
pipe.connect("prompt_builder", "llm")
