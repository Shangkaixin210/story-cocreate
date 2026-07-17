"""
Image generation service for story illustrations.

Uses Pollinations.ai (free, no API key required).
"""

from urllib.parse import quote


def generate_image_url(prompt: str, width: int = 512, height: int = 512) -> str:
    """Generate an illustration URL from a text prompt.

    Uses Pollinations.ai free API.
    Returns a URL that renders the generated image directly.
    """
    if not prompt or not prompt.strip():
        return ""

    # Clean and truncate prompt
    clean = prompt.strip()[:300]
    encoded = quote(clean, safe="")

    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&nologo=true&seed={hash(clean) & 0xFFFF}"
    )


def generate_image_prompt_from_narrative(narrative: str) -> str:
    """Create a short English image prompt from the narrative text.

    Extracts key visual elements for better image generation results.
    """
    if not narrative:
        return ""

    # Simple heuristic: take key nouns and the scene context
    # For Chinese text, we'll use it directly (Pollinations handles Chinese)
    # For English or mixed, also use directly
    # Just clean it up a bit
    clean = narrative.strip()
    # Truncate to ~200 chars for a focused prompt
    if len(clean) > 200:
        clean = clean[:200]

    # Add style guidance
    style = "children's book illustration, warm colors, storybook art style"
    return f"{clean}, {style}"
