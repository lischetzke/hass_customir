"""Generate the project's icon as an SVG (canonical) and PNG (for HACS / HA).

The icon depicts a stylised IR remote (rounded rectangle + three buttons)
with three IR-broadcast arcs emanating from the LED at the top. Two-colour
flat-design palette tuned to read at 96px and scale up to 512px.

Outputs:
  - icon.svg  (repo root) — vector source.
  - icon.png  (repo root, 512×512) — README / HACS preview.
  - custom_components/hass_customir/icon.png        (256×256)
  - custom_components/hass_customir/icon@2x.png     (512×512)
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent

PRIMARY = (255, 145, 38, 255)        # IR-LED orange-red
PRIMARY_DARK = (200, 95, 20, 255)    # button accents
DARK = (38, 38, 60, 255)             # remote body
BG = (255, 255, 255, 0)              # transparent
LIGHT = (245, 245, 250, 255)         # button face


# ---------------------------------------------------------------------------
# SVG (canonical source)
# ---------------------------------------------------------------------------

SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Custom IR">
  <title>Custom IR</title>
  <!-- broadcast arcs -->
  <g fill="none" stroke="#FF9126" stroke-linecap="round" stroke-width="22">
    <path d="M256 80 A 60 60 0 0 1 316 140" />
    <path d="M256 50 A 90 90 0 0 1 346 140" />
    <path d="M256 20 A 120 120 0 0 1 376 140" />
  </g>
  <g fill="none" stroke="#FF9126" stroke-linecap="round" stroke-width="22" transform="translate(512 0) scale(-1 1)">
    <path d="M256 80 A 60 60 0 0 1 316 140" />
    <path d="M256 50 A 90 90 0 0 1 346 140" />
    <path d="M256 20 A 120 120 0 0 1 376 140" />
  </g>
  <!-- IR LED dot -->
  <circle cx="256" cy="160" r="22" fill="#FF9126"/>
  <!-- remote body -->
  <rect x="160" y="180" width="192" height="312" rx="36" ry="36" fill="#26263C"/>
  <!-- screen / power region -->
  <rect x="186" y="206" width="140" height="44" rx="10" ry="10" fill="#F5F5FA" opacity="0.92"/>
  <circle cx="316" cy="228" r="10" fill="#FF9126"/>
  <!-- D-pad ring -->
  <circle cx="256" cy="312" r="50" fill="#0F0F1A" stroke="#F5F5FA" stroke-width="4"/>
  <circle cx="256" cy="312" r="20" fill="#FF9126"/>
  <!-- bottom button grid -->
  <g fill="#F5F5FA">
    <rect x="190" y="394" width="48" height="32" rx="8"/>
    <rect x="274" y="394" width="48" height="32" rx="8"/>
    <rect x="190" y="438" width="48" height="32" rx="8"/>
    <rect x="274" y="438" width="48" height="32" rx="8"/>
  </g>
  <!-- accent dots on D-pad arms -->
  <g fill="#F5F5FA">
    <circle cx="256" cy="276" r="4"/>
    <circle cx="256" cy="348" r="4"/>
    <circle cx="220" cy="312" r="4"/>
    <circle cx="292" cy="312" r="4"/>
  </g>
</svg>
"""


def write_svg(path: Path) -> None:
    path.write_text(SVG.lstrip(), encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO)}")


# ---------------------------------------------------------------------------
# PNG (rasterised twin of the SVG, drawn directly with Pillow)
# ---------------------------------------------------------------------------


def render_png(size: int) -> Image.Image:
    """Render the icon at *size*×*size* using Pillow primitives."""
    scale = size / 512  # design coordinates are in a 512x512 viewBox
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    def s(*coords: float) -> tuple[float, ...]:
        return tuple(c * scale for c in coords)

    def round_rect(box: tuple[float, float, float, float], radius: float, fill, outline=None, width=0):
        # Pillow's rounded_rectangle requires integer coords and full pixel alignment.
        draw.rounded_rectangle(s(*box), radius=radius * scale, fill=fill, outline=outline, width=int(width * scale))

    # Broadcast arcs — three on each side
    arc_width = max(1, int(22 * scale))
    for cx, cy, r in ((256, 140, 60), (256, 140, 90), (256, 140, 120)):
        # Left half of arc (from top-left to top-right at angle covering 240..300)
        bbox = (cx - r, cy - r, cx + r, cy + r)
        draw.arc(s(*bbox), start=240, end=300, fill=PRIMARY, width=arc_width)

    # IR LED dot
    draw.ellipse(s(256 - 22, 160 - 22, 256 + 22, 160 + 22), fill=PRIMARY)

    # Remote body
    round_rect((160, 180, 352, 492), 36, fill=DARK)

    # Screen / power strip
    round_rect((186, 206, 326, 250), 10, fill=LIGHT)
    draw.ellipse(s(316 - 10, 228 - 10, 316 + 10, 228 + 10), fill=PRIMARY)

    # D-pad ring
    ring_w = max(1, int(4 * scale))
    draw.ellipse(s(256 - 50, 312 - 50, 256 + 50, 312 + 50),
                 fill=(15, 15, 26, 255), outline=LIGHT, width=ring_w)
    draw.ellipse(s(256 - 20, 312 - 20, 256 + 20, 312 + 20), fill=PRIMARY)

    # Bottom buttons
    for x in (190, 274):
        for y in (394, 438):
            round_rect((x, y, x + 48, y + 32), 8, fill=LIGHT)

    # D-pad accent dots
    for cx, cy in ((256, 276), (256, 348), (220, 312), (292, 312)):
        draw.ellipse(s(cx - 4, cy - 4, cx + 4, cy + 4), fill=LIGHT)

    return img


def main() -> None:
    write_svg(REPO / "icon.svg")
    for path, size in (
        (REPO / "icon.png", 512),
        (REPO / "custom_components/hass_customir/icon.png", 256),
        (REPO / "custom_components/hass_customir/icon@2x.png", 512),
    ):
        img = render_png(size)
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, format="PNG", optimize=True)
        print(f"  wrote {path.relative_to(REPO)}  ({size}x{size})")


if __name__ == "__main__":
    main()
