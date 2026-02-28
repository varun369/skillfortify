"""Multiple Semantic Kernel plugins in one file with kernel registration.

Fixture exercises multi-class extraction, kernel.add_plugin calls,
and prompt template detection.
"""

import os

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.prompt_template import PromptTemplateConfig


class MathPlugin:
    """Plugin for mathematical operations."""

    @kernel_function(description="Add two numbers together")
    def add(self, number_a: float, number_b: float) -> float:
        """Return the sum of two numbers."""
        return number_a + number_b

    @kernel_function(description="Multiply two numbers")
    def multiply(self, number_a: float, number_b: float) -> float:
        """Return the product of two numbers."""
        return number_a * number_b


class TextPlugin:
    """Plugin for text manipulation."""

    @kernel_function(description="Convert text to uppercase")
    def to_upper(self, text: str) -> str:
        """Return uppercase version of text."""
        return text.upper()


kernel = Kernel()
kernel.add_plugin(MathPlugin(), plugin_name="math")
kernel.add_plugin(TextPlugin(), plugin_name="text")

# Prompt function registration.
summary_config = PromptTemplateConfig(
    template="Summarize the following: {{$input}}"
)
