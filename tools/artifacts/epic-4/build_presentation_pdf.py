#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[3]
SLIDES = ROOT / "tmp/epic4-presentation/renders"
OUTPUT = ROOT / "output/pdf/techflow-epic4-assist-validation-presentation.pdf"
images = sorted(SLIDES.glob("slide-*.png"))
if len(images) != 6:
    raise RuntimeError(f"expected 6 slides, found {len(images)}")
with Image.open(images[0]) as first:
    width, height = first.size
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
pdf = canvas.Canvas(str(OUTPUT), pagesize=(width, height))
pdf.setTitle("TechFlow Epic #4 Assist 운영 실증 발표자료")
pdf.setAuthor("ABLESTACK TechFlow")
for image in images:
    with Image.open(image) as current:
        if current.size != (width, height):
            raise ValueError(f"inconsistent slide size: {image}")
    pdf.drawImage(ImageReader(str(image)), 0, 0, width=width, height=height)
    pdf.showPage()
pdf.save()
print(OUTPUT)
