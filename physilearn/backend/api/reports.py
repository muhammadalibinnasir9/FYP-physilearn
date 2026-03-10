from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import io

def generate_student_pdf(student, health_record, history, performances):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"Student Progress Report: {student.name}", styles['Title']))
    elements.append(Spacer(1, 12))

    # Basic Info
    info_data = [
        ["Roll Number:", student.roll_number or "N/A"],
        ["Section:", student.section or "N/A"],
        ["Current BMI:", f"{health_record.bmi} ({health_record.fitness_status})"],
        ["Height:", f"{health_record.height} cm"],
        ["Weight:", f"{health_record.weight} kg"],
    ]
    info_table = Table(info_data, colWidths=[100, 300])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 24))

    # AI Recommendations
    elements.append(Paragraph("AI Health Recommendations", styles['Heading2']))
    elements.append(Paragraph(health_record.ai_recommendations or "No recommendations available.", styles['Normal']))
    elements.append(Spacer(1, 24))

    # BMI History
    elements.append(Paragraph("BMI History (Trends)", styles['Heading2']))
    history_data = [["Date", "Height (cm)", "Weight (kg)", "BMI"]]
    for h in history[:10]: # Last 10 records
        history_data.append([str(h.date), h.height, h.weight, h.bmi])
    
    if len(history_data) > 1:
        history_table = Table(history_data, colWidths=[100, 100, 100, 100])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(history_table)
    else:
        elements.append(Paragraph("No historical data available.", styles['Normal']))
    
    elements.append(Spacer(1, 24))

    # Fitness Performance
    elements.append(Paragraph("Fitness Test Scores", styles['Heading2']))
    perf_data = [["Date", "Metric", "Score"]]
    for p in performances:
        perf_data.append([str(p.date), p.metric_name, p.score])
    
    if len(perf_data) > 1:
        perf_table = Table(perf_data, colWidths=[150, 150, 100])
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(perf_table)
    else:
        elements.append(Paragraph("No fitness test scores recorded.", styles['Normal']))

    # Safety Disclaimer
    elements.append(Spacer(1, 48))
    disclaimer = "This is an informational tool and does not provide medical diagnosis"
    elements.append(Paragraph(disclaimer, styles['Italic']))


    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
