import argparse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

def md_to_text(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="docs/methodology_template.md")
    ap.add_argument("--out_pdf", default="M6_METHODLOGY.pdf")
    args = ap.parse_args()

    text = md_to_text(args.md)
    c = canvas.Canvas(args.out_pdf, pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica", 11)

    # Very basic MD -> text: just wrap
    lines = []
    for para in text.split("\n\n"):
        wrapped = simpleSplit(para, "Helvetica", 11, width-80)
        lines.extend(wrapped + [""])

    for line in lines:
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 40
        c.drawString(40, y, line)
        y -= 14

    c.save()

if __name__ == "__main__":
    main()
