from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import io
from datetime import datetime
from django.db import models

def generate_student_pdf(student, health_record, history, performances):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title and Generation Info
    elements.append(Paragraph(f"Student Progress Report: {student.name}", styles['Title']))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Basic Info
    if health_record:
        bmi_str = f"{health_record.bmi:.1f}" if health_record.bmi is not None else "N/A"
        info_data = [
            ["Roll Number:", student.roll_number or "N/A"],
            ["Section:", student.section or "N/A"],
            ["Current BMI:", f"{bmi_str} ({health_record.fitness_status or 'N/A'})"],
            ["Height:", f"{health_record.height} cm"],
            ["Weight:", f"{health_record.weight} kg"],
        ]
    else:
        info_data = [
            ["Roll Number:", student.roll_number or "N/A"],
            ["Section:", student.section or "N/A"],
            ["Health Status:", "No current health record available."],
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
    recommendations = health_record.ai_recommendations if health_record else "No recommendations available."
    elements.append(Paragraph(recommendations or "No recommendations available.", styles['Normal']))
    elements.append(Spacer(1, 24))

    # BMI History with Trend Analysis
    elements.append(Paragraph("BMI History and Trend Analysis", styles['Heading2']))
    
    # Calculate BMI trend
    bmi_trend = "No trend data available"
    bmi_change = 0
    if len(history) > 1:
        first_bmi = history.last().bmi
        last_bmi = history.first().bmi
        bmi_change = last_bmi - first_bmi
        
        if bmi_change > 0.5:
            bmi_trend = "Increasing (Weight Gain)"
        elif bmi_change < -0.5:
            bmi_trend = "Decreasing (Weight Loss)"
        else:
            bmi_trend = "Stable"
    
    # Add trend information
    elements.append(Paragraph(f"Overall BMI Trend: {bmi_trend}", styles['Normal']))
    if bmi_change != 0:
        elements.append(Paragraph(f"Total BMI Change: {bmi_change:+.2f}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    history_data = [["Date", "Height (cm)", "Weight (kg)", "BMI", "Status"]]
    for h in history[:10]: # Last 10 records
        status = h.fitness_status or "Unknown"
        date_str = h.date.strftime('%Y-%m-%d') if hasattr(h.date, 'strftime') else str(h.date)
        bmi_str = f"{h.bmi:.1f}" if h.bmi is not None else "N/A"
        history_data.append([date_str, h.height, h.weight, bmi_str, status])
    
    if len(history_data) > 1:
        history_table = Table(history_data, colWidths=[90, 80, 80, 60, 90])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(history_table)
    else:
        elements.append(Paragraph("No historical data available.", styles['Normal']))
    
    elements.append(Spacer(1, 24))

    # Enhanced Fitness Performance Analysis
    elements.append(Paragraph("Fitness Performance Results", styles['Heading2']))
    
    # Handle performances as QuerySet or list
    performances_list = performances if hasattr(performances, '__iter__') else []
    
    # Group performances by metric
    metrics_data = {}
    for p in performances_list:
        metric_name = getattr(p, 'metric_name', "Unknown") or "Unknown"
        if metric_name not in metrics_data:
            metrics_data[metric_name] = []
        metrics_data[metric_name].append(p)
    
    # Analyze each metric
    for metric_name, metric_performances in metrics_data.items():
        elements.append(Paragraph(f"{metric_name} Analysis", styles['Heading3']))
        
        # Calculate progress
        if len(metric_performances) > 1:
            first_score = metric_performances[-1].score
            last_score = metric_performances[0].score
            score_change = last_score - first_score
            score_change_pct = (score_change / first_score * 100) if first_score != 0 else 0
            
            if score_change > 0:
                progress_trend = f"Improving (+{score_change:.1f} points, {score_change_pct:+.1f}%)"
            elif score_change < 0:
                progress_trend = f"Declining ({score_change:.1f} points, {score_change_pct:+.1f}%)"
            else:
                progress_trend = "Stable"
                
            elements.append(Paragraph(f"Progress: {progress_trend}", styles['Normal']))
            elements.append(Paragraph(f"Latest Score: {last_score} | First Score: {first_score}", styles['Normal']))
        else:
            latest_score = getattr(metric_performances[0], 'score', 'N/A') if metric_performances else 'N/A'
            elements.append(Paragraph(f"Latest Score: {latest_score}", styles['Normal']))
        
        # Add table for this metric
        metric_data = [["Date", "Score", "Notes"]]
        for p in metric_performances[:5]:  # Last 5 performances for this metric
            date_str = getattr(p, 'date', 'Unknown')
            if hasattr(date_str, 'strftime'):
                date_str = date_str.strftime('%Y-%m-%d')
            else:
                date_str = str(date_str)
            score = getattr(p, 'score', 'N/A')
            metric_data.append([date_str, f"{score}", ""])
        
        metric_table = Table(metric_data, colWidths=[120, 80, 120])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(metric_table)
        elements.append(Spacer(1, 12))
    
    if not metrics_data:
        elements.append(Paragraph("No fitness test scores recorded.", styles['Normal']))
    
    elements.append(Spacer(1, 24))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", styles['Heading2']))
    
    summary_points = []
    
    # Health summary
    if health_record:
        bmi_str = f"{health_record.bmi:.1f}" if health_record.bmi is not None else "N/A"
        summary_points.append(f"Current BMI: {bmi_str} ({health_record.fitness_status or 'Unknown status'})")
    
    # BMI trend summary
    if len(history) > 1:
        first_bmi = history.last().bmi
        last_bmi = history.first().bmi
        bmi_change = last_bmi - first_bmi
        if bmi_change > 0.5:
            summary_points.append(f"BMI trend: Increasing by {bmi_change:+.2f} points")
        elif bmi_change < -0.5:
            summary_points.append(f"BMI trend: Decreasing by {bmi_change:+.2f} points")
        else:
            summary_points.append("BMI trend: Stable")
    
    # Fitness summary
    if len(performances_list) > 0:
        total_tests = len(performances_list)
        summary_points.append(f"Total fitness tests: {total_tests}")
        
        # Calculate average score
        scores = [getattr(p, 'score', 0) for p in performances_list if hasattr(p, 'score')]
        if scores:
            avg_score = sum(scores) / len(scores)
            summary_points.append(f"Average fitness score: {avg_score:.1f}")
    else:
        summary_points.append("No fitness tests recorded")
    
    # Data completeness
    summary_points.append(f"Health records: {len(history) + (1 if health_record else 0)}")
    summary_points.append(f"Fitness records: {len(performances_list)}")
    
    for point in summary_points:
        elements.append(Paragraph(f"• {point}", styles['Normal']))
    
    elements.append(Spacer(1, 24))

    # Safety Disclaimer
    elements.append(Spacer(1, 48))
    disclaimer = "<i>This is an informational tool and does not provide medical diagnosis</i>"
    elements.append(Paragraph(disclaimer, styles['Normal']))


    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
