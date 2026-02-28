"""Haystack pipeline demonstrating Secret usage patterns -- test fixture."""

import os

from haystack import Pipeline
from haystack.components.generators import OpenAIGenerator, HuggingFaceLocalGenerator
from haystack.utils import Secret

api_key = Secret.from_env_var("OPENAI_API_KEY")
hf_token = Secret.from_env_var("HF_TOKEN")
custom_key = Secret.from_env_var("CUSTOM_SERVICE_KEY")

llm = OpenAIGenerator(
    api_key=api_key,
    model="gpt-4o",
)

local_llm = HuggingFaceLocalGenerator(
    model="mistralai/Mistral-7B",
    token=hf_token,
)

db_password = os.environ["DATABASE_PASSWORD"]
analytics_endpoint = "https://analytics.internal.corp.com/v2/ingest"

pipe = Pipeline()
pipe.add_component("llm", llm)
