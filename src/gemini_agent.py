import json
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

load_dotenv()


class Component(BaseModel):
    label: str = Field(description="The label of the component")
    id: str = Field(description="The id of the component, label plus running number, if needed")
    category: str = Field(description="The category of the component")
    description: str = Field(description="The description of the component")
    x: float = Field(description="The x coordinate of the component center")
    y: float = Field(description="The y coordinate of the component center")


class Pipe(BaseModel):
    label: str = Field(description="The label of the pipe")
    source: str = Field(description="The id of the source component")
    target: str = Field(description="The id of the target component")
    description: str = Field(description="The description of the pipe")
    x: float = Field(description="The x coordinate of the pipe label/midpoint")
    y: float = Field(description="The y coordinate of the pipe label/midpoint")


class PNID(BaseModel):
    components: list[Component] = Field(description="The components of the PNID")
    pipes: list[Pipe] = Field(description="The pipes of the PNID")


INPUT_IMAGE = "data/input/brewary.jpg"


# Assuming you have an image file named 'my_image.jpg' in the same directory
image_file_path = Path(INPUT_IMAGE)

# Encode the image to Base64
with open(image_file_path, "rb") as image_file:
    image_content = image_file.read()

binary_content = BinaryContent(data=image_content, media_type="image/png")

import os

provider = GoogleProvider(vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"))
model = GoogleModel("gemini-3-pro-preview", provider=provider)
agent = Agent(
    model,
    output_type=PNID,
    system_prompt=(
        "You are an expert in process network identification."
        "You are given an image of a process network and you have to identify the components and pipes."
        "You have to identify the components and pipes based on the image."
    ),
)

result = agent.run_sync(
    [
        binary_content,
    ]
)

print(result)

output_path = Path("data/output/pnid.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(result.output.model_dump(), indent=4, ensure_ascii=False))
