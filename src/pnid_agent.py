"""Generalized P&ID extraction agent supporting multiple AI providers.

Supports:
- Google Gemini (via VertexAI or API key)
- Azure Anthropic Claude
- Azure DeepSeek
- Anthropic (direct)
- OpenAI

Usage:
    from pnid_agent import extract_pnid, Provider

    result = extract_pnid(
        image_path="data/input/brewery.png",
        provider=Provider.AZURE_ANTHROPIC,
        output_path="data/output/pnid.json"
    )
"""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryContent

load_dotenv()


class Component(BaseModel):
    """A component in a P&ID diagram."""

    label: str = Field(description="The label of the component")
    id: str = Field(description="The id of the component, label plus running number, if needed")
    category: str = Field(description="The category of the component")
    description: str = Field(description="The description of the component")
    x: float = Field(description="The x coordinate of the component center")
    y: float = Field(description="The y coordinate of the component center")


class Pipe(BaseModel):
    """A pipe/stream connecting components in a P&ID diagram."""

    label: str = Field(description="The label of the pipe")
    source: str = Field(description="The id of the source component")
    target: str = Field(description="The id of the target component")
    description: str = Field(description="The description of the pipe")
    x: float = Field(description="The x coordinate of the pipe label/midpoint")
    y: float = Field(description="The y coordinate of the pipe label/midpoint")


class PNID(BaseModel):
    """Complete P&ID diagram with components and pipes."""

    components: list[Component] = Field(description="The components of the PNID")
    pipes: list[Pipe] = Field(description="The pipes of the PNID")


class Provider(str, Enum):
    """Supported AI providers for P&ID extraction."""

    GOOGLE_GEMINI = "google"
    AZURE_ANTHROPIC = "azure-anthropic"
    AZURE_DEEPSEEK = "azure-deepseek"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


def create_agent(provider: Provider, model_name: str | None = None) -> Agent:
    """Create a P&ID extraction agent for the specified provider.

    Args:
        provider: The AI provider to use
        model_name: Optional model name override (uses defaults if not provided)

    Returns:
        Configured Agent instance

    Raises:
        ValueError: If required environment variables are missing
        ImportError: If required provider packages are not installed
    """
    system_prompt = (
        "You are an expert in process network identification. "
        "You are given an image of a process network and you have to identify the components and pipes. "
        "You have to identify the components and pipes based on the image. "
        "For each component and pipe, provide the x,y coordinates of its center or label position. "
        "Use pixel coordinates based on the image dimensions."
    )

    if provider == Provider.GOOGLE_GEMINI:
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required for Google Gemini")

        model_name = model_name or "gemini-3.0-pro-preview"
        google_provider = GoogleProvider(vertexai=False, api_key=api_key)
        model = GoogleModel(model_name, provider=google_provider)

    elif provider == Provider.AZURE_ANTHROPIC:
        from anthropic import AsyncAnthropicFoundry
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        api_key = os.getenv("AZURE_ANTROPIC_API_KEY") or os.getenv("ANTHROPIC_FOUNDRY_API_KEY")
        if not api_key:
            raise ValueError(
                "AZURE_ANTROPIC_API_KEY or ANTHROPIC_FOUNDRY_API_KEY environment variable is required"
            )

        client = AsyncAnthropicFoundry(
            base_url="https://aif-minside.services.ai.azure.com/anthropic/",
            api_key=api_key,
        )
        model_name = model_name or "claude-opus-4-5"
        model = AnthropicModel(model_name, provider=AnthropicProvider(anthropic_client=client))

    elif provider == Provider.AZURE_DEEPSEEK:
        from openai import AsyncAzureOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        # Use generalized Azure AI key for Azure OpenAI as well
        api_key = os.getenv("AZURE_AI_API_KEY")
        if not api_key:
            raise ValueError("AZURE_AI_API_KEY environment variable is required for Azure OpenAI")

        client = AsyncAzureOpenAI(
            azure_endpoint="https://aif-minside.cognitiveservices.azure.com/",
            api_version="2024-07-01-preview",
            api_key=api_key,
        )
        # Default to GPT-5.1 on Azure unless overridden
        model_name = model_name or "gpt-5.1"
        model = OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))

    elif provider == Provider.ANTHROPIC:
        from pydantic_ai.models.anthropic import AnthropicModel

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        model_name = model_name or "claude-sonnet-4-5"
        model = AnthropicModel(model_name, api_key=api_key)

    elif provider == Provider.OPENAI:
        from pydantic_ai.models.openai import OpenAIChatModel

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        model_name = model_name or "gpt-5"
        model = OpenAIChatModel(model_name, api_key=api_key)

    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return Agent(
        model,
        output_type=PNID,
        system_prompt=system_prompt,
    )


def extract_pnid(
    image_path: str | Path,
    provider: Provider = Provider.GOOGLE_GEMINI,
    model_name: str | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Extract P&ID components and pipes from an image.

    Args:
        image_path: Path to the P&ID diagram image
        provider: AI provider to use (default: Google Gemini)
        model_name: Optional model name override
        output_path: Optional path to save JSON output

    Returns:
        Dictionary with extraction results including:
        - output: Extracted PNID data (components and pipes)
        - provider: Provider used
        - model: Model name used
        - image_path: Input image path

    Raises:
        FileNotFoundError: If image_path does not exist
        ValueError: If provider configuration is invalid
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Read image
    with open(image_path, "rb") as f:
        image_content = f.read()

    # Determine media type from extension
    ext = image_path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/png")

    binary_content = BinaryContent(data=image_content, media_type=media_type)

    # Create agent and run extraction
    agent = create_agent(provider, model_name)
    result = agent.run_sync([binary_content])

    # Prepare output
    output_data = {
        "output": result.output.model_dump(),
        "provider": provider.value,
        "model": result.response.model_name or model_name or "unknown",
        "image_path": str(image_path),
    }

    # Save to file if requested
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_data, indent=4, ensure_ascii=False))
        print(f"✅ Saved output to: {output_path}")

    return output_data


def main():
    """CLI entry point for P&ID extraction."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract P&ID components and pipes from images")
    parser.add_argument("image_path", type=str, help="Path to P&ID diagram image")
    parser.add_argument(
        "-p",
        "--provider",
        type=str,
        choices=[p.value for p in Provider],
        default=Provider.GOOGLE_GEMINI.value,
        help="AI provider to use",
    )
    parser.add_argument("-m", "--model", type=str, help="Model name override")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="data/output/pnid.json",
        help="Output JSON file path",
    )

    args = parser.parse_args()

    try:
        result = extract_pnid(
            image_path=args.image_path,
            provider=Provider(args.provider),
            model_name=args.model,
            output_path=args.output,
        )

        print(f"\n✅ Extraction complete!")
        print(f"Provider: {result['provider']}")
        print(f"Model: {result['model']}")
        print(f"Components: {len(result['output']['components'])}")
        print(f"Pipes: {len(result['output']['pipes'])}")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
