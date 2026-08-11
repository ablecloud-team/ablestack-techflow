#!/usr/bin/env python3
"""Assemble visually verified Issue #46 slide renders into a PDF."""

from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[3]
SLIDES = ROOT / "tmp/issue46-presentation/renders"
OUTPUT = ROOT / "output/pdf/techflow-golden-set-quality-security-e2e-presentation.pdf"
images = sorted(SLIDES.glob("slide-*.png"))
if len(images) != 10:
    raise RuntimeError(f"expected 10 rendered slides, found {len(images)}")
with Image.open(images[0]) as first:
    width, height = first.size
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
pdf = canvas.Canvas(str(OUTPUT), pagesize=(width, height))
pdf.setTitle("TechFlow Issue #46 Golden Set·품질·보안·E2E 발표자료")
pdf.setAuthor("ABLESTACK TechFlow")
for image in images:
    with Image.open(image) as current:
        if current.size != (width, height):
            raise ValueError(f"inconsistent slide size: {image}")
    pdf.drawImage(ImageReader(str(image)), 0, 0, width=width, height=height)
    pdf.showPage()
pdf.save()
print(OUTPUT)
