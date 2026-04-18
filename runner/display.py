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

# Resolution Scaling
SCALE = 2

def res_scale(val: float) -> int:
    """Scale a coordinate or dimension."""
    return int(val * SCALE)

# Card dimensions (scaled)
WIDTH = res_scale(800)
HEIGHT = res_scale(1450)

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

def _draw_text_with_shadow(
    draw: ImageDraw.Draw,
    position: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str = WHITE,
    shadow_color: str = "black",
    shadow_offset: int = 1
) -> None:
    """Draw text with a subtle shadow for better contrast."""
    x, y = position
    off = res_scale(shadow_offset)
    # Draw shadow in 4 directions for better outline effect
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        draw.text((x + dx*off, y + dy*off), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill)


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
        # Aggregate logic: aggregate_scores returns a dict with mean for each axis
        # We need to flatten it back to just scores for the display engine
        raw_aggregate = result_data.get("aggregate", {})
        scores = {"paired": {}, "unpaired": {}}
        
        # Flatten paired axes
        for pair_name, axes_data in raw_aggregate.get("paired", {}).items():
            scores["paired"][pair_name] = {}
            for axis_name, stats in axes_data.items():
                scores["paired"][pair_name][axis_name] = stats.get("mean")
        
        # Flatten unpaired axes
        for axis_name, stats in raw_aggregate.get("unpaired", {}).items():
            scores["unpaired"][axis_name] = stats.get("mean")
            
        duration = 0
        tokens = 0

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 1. Header
    header_h = res_scale(65)
    draw.rectangle([0, 0, WIDTH, header_h], fill=HEADER_BG)
    font_header_title = _get_font(res_scale(30), bold=True)
    draw.text((res_scale(20), res_scale(15)), "PolitiScales", font=font_header_title, fill=WHITE)
    
    # NEW: Model Branding in Header
    font_model = _get_font(res_scale(20))
    badges.draw_model_branding(img, model_id, res_scale(220), res_scale(15), font_model, font_color=WHITE, scale=SCALE)
    
    font_url = _get_font(res_scale(18))
    draw.text((WIDTH - res_scale(150), res_scale(20)), "politiscales.party", font=font_url, fill=WHITE)

    # 2. Simplified Flag
    # Sort axes by score to find dominant ones for flag colors (exclude neutral)
    axis_scores = []
    for pair_name, axes_data in scores["paired"].items():
        for axis_name, val in axes_data.items():
            if val is not None and axis_name != "neutral":
                axis_scores.append((axis_name, val))
    axis_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Flag Background (3 horizontal strips)
    flag_w, flag_h = res_scale(400), res_scale(240)
    flag_x = (WIDTH - flag_w) // 2
    flag_y = res_scale(120)
    
    # Pick top 3 colors
    top_colors = [meta_json["paired"].get(a[0], {}).get("color", GREY) for a in axis_scores[:3]]
    while len(top_colors) < 3:
        top_colors.append(GREY)
        
    for i, color in enumerate(top_colors):
        segment_y_start = flag_y + i*(flag_h//3)
        segment_y_end = flag_y + (i+1)*(flag_h//3)
        draw.rectangle(
            [flag_x, segment_y_start, flag_x + flag_w, segment_y_end],
            fill=color
        )
        
    # Flag Symbol (Centered)
    top_axis = axis_scores[0][0]
    symbol_path = _ASSETS_DIR / f"{top_axis}.png"
    if symbol_path.exists():
        symbol_img = Image.open(symbol_path).convert("RGBA")
        symbol_size = res_scale(120)
        symbol_img.thumbnail((symbol_size, symbol_size), Image.Resampling.LANCZOS)
        img.paste(symbol_img, (flag_x + (flag_w - symbol_img.width)//2, flag_y + (flag_h - symbol_img.height)//2), symbol_img)

    # 3. Slogans
    slogans = []
    for axis_name, _ in axis_scores:
        slogan = meta_json["paired"].get(axis_name, {}).get("slogan")
        if slogan and slogan not in slogans:
            slogans.append(slogan.capitalize())
        if len(slogans) >= 3:
            break
            
    font_slogan = _get_font(res_scale(28), bold=True)
    slogan_text = " · ".join(slogans) if slogans else "Neutral"
    w = draw.textlength(slogan_text, font=font_slogan)
    draw.text(((WIDTH - w) // 2, flag_y + flag_h + res_scale(20)), slogan_text, font=font_slogan, fill=TEXT_COLOR)

    # 4. Paired Axis Bars
    bar_y = flag_y + flag_h + res_scale(100)
    bar_h = res_scale(35)
    bar_w = res_scale(400)
    bar_x = (WIDTH - bar_w) // 2
    
    font_label = _get_font(res_scale(18))
    font_pct = _get_font(res_scale(16), bold=True)

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
        draw.text((bar_x, bar_y - res_scale(25)), left_label, font=font_label, fill=TEXT_COLOR)
        w_right = draw.textlength(right_label, font=font_label)
        draw.text((bar_x + bar_w - w_right, bar_y - res_scale(25)), right_label, font=font_label, fill=TEXT_COLOR)

        # Draw Icons
        for icon_name, x_pos in [(left, bar_x - res_scale(85)), (right, bar_x + bar_w + res_scale(10))]:
            icon_path = _ASSETS_DIR / f"{icon_name}_small.png"
            if not icon_path.exists():
                icon_path = _ASSETS_DIR / f"{icon_name}.png"
            if icon_path.exists():
                icon_img = Image.open(icon_path).convert("RGBA")
                icon_dim = res_scale(75)
                icon_img.thumbnail((icon_dim, icon_dim), Image.Resampling.LANCZOS)
                img.paste(icon_img, (int(x_pos), int(bar_y - res_scale(20))), icon_img)

        # Draw Three-Segment Bar
        # 1. Left axis
        l_w = int(bar_w * lp)
        draw.rectangle([bar_x, bar_y, bar_x + l_w, bar_y + bar_h], fill=meta_json["paired"][left]["color"])
        if lp > 0.05:
            _draw_text_with_shadow(draw, (bar_x + res_scale(5), bar_y + res_scale(8)), f"{int(lp*100)}%", font=font_pct)
            
        # 2. Neutral axis
        n_w = int(bar_w * np)
        draw.rectangle([bar_x + l_w, bar_y, bar_x + l_w + n_w, bar_y + bar_h], fill=GREY)
        if np > 0.05:
            nw_full = draw.textlength(f"{int(np*100)}%", font=font_pct)
            _draw_text_with_shadow(draw, (bar_x + l_w + (n_w - nw_full)//2, bar_y + res_scale(8)), f"{int(np*100)}%", font=font_pct)

        # 3. Right axis
        r_w = bar_w - l_w - n_w
        draw.rectangle([bar_x + l_w + n_w, bar_y, bar_x + bar_w, bar_y + bar_h], fill=meta_json["paired"][right]["color"])
        if rp > 0.05:
            rw_full = draw.textlength(f"{int(rp*100)}%", font=font_pct)
            _draw_text_with_shadow(draw, (bar_x + bar_w - rw_full - res_scale(5), bar_y + res_scale(8)), f"{int(rp*100)}%", font=font_pct)

        bar_y += res_scale(90) 

    # 5. Axis Badges (unpaired) at the bottom
    badges.draw_axis_badges(img, scores, bar_x, bar_y + res_scale(20), scale=SCALE)

    # 6. Footer with metadata
    footer_y = HEIGHT - res_scale(80)
    draw.line([res_scale(50), footer_y - res_scale(10), WIDTH - res_scale(50), footer_y - res_scale(10)], fill=GREY, width=max(1, res_scale(1)))
    
    font_footer = _get_font(res_scale(14))
    font_footer_bold = _get_font(res_scale(14), bold=True)
    
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
    
    draw.text((res_scale(50), footer_y), meta_line1, font=font_footer_bold, fill=TEXT_COLOR)
    draw.text((res_scale(50), footer_y + res_scale(20)), meta_line2, font=font_footer, fill=TEXT_COLOR)
    draw.text((res_scale(50), footer_y + res_scale(40)), meta_line3, font=font_footer, fill=TEXT_COLOR)
    
    timestamp = run_meta.get("timestamp", "")
    draw.text((WIDTH - res_scale(250), footer_y), f"Generated on: {timestamp[:19]}", font=font_footer, fill=TEXT_COLOR)
    draw.text((WIDTH - res_scale(250), footer_y + res_scale(20)), f"Runner Version: {run_meta.get('version')}", font=font_footer, fill=TEXT_COLOR)

    # Save
    img.save(output_path)
