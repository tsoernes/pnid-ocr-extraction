import os

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()


# Create client with API key authentication
client = AsyncAzureOpenAI(
    azure_endpoint="https://aif-minside.cognitiveservices.azure.com/",
    api_version="2024-07-01-preview",
    api_key=os.getenv("AZURE_ANTROPIC_API_KEY"),
)

model = OpenAIChatModel("DeepSeek-V3.1", provider=OpenAIProvider(openai_client=client))
agent = Agent(model)
response = agent.run_sync("good morning")
print(response.output)
