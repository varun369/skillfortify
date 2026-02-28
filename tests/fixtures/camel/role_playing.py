"""CAMEL-AI RolePlaying society with assistant and user roles."""
from camel.societies import RolePlaying
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

role_play = RolePlaying(
    assistant_role_name="Researcher",
    user_role_name="Student",
    model=model,
)
