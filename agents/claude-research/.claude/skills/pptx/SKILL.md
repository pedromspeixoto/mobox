---
name: pptx
description: Create professional PowerPoint presentations using python-pptx. Use when you need to generate slides with bullet points, charts, and professional formatting. Ideal for research summaries, executive briefings, and presentations.
---

# PowerPoint Presentation Generation

## Overview

This skill enables creation of professional PowerPoint presentations using Python's python-pptx library. Presentations include clean, text-focused slides with bullet points, embedded charts, and professional styling.

## Quick Start

```python
from pptx import Presentation
from pptx.util import Inches, Pt
import os

# Ensure output directory exists
os.makedirs('files/reports', exist_ok=True)

# Create presentation
prs = Presentation()
prs.slide_width = Inches(13.333)  # Widescreen 16:9
prs.slide_height = Inches(7.5)

# Add title slide
slide_layout = prs.slide_layouts[0]  # Title slide layout
slide = prs.slides.add_slide(slide_layout)
title = slide.shapes.title
subtitle = slide.placeholders[1]

title.text = "Research Report"
subtitle.text = "Generated Analysis"

# Save
prs.save('files/reports/presentation.pptx')
print("PPTX saved to: files/reports/presentation.pptx")
```

## Complete Presentation Template

Use this template for comprehensive research presentations:

```python
import os
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RgbColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_research_presentation(
    title: str,
    sections: list,
    charts: list,
    sources: list,
    output_path: str
):
    """Create a professional research presentation.

    Args:
        title: Presentation title
        sections: List of dicts with 'title' and 'bullets' keys
        charts: List of chart file paths
        sources: List of source strings
        output_path: Where to save the PPTX
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Colors
    PRIMARY = RgbColor(0x1A, 0x1A, 0x2E)  # Dark blue
    ACCENT = RgbColor(0x0F, 0x4C, 0x75)   # Medium blue
    TEXT_LIGHT = RgbColor(0xFF, 0xFF, 0xFF)
    TEXT_DARK = RgbColor(0x2D, 0x34, 0x36)

    # Create widescreen presentation
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # === TITLE SLIDE ===
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Background
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0,
        prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = PRIMARY
    bg.line.fill.background()

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5)
    )
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = TEXT_LIGHT
    p.alignment = PP_ALIGN.CENTER

    # Date
    date_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(6), Inches(12.333), Inches(0.5)
    )
    tf = date_box.text_frame
    p = tf.paragraphs[0]
    p.text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
    p.font.size = Pt(14)
    p.font.color.rgb = TEXT_LIGHT
    p.alignment = PP_ALIGN.CENTER

    # === CONTENT SLIDES ===
    for section in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        # Header bar
        header = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
        )
        header.fill.solid()
        header.fill.fore_color.rgb = PRIMARY
        header.line.fill.background()

        # Section title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.7)
        )
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = section['title']
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = TEXT_LIGHT

        # Bullets
        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5.5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True

        bullets = section.get('bullets', [])
        for i, bullet in enumerate(bullets[:6]):  # Max 6 bullets
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = f"• {bullet}"
            p.font.size = Pt(20)
            p.font.color.rgb = TEXT_DARK
            p.space_after = Pt(12)

    # === CHART SLIDES ===
    for chart_path in charts:
        if os.path.exists(chart_path):
            slide = prs.slides.add_slide(prs.slide_layouts[6])

            # Header
            header = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
            )
            header.fill.solid()
            header.fill.fore_color.rgb = ACCENT
            header.line.fill.background()

            # Chart title
            chart_name = os.path.basename(chart_path).replace('_', ' ').replace('.png', '').title()
            title_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.7)
            )
            tf = title_box.text_frame
            p = tf.paragraphs[0]
            p.text = chart_name
            p.font.size = Pt(28)
            p.font.bold = True
            p.font.color.rgb = TEXT_LIGHT

            # Chart image
            img = slide.shapes.add_picture(
                chart_path, Inches(1.667), Inches(1.5), width=Inches(10)
            )
            # Center horizontally
            img.left = int((prs.slide_width - img.width) / 2)

    # === SOURCES SLIDE ===
    if sources:
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        header = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
        )
        header.fill.solid()
        header.fill.fore_color.rgb = PRIMARY
        header.line.fill.background()

        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.7)
        )
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = "Sources"
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = TEXT_LIGHT

        sources_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5.5)
        )
        tf = sources_box.text_frame
        tf.word_wrap = True

        for i, source in enumerate(sources[:10], 1):
            if i == 1:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = f"{i}. {source}"
            p.font.size = Pt(14)
            p.font.color.rgb = TEXT_DARK
            p.space_after = Pt(8)

    # === THANK YOU SLIDE ===
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = PRIMARY
    bg.line.fill.background()

    thanks_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(2.8), Inches(12.333), Inches(1)
    )
    tf = thanks_box.text_frame
    p = tf.paragraphs[0]
    p.text = "Thank You"
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = TEXT_LIGHT
    p.alignment = PP_ALIGN.CENTER

    prs.save(output_path)
    return output_path

# Example usage:
# create_research_presentation(
#     title="Electric Vehicle Market Analysis",
#     sections=[
#         {
#             "title": "Executive Summary",
#             "bullets": [
#                 "Global EV market reached $384B in 2024",
#                 "25.3% year-over-year growth",
#                 "Tesla leads with 19.5% market share"
#             ]
#         },
#         {
#             "title": "Key Trends",
#             "bullets": [
#                 "Battery costs down 40% since 2020",
#                 "Charging infrastructure growing 42% YoY",
#                 "Consumer adoption accelerating"
#             ]
#         }
#     ],
#     charts=["files/charts/market_share.png"],
#     sources=["IEA Global EV Outlook 2025", "BloombergNEF"],
#     output_path="files/reports/ev_analysis.pptx"
# )
```

## Design Principles

1. **Maximum 5-6 bullets per slide** - Keep content scannable
2. **One idea per bullet** - Be concise
3. **Include statistics** - Numbers make points memorable
4. **Clean backgrounds** - Dark header, white content area
5. **Consistent fonts** - Use system fonts for compatibility

## Embedding Charts

```python
from pptx.util import Inches
import os

chart_path = "files/charts/trend.png"
if os.path.exists(chart_path):
    # Add picture with width constraint
    img = slide.shapes.add_picture(
        chart_path,
        Inches(1.667),  # Left position
        Inches(1.5),    # Top position
        width=Inches(10)
    )
    # Center horizontally
    img.left = int((prs.slide_width - img.width) / 2)
```

## Best Practices

1. **Always check paths exist** before adding images
2. **Use 16:9 widescreen** format for modern displays
3. **Limit text per slide** - Use appendix for details
4. **Include source citations** on dedicated slide
5. **End with Thank You** slide for closure

## File Locations

- Output: `files/reports/*.pptx`
- Charts: `files/charts/*.png`
- Research notes: `files/research_notes/*.md`
