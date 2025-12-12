"""Google Gemini P&ID extraction agent using the generalized pnid_agent module."""

from pnid_agent import Provider, extract_pnid

if __name__ == "__main__":
    result = extract_pnid(
        image_path="data/input/brewery.jpg",
        provider=Provider.GOOGLE_GEMINI,
        output_path="data/output/pnid.json",
    )

    print(f"\n✅ Extraction complete!")
    print(f"Provider: {result['provider']}")
    print(f"Model: {result['model']}")
    print(f"Components: {len(result['output']['components'])}")
    print(f"Pipes: {len(result['output']['pipes'])}")
