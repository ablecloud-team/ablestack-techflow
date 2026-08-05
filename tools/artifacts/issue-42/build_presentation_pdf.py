#!/usr/bin/env python3
"""Assemble rendered Issue #42 slides into a presentation PDF."""

import re
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[3]
SLIDES = ROOT / "tmp/issue-42-artifacts/rendered"
OUTPUT = ROOT / "output/pdf/techflow-source-registry-presentation.pdf"


def natural(path):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name)]


images = sorted(SLIDES.glob("*.png"), key=natural)
if len(images) != 10:
    raise RuntimeError(f"expected 10 rendered slides, found {len(images)}")
with Image.open(images[0]) as first:
    width, height = first.size
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
pdf = canvas.Canvas(str(OUTPUT), pagesize=(width, height))
pdf.setTitle("TechFlow Issue #42 Source Registry 구현 완료")
pdf.setAuthor("ABLESTACK TechFlow")
for image in images:
    with Image.open(image) as current:
        if current.size != (width, height):
            raise ValueError(f"inconsistent slide size: {image}")
    pdf.drawImage(ImageReader(str(image)), 0, 0, width=width, height=height)
    pdf.showPage()
pdf.save()
print(OUTPUT)
