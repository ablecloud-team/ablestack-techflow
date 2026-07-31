#!/usr/bin/env python3
"""Assemble rendered Issue #18 slide PNGs into a presentation PDF."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[3]
SLIDES_DIR = ROOT / "tmp" / "artifacts" / "issue-18" / "rendered"
OUTPUT = ROOT / "output" / "pdf" / "techflow-image-version-lock-presentation.pdf"


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name)]


def build() -> None:
    images = sorted(SLIDES_DIR.glob("*.png"), key=natural_key)
    if not images:
        raise FileNotFoundError(f"No rendered slides found in {SLIDES_DIR}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(images[0]) as first:
        width, height = first.size
    pdf = canvas.Canvas(str(OUTPUT), pagesize=(width, height))
    pdf.setTitle("TechFlow 이미지 버전·Digest 고정")
    pdf.setAuthor("ABLESTACK TechFlow")
    for image_path in images:
        with Image.open(image_path) as image:
            if image.size != (width, height):
                raise ValueError(f"Inconsistent slide size: {image_path}")
        pdf.drawImage(ImageReader(str(image_path)), 0, 0, width=width, height=height)
        pdf.showPage()
    pdf.save()
    print(OUTPUT)


if __name__ == "__main__":
    build()
