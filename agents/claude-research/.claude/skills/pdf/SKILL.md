---
name: pdf
description: Create professional PDF reports using reportlab. Use when you need to generate formatted PDF documents with text, tables, charts, and images. Ideal for research reports, data summaries, and professional documents.
---

# PDF Report Generation

## Overview

This skill enables creation of professional PDF reports using Python's reportlab library. Reports include proper formatting, embedded charts, tables, and sources sections.

## Quick Start

```python
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.units import inch
import os

# Ensure output directory exists
os.makedirs('files/reports', exist_ok=True)

# Create document
doc = SimpleDocTemplate(
    "files/reports/report.pdf",
    pagesize=letter,
    rightMargin=72, leftMargin=72,
    topMargin=72, bottomMargin=72
)

styles = getSampleStyleSheet()
story = []

# Add title
story.append(Paragraph("Report Title", styles['Title']))
story.append(Spacer(1, 0.25*inch))

# Add content
story.append(Paragraph("Executive Summary", styles['Heading1']))
story.append(Paragraph("Summary content here...", styles['Normal']))

# Build PDF
doc.build(story)
print("PDF saved to: files/reports/report.pdf")
```

## Complete Report Template

Use this template for comprehensive research reports:

```python
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    PageBreak, Table, TableStyle
)
from reportlab.lib import colors

def create_research_report(
    title: str,
    sections: list,
    charts: list,
    sources: list,
    output_path: str
):
    """Create a professional research report PDF.

    Args:
        title: Report title
        sections: List of dicts with 'heading' and 'content' keys
        charts: List of chart file paths
        sources: List of source strings
        output_path: Where to save the PDF
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name='CenteredTitle',
        parent=styles['Title'],
        alignment=TA_CENTER,
        fontSize=24,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='Justify',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=11,
        leading=14
    ))

    story = []

    # Title page
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph(title, styles['CenteredTitle']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y')}",
        styles['Normal']
    ))
    story.append(PageBreak())

    # Content sections
    for section in sections:
        story.append(Paragraph(section['heading'], styles['Heading1']))
        story.append(Spacer(1, 0.1*inch))

        # Handle bullet points
        if isinstance(section['content'], list):
            for bullet in section['content']:
                story.append(Paragraph(f"• {bullet}", styles['Justify']))
                story.append(Spacer(1, 0.05*inch))
        else:
            story.append(Paragraph(section['content'], styles['Justify']))

        story.append(Spacer(1, 0.2*inch))

    # Charts section
    if charts:
        story.append(PageBreak())
        story.append(Paragraph("Data Visualizations", styles['Heading1']))
        story.append(Spacer(1, 0.2*inch))

        for chart_path in charts:
            if os.path.exists(chart_path):
                img = Image(chart_path, width=5*inch, height=3*inch)
                story.append(img)
                story.append(Spacer(1, 0.3*inch))

    # Sources section
    if sources:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Sources", styles['Heading2']))
        for i, source in enumerate(sources, 1):
            story.append(Paragraph(f"{i}. {source}", styles['Normal']))

    doc.build(story)
    return output_path

# Example usage:
# create_research_report(
#     title="Electric Vehicle Market Analysis",
#     sections=[
#         {"heading": "Executive Summary", "content": "Key findings..."},
#         {"heading": "Market Overview", "content": ["Point 1", "Point 2"]},
#     ],
#     charts=["files/charts/market_share.png"],
#     sources=["Source 1 - URL", "Source 2 - URL"],
#     output_path="files/reports/ev_analysis.pdf"
# )
```

## Adding Tables

```python
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

# Create table data
data = [
    ['Company', 'Market Share', 'Growth'],
    ['Tesla', '19.5%', '+2.1%'],
    ['BYD', '16.2%', '+4.3%'],
    ['VW', '8.3%', '+0.8%'],
]

table = Table(data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 12),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
]))

story.append(table)
```

## Embedding Charts

```python
from reportlab.platypus import Image
from reportlab.lib.units import inch
import os

# Check if chart exists before adding
chart_path = "files/charts/market_trends.png"
if os.path.exists(chart_path):
    img = Image(chart_path, width=5*inch, height=3*inch)
    story.append(img)
    story.append(Spacer(1, 0.2*inch))
```

## Best Practices

1. **Always check paths exist** before adding images
2. **Use consistent styling** throughout the document
3. **Add page breaks** between major sections
4. **Include metadata** (date, author) on title page
5. **Use bullet points** for key statistics
6. **Add source citations** for all data

## File Locations

- Output: `files/reports/*.pdf`
- Charts: `files/charts/*.png`
- Research notes: `files/research_notes/*.md`
