#!/usr/bin/env python3
"""Assemble the visually reviewed Issue #44 slide renders into a PDF."""

from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[3]
SLIDES = ROOT / "tmp/issue-44-artifacts/rendered"
OUTPUT = ROOT / "output/pdf/techflow-grounded-responses-presentation.pdf"
images = sorted(SLIDES.glob("slide-*.png"))
if len(images) != 10:
    raise RuntimeError(f"expected 10 rendered slides, found {len(images)}")
with Image.open(images[0]) as first:
    width, height = first.size
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
pdf = canvas.Canvas(str(OUTPUT), pagesize=(width, height))
pdf.setTitle("TechFlow Issue #44 근거 기반 Responses 발표자료")
pdf.setAuthor("ABLESTACK TechFlow")
for image in images:
    with Image.open(image) as current:
        if current.size != (width, height):
            raise ValueError(f"inconsistent slide size: {image}")
    pdf.drawImage(ImageReader(str(image)), 0, 0, width=width, height=height)
    pdf.showPage()
pdf.save()
print(OUTPUT)
