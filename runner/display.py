"""
Visualization engine — generates a results card image using Pillow.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from runner.scorer import PAIRED_AXES
from runner import badges

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Data Loading
# ---------------------------------------------------------------------------

_ASSETS_DIR = Path(__file__).parent.parent / "politiscales" / "public" / "images"
_META_PATH = Path(__file__).parent / "data" / "axes_meta.json"

BG_COLOR = "#eeeeee"
HEADER_BG = "#5b2c6f"  # PolitiScales purple
TEXT_COLOR = "#333333"
WHITE = "#ffffff"
GREY = "#cccccc"

# Card dimensions
WIDTH = 800
HEIGHT = 1450 # Increased height

# Font paths (macOS defaults)
FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Verdana.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _load_meta() -> dict:
    with _META_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a system font, otherwise fallback to default."""
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing Helpers
# ---------------------------------------------------------------------------

def generate_results_card(result_data: dict, output_path: Path) -> None:
    """Generate the full results card image."""
    meta_json = _load_meta()
    
    # Extract metadata and scores
    run_meta = result_data.get("meta", {})
    model_id = run_meta.get("model", "Unknown Model")
    
    if "runs" in result_data and result_data["runs"]:
        # Use first run for individual card
        run_record = result_data["runs"][0]
        scores = run_record["scores"]
        duration = run_record.get("duration_seconds", 0)
        tokens = run_record.get("total_tokens", 0)
    else:
        scores = result_data.get("scores", result_data.get("aggregate", {}))
        duration = 0
        tokens = 0

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.rectangle([0, 0, WIDTH, 65], fill=HEADER_BG)
    font_header_title = _get_font(30, bold=True)
    draw.text((20, 15), "PolitiScales", font=font_header_title, fill=WHITE)
    
    # NEW: Model Branding in Header (Right-aligned or beside title)
    font_model = _get_font(20)
    badges.draw_model_branding(img, model_id, 220, 15, font_model, font_color=WHITE)
    
    font_url = _get_font(18)
    draw.text((WIDTH - 150, 20), "politiscales.party", font=font_url, fill=WHITE)

    # 2. Simplified Flag
    # Sort axes by score to find dominant ones for flag colors
    axis_scores = []
    for pair_name, axes_data in scores["paired"].items():
        for axis_name, val in axes_data.items():
            if val is not None:
                axis_scores.append((axis_name, val))
    axis_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Flag Background (3 horizontal strips)
    flag_w, flag_h = 400, 240
    flag_x = (WIDTH - flag_w) // 2
    flag_y = 120
    
    # Pick top 3 colors
    top_colors = [meta_json["paired"].get(a[0], {}).get("color", GREY) for a in axis_scores[:3]]
    while len(top_colors) < 3:
        top_colors.append(GREY)
        
    for i, color in enumerate(top_colors):
        draw.rectangle(
            [flag_x, flag_y + i*(flag_h//3), flag_x + flag_w, flag_y + (i+1)*(flag_h//3)],
            fill=color
        )
        
    # Flag Symbol (Centered)
    top_axis = axis_scores[0][0]
    symbol_path = _ASSETS_DIR / f"{top_axis}.png"
    if symbol_path.exists():
        symbol_img = Image.open(symbol_path).convert("RGBA")
        symbol_img.thumbnail((120, 120), Image.Resampling.LANCZOS)
        img.paste(symbol_img, (flag_x + (flag_w - symbol_img.width)//2, flag_y + (flag_h - symbol_img.height)//2), symbol_img)

    # 3. Slogans
    slogans = []
    for axis_name, _ in axis_scores:
        s = meta_json["paired"].get(axis_name, {}).get("slogan")
        if s and s not in slogans:
            slogans.append(s.capitalize())
        if len(slogans) >= 3:
            break
            
    font_slogan = _get_font(28, bold=True)
    slogan_text = " · ".join(slogans) if slogans else "Neutral"
    w = draw.textlength(slogan_text, font=font_slogan)
    draw.text(((WIDTH - w) // 2, flag_y + flag_h + 20), slogan_text, font=font_slogan, fill=TEXT_COLOR)

    # 4. Paired Axis Bars
    bar_y = flag_y + flag_h + 100
    bar_h = 35
    bar_w = 400
    bar_x = (WIDTH - bar_w) // 2
    
    font_label = _get_font(18)
    font_pct = _get_font(16, bold=True)

    for pair_name, (left, right) in PAIRED_AXES.items():
        pair_data = scores["paired"].get(pair_name)
        if not pair_data or pair_data.get(left) is None:
            continue
            
        lp = pair_data[left]
        rp = pair_data[right]
        np = pair_data.get("neutral", 0.0)

        # Draw Labels
        left_label = meta_json["labels"].get(left, left)
        right_label = meta_json["labels"].get(right, right)
        draw.text((bar_x, bar_y - 25), left_label, font=font_label, fill=TEXT_COLOR)
        w_right = draw.textlength(right_label, font=font_label)
        draw.text((bar_x + bar_w - w_right, bar_y - 25), right_label, font=font_label, fill=TEXT_COLOR)

        # Draw Icons
        for icon_name, x_pos in [(left, bar_x - 85), (right, bar_x + bar_w + 10)]:
            icon_path = _ASSETS_DIR / f"{icon_name}_small.png"
            if not icon_path.exists():
                icon_path = _ASSETS_DIR / f"{icon_name}.png"
            if icon_path.exists():
                icon_img = Image.open(icon_path).convert("RGBA")
                icon_img.thumbnail((75, 75), Image.Resampling.LANCZOS)
                img.paste(icon_img, (int(x_pos), int(bar_y - 20)), icon_img)

        # Draw Three-Segment Bar
        l_w = int(bar_w * lp)
        draw.rectangle([bar_x, bar_y, bar_x + l_w, bar_y + bar_h], fill=meta_json["paired"][left]["color"])
        if lp > 0.05:
            draw.text((bar_x + 5, bar_y + 8), f"{int(lp*100)}%", font=font_pct, fill=WHITE)
            
        n_w = int(bar_w * np)
        draw.rectangle([bar_x + l_w, bar_y, bar_x + l_w + n_w, bar_y + bar_h], fill=GREY)
        if np > 0.15:
            nw_full = draw.textlength(f"{int(np*100)}%", font=font_pct)
            draw.text((bar_x + l_w + (n_w - nw_full)//2, bar_y + 8), f"{int(np*100)}%", font=font_pct, fill=WHITE)

        r_w = bar_w - l_w - n_w
        draw.rectangle([bar_x + l_w + n_w, bar_y, bar_x + bar_w, bar_y + bar_h], fill=meta_json["paired"][right]["color"])
        if rp > 0.05:
            rw_full = draw.textlength(f"{int(rp*100)}%", font=font_pct)
            draw.text((bar_x + bar_w - rw_full - 5, bar_y + 8), f"{int(rp*100)}%", font=font_pct, fill=WHITE)

        bar_y += 90 

    # 5. NEW: Axis Badges (unpaired) at the bottom
    badges.draw_axis_badges(img, scores, bar_x, bar_y + 20)

    # 6. NEW: Footer with metadata
    footer_y = HEIGHT - 80
    draw.line([50, footer_y - 10, WIDTH - 50, footer_y - 10], fill=GREY, width=1)
    
    font_footer = _get_font(14)
    font_footer_bold = _get_font(14, bold=True)
    
    # Model info
    meta_line1 = f"Model: {model_id}"
    meta_line2 = (
        f"Mode: {run_meta.get('mode')} | "
        f"Temp: {run_meta.get('temperature')} | "
        f"Top_P: {run_meta.get('top_p')}"
    )
    meta_line3 = (
        f"Duration: {duration:.1f}s | "
        f"Tokens: {tokens}"
    )
    
    draw.text((50, footer_y), meta_line1, font=font_footer_bold, fill=TEXT_COLOR)
    draw.text((50, footer_y + 20), meta_line2, font=font_footer, fill=TEXT_COLOR)
    draw.text((50, footer_y + 40), meta_line3, font=font_footer, fill=TEXT_COLOR)
    
    timestamp = run_meta.get("timestamp", "")
    draw.text((WIDTH - 250, footer_y), f"Generated on: {timestamp[:19]}", font=font_footer, fill=TEXT_COLOR)
    draw.text((WIDTH - 250, footer_y + 20), f"Runner Version: {run_meta.get('version')}", font=font_footer, fill=TEXT_COLOR)

    # Save
    img.save(output_path)
