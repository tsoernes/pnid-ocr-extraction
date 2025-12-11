from anthropic import AsyncAnthropicFoundry
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from dotenv import load_dotenv
import os
load_dotenv()



# Create client with API key authentication
client = AsyncAnthropicFoundry(
    base_url="https://aif-minside.services.ai.azure.com/anthropic/",
    api_key=os.getenv("AZURE_ANTROPIC_API_KEY"),
)

model = AnthropicModel(
    "claude-opus-4-5", provider=AnthropicProvider(anthropic_client=client)
)
agent = Agent(model)
response = agent.run_sync("good morning")
print(response.output)