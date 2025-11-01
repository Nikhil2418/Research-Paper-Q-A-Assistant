from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import os

def export_answer_to_pdf(question: str, answer: str, citations: list, filename="answer.pdf"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs("data", exist_ok=True)
    file_path = f"data/{timestamp}_{filename}"

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 60, "Research Paper Q&A Result")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 100, "Question:")
    c.setFont("Helvetica", 11)
    text_obj = c.beginText(40, height - 120)
    text_obj.textLines(question)
    c.drawText(text_obj)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 170, "Answer:")
    c.setFont("Helvetica", 11)
    text_obj = c.beginText(40, height - 190)
    text_obj.textLines(answer)
    c.drawText(text_obj)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, 150, "Sources:")
    c.setFont("Helvetica", 11)
    y = 130
    for cite in citations:
        c.drawString(60, y, f"• {cite}")
        y -= 15

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, 40, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.save()
    return file_path
