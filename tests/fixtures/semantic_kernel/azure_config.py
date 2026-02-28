"""Semantic Kernel plugin with Azure AI service configuration.

Fixture exercises env-var extraction for Azure OpenAI endpoints,
Kernel() instantiation detection, and add_service calls.
"""

import os

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion


kernel = Kernel()

kernel.add_service(
    AzureChatCompletion(
        deployment_name="gpt-4",
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )
)

BACKUP_KEY = os.getenv("AZURE_BACKUP_KEY")
