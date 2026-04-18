"""
Badges module — handles rendering of model branding and PolitiScales axis badges.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from runner.scorer import UNPAIRED_AXES

logger = logging.getLogger(__name__)

# Directory paths
_LOGOS_DIR = Path(__file__).parent / "data" / "assets" / "logos"
_SUBMODULE_IMAGES = Path(__file__).parent.parent / "politiscales" / "public" / "images"



def get_provider_logo(model_id: str) -> Image.Image | None:
    """Load the logo for the given model's provider dynamically."""
    # Handle cases like "google/gemini-pro" -> "google"
    # or "anthropic/claude-3" -> "anthropic"
    provider = model_id.split("/")[0].lower()
    
    # Common mappings for providers that might have different names in logos
    mappings = {
        "google": ["google", "gemini"],
        "anthropic": ["anthropic", "claude"],
        "meta": ["meta", "llama"],
    }
    
    search_names = mappings.get(provider, [provider])
    
    for name in search_names:
        logo_path = _LOGOS_DIR / f"{name}.png"
        if logo_path.exists():
            return Image.open(logo_path).convert("RGBA")
    
    return None


def draw_model_branding(
    img: Image.Image,
    model_name: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    font_color: str = "#ffffff"
) -> None:
    """Draw the model provider logo and model name in the header."""
    logo = get_provider_logo(model_name)
    draw = ImageDraw.Draw(img)
    
    current_x = x
    if logo:
        # Resize logo to fit header height nicely (around 40px)
        logo.thumbnail((40, 40), Image.Resampling.LANCZOS)
        img.paste(logo, (current_x, y), logo)
        current_x += logo.width + 12
    
    # Draw model name
    draw.text((current_x, y + 5), model_name, font=font, fill=font_color)


def draw_axis_badges(
    img: Image.Image,
    scores: dict,
    start_x: int,
    y: int,
    spacing: int = 120
) -> int:
    """Draw large PolitiScales icons for any unpaired axis that exceeds its threshold.
    
    Returns the total width used.
    """
    unpaired_scores = scores.get("unpaired", {})
    current_x = start_x
    
    for axis, threshold in UNPAIRED_AXES.items():
        score = unpaired_scores.get(axis)
        if score is not None and score >= threshold:
            icon_path = _SUBMODULE_IMAGES / f"{axis}.png"
            if icon_path.exists():
                icon_img = Image.open(icon_path).convert("RGBA")
                # Large badge size
                icon_img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                img.paste(icon_img, (current_x, y), icon_img)
                current_x += spacing
                
    return current_x - start_x
