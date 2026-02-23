import io
import os
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, 
    Image, PageBreak, KeepTogether, NextPageTemplate
)
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import calculations
import database

# Set plotting style for cleaner, flatter look
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("deep")

# --- BRAND COLORS ---
PRIMARY_HEX = '#2c5aa0'
SECONDARY_HEX = '#5fa2e8'
ACCENT_HEX = '#ffc107'
SUCCESS_HEX = '#4caf50'
DANGER_HEX = '#f44336'
TEXT_HEX = '#333333'
LIGHT_BG_HEX = '#f8f9fa'
GRAY_LINE_HEX = '#e0e0e0'

PRIMARY_COLOR = colors.HexColor(PRIMARY_HEX)
SECONDARY_COLOR = colors.HexColor(SECONDARY_HEX)
ACCENT_COLOR = colors.HexColor(ACCENT_HEX)
SUCCESS_COLOR = colors.HexColor(SUCCESS_HEX)
DANGER_COLOR = colors.HexColor(DANGER_HEX)
TEXT_COLOR = colors.HexColor(TEXT_HEX)
LIGHT_BG = colors.HexColor(LIGHT_BG_HEX)
GRAY_LINE = colors.HexColor(GRAY_LINE_HEX)

class PDFReportGenerator:
    def __init__(self, project_id):
        self.project_id = project_id
        self.metrics = calculations.get_project_metrics(project_id)
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        
    def _create_custom_styles(self):
        """Create custom paragraph styles for the report"""
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=self.styles['Title'],
            fontSize=36,
            leading=42,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=50,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            leading=20,
            textColor=PRIMARY_COLOR,
            spaceBefore=20,
            spaceAfter=15,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalJustified',
            parent=self.styles['Normal'],
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor('#444444')
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['BodyText'],
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=PRIMARY_COLOR,
            alignment=TA_CENTER
        ))

    def _draw_logo(self, canvas, x, y, size=30):
        """Draws a simple geometric logo"""
        canvas.saveState()
        canvas.translate(x, y)
        # Main square
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, size, size, fill=1, stroke=0)
        # Inner accent
        canvas.setFillColor(ACCENT_COLOR)
        canvas.circle(size*0.7, size*0.7, size*0.2, fill=1, stroke=0)
        # Text "PM"
        canvas.setFillColor(PRIMARY_COLOR)
        canvas.setFont("Helvetica-Bold", size*0.6)
        canvas.drawCentredString(size*0.4, size*0.3, "PM")
        canvas.restoreState()

    def _header_footer(self, canvas, doc):
        """Draw Header and Footer on every page"""
        canvas.saveState()
        
        width, height = A4
        
        # --- HEADER ---
        # Minimalist white header with colored bar at very top
        canvas.setFillColor(PRIMARY_COLOR)
        canvas.rect(0, height - 15, width, 15, fill=1, stroke=0)
        
        # Project Name Left
        canvas.setFillColor(PRIMARY_COLOR)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawString(40, height - 50, f"{self.metrics['project_name']}")
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.gray)
        canvas.drawString(40, height - 62, f"Project Ref: {self.metrics['project_number']}")

        # Date Right
        canvas.drawRightString(width - 40, height - 50, f"{datetime.now().strftime('%B %d, %Y')}")
        
        # Divider Line
        canvas.setStrokeColor(GRAY_LINE)
        canvas.setLineWidth(1)
        canvas.line(40, height - 70, width - 40, height - 70)
        
        # --- FOOTER ---
        canvas.setStrokeColor(GRAY_LINE)
        canvas.line(40, 50, width - 40, 50)
        
        canvas.setFillColor(colors.gray)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(40, 35, "Generated by PM Tool | Confidential - Internal Use Only")
        canvas.drawRightString(width - 40, 35, f"Page {doc.page}")
        
        canvas.restoreState()

    def _cover_page_bg(self, canvas, doc):
        """Draw background for the cover page"""
        canvas.saveState()
        width, height = A4
        
        # 1. Left Sidebar (Dark Blue)
        canvas.setFillColor(PRIMARY_COLOR)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        
        # 2. Right Content Area (White) - Curved edge design
        canvas.setFillColor(colors.white)
        # Draw a white rectangle covering the right side
        path = canvas.beginPath()
        path.moveTo(width * 0.35, 0)
        path.lineTo(width, 0)
        path.lineTo(width, height)
        path.lineTo(width * 0.35, height)
        path.close()
        canvas.drawPath(path, fill=1, stroke=0)
        
        # 3. Logo on Sidebar
        self._draw_logo(canvas, 40, height - 80, size=50)
        
        # 4. Sidebar Text
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(40, 50, "CONFIDENTIAL REPORT")
        
        canvas.restoreState()

    def _create_financial_chart(self):
        """Create a Bar chart for Financial Overview (High Res)"""
        plt.figure(figsize=(6, 3))
        
        categories = ['Budget', 'Forecast', 'Actual']
        values = [
            self.metrics['total_budget'], 
            self.metrics['forecast'], 
            self.metrics['total_spent']
        ]
        
        # Clean minimalist bars
        bars = plt.bar(categories, values, color=[PRIMARY_HEX, '#7c3aed', '#0891b2'], 
                      width=0.5, edgecolor='none')
        
        # Remove frames
        ax = plt.gca()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#dddddd')
        
        # Grid lines
        ax.yaxis.grid(True, linestyle='--', color='#eeeeee')
        ax.xaxis.grid(False)
        
        # Add values on top
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + (max(values)*0.02),
                    f'R {height/1000:.0f}k',
                    ha='center', va='bottom', fontsize=10, fontweight='bold', color='#444')
            
        plt.title('Financial Performance', loc='left', fontsize=12, pad=20, color='#444')
        plt.tick_params(left=False, bottom=False, labelleft=False, labelcolor='#666')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
        plt.close()
        return buf

    def _create_cost_breakdown_chart(self):
        """Create a Donut chart for Cost Breakdown (High Res)"""
        exp_df = calculations.get_category_spending(self.project_id)
        
        plt.figure(figsize=(5, 3))
        
        if not exp_df.empty:
            colors_palette = sns.color_palette("mako", n_colors=len(exp_df))
            wedges, texts, autotexts = plt.pie(exp_df['total'], labels=exp_df['category'], autopct='%1.0f%%', 
                   startangle=90, pctdistance=0.85, colors=colors_palette,
                   wedgeprops=dict(width=0.4, edgecolor='white'))
            
            plt.setp(autotexts, size=9, weight="bold", color="white")
            plt.setp(texts, size=9, color="#444")
            
            plt.title('Cost Distribution', loc='center', fontsize=12, pad=10, color='#444')
        else:
            plt.text(0.5, 0.5, 'No Data', ha='center', va='center')
            plt.axis('off')
            
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
        plt.close()
        return buf

    def _create_progress_chart(self):
        """Create a Sleek Progress Bar"""
        plt.figure(figsize=(7, 1))
        
        progress = self.metrics['pct_complete']
        
        # Background
        plt.barh([0], [100], color='#f1f3f5', height=0.6, edgecolor='none', align='center')
        # Progress
        plt.barh([0], [progress], color=SUCCESS_HEX, height=0.6, edgecolor='none', align='center')
        
        plt.xlim(0, 100)
        plt.axis('off')
        
        # Add text inside
        plt.text(1, 0, f"{progress:.1f}% Complete", va='center', ha='left', fontsize=11, fontweight='bold', color='white' if progress > 15 else '#444')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', transparent=True)
        plt.close()
        return buf

    def generate(self):
        buffer = io.BytesIO()
        
        # Layout Setup
        doc = BaseDocTemplate(buffer, pagesize=A4, 
                              topMargin=0.7*inch, bottomMargin=0.7*inch, 
                              leftMargin=0.7*inch, rightMargin=0.7*inch)
        
        # 1. Cover Page Frame (Full Page)
        cover_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='cover')
        
        # 2. Normal Page Frame (With Header/Footer spacing)
        normal_frame = Frame(doc.leftMargin, doc.bottomMargin + 30, doc.width, doc.height - 80, id='normal')
        
        # Templates
        cover_template = PageTemplate(id='cover_page', frames=cover_frame, onPage=self._cover_page_bg)
        normal_template = PageTemplate(id='report_page', frames=normal_frame, onPage=self._header_footer)
        
        doc.addPageTemplates([cover_template, normal_template])
        
        story = []
        
        if not self.metrics:
            return buffer # Handle error gracefully

        # === COVER PAGE ===
        story.append(Spacer(1, 2*inch))
        
        # Left sidebar style (using white text on blue bg)
        # Note: Since we draw bg on canvas, we just need to align text.
        # But reportlab flowables flow relative to frame. 
        # For the cover layout, we need to push text to the blue area or white area.
        
        # We will put the Title on the BLUE side (Left)
        # But the frame covers the whole page. We need to indent specifically or use a table.
        
        cover_table_data = [[
            Paragraph(f"PROJECT<br/>STATUS<br/>REPORT", self.styles['CoverTitle']),
            Paragraph(f"<br/><br/><br/><b>{self.metrics['project_name']}</b><br/>{datetime.now().strftime('%B %Y')}", 
                      ParagraphStyle('CoverRight', parent=self.styles['Normal'], fontSize=20, leading=26, textColor=PRIMARY_COLOR))
        ]]
        
        t_cover = Table(cover_table_data, colWidths=[3.5*inch, 4*inch])
        t_cover.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (0,0), (0,0), 20),
        ]))
        story.append(t_cover)
        
        story.append(Spacer(1, 4*inch))
        
        # Key Stats on Cover (Bottom Right)
        stats_data = [
            ['BUDGET USED', 'SCHEDULE HEALTH', 'OPEN RISKS'],
            [f"{self.metrics['budget_used_pct']:.0f}%", self.metrics['schedule_health'], "Checking..."]
        ]
        
        risks_df = database.get_project_risks(self.project_id)
        open_risks = len(risks_df[risks_df['status'] == 'Open']) if not risks_df.empty else 0
        stats_data[1][2] = str(open_risks)
        
        t_stats = Table(stats_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch])
        t_stats.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('TEXTCOLOR', (0,0), (-1,0), colors.gray),
            ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,1), (-1,1), 24),
            ('TEXTCOLOR', (0,1), (-1,1), PRIMARY_COLOR),
            ('TOPPADDING', (0,1), (-1,1), 5),
        ]))
        
        # Push stats to right
        t_stats_container = Table([[None, t_stats]], colWidths=[3.5*inch, 5.5*inch])
        story.append(t_stats_container)
        
        story.append(NextPageTemplate('report_page'))
        story.append(PageBreak())
        
        # === CONTENT PAGES ===
        
        # 1. EXECUTIVE SUMMARY SECTION
        elements_exec = []
        elements_exec.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        status_color = "#4caf50" if self.metrics['budget_health'] == 'Green' else "#f44336"
        status_text = "exceeding budget" if self.metrics['forecast'] > self.metrics['total_budget'] else "well within budget"
        
        summary_html = f"""
        The project <b>{self.metrics['project_name']}</b> is currently in <b>{self.metrics['actual_status']}</b> status. 
        Physical completion is estimated at <b>{self.metrics['pct_complete']:.1f}%</b>. 
        Financial performance shows we are <font color="{status_color}"><b>{status_text}</b></font> 
        with a forecasted completion cost of <b>R {self.metrics['forecast']:,.2f}</b> against a budget of <b>R {self.metrics['total_budget']:,.2f}</b>.
        """
        elements_exec.append(Paragraph(summary_html, self.styles['NormalJustified']))
        elements_exec.append(Spacer(1, 15))
        
        # Progress Bar
        elements_exec.append(Paragraph("Overall Progress", ParagraphStyle('SubHeader', parent=self.styles['Heading3'], fontSize=11, textColor=colors.gray)))
        elements_exec.append(Image(self._create_progress_chart(), width=7*inch, height=0.5*inch))
        elements_exec.append(Spacer(1, 25))
        
        story.append(KeepTogether(elements_exec))
        
        # 2. FINANCIAL OVERVIEW SECTION
        elements_fin = []
        elements_fin.append(Paragraph("Financial Performance", self.styles['SectionHeader']))
        
        # Charts Side-by-Side
        fin_chart = Image(self._create_financial_chart(), width=3.4*inch, height=2.2*inch)
        cost_chart = Image(self._create_cost_breakdown_chart(), width=3.4*inch, height=2.2*inch)
        
        charts_table = Table([[fin_chart, cost_chart]], colWidths=[3.5*inch, 3.5*inch])
        charts_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
        elements_fin.append(charts_table)
        elements_fin.append(Spacer(1, 10))
        
        # Financial Data Table (Minimalist)
        fin_data = [['CATEGORY', 'BUDGET', 'ACTUAL', 'FORECAST', 'VARIANCE']]
        fin_data.append([
            'Project Total',
            f"{self.metrics['total_budget']:,.0f}",
            f"{self.metrics['total_spent']:,.0f}",
            f"{self.metrics['forecast']:,.0f}",
            f"{self.metrics['variance_at_completion']:,.0f}"
        ])
        
        t_fin = Table(fin_data, colWidths=[2*inch, 1.25*inch, 1.25*inch, 1.25*inch, 1.25*inch])
        t_fin.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('TEXTCOLOR', (0,0), (-1,0), colors.gray),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('LINEBELOW', (0,0), (-1,0), 1, PRIMARY_COLOR),
            
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
            ('LINEBELOW', (0,1), (-1,-1), 0.5, GRAY_LINE),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        elements_fin.append(t_fin)
        elements_fin.append(Spacer(1, 20))
        story.append(KeepTogether(elements_fin))
        
        # 3. RISKS SECTION
        elements_risk = []
        elements_risk.append(Paragraph("Risk Register (High Priority)", self.styles['SectionHeader']))
        
        if not risks_df.empty:
            risk_data = [['ID', 'DESCRIPTION', 'IMPACT', 'STATUS', 'MITIGATION']]
            for idx, row in risks_df.head(5).iterrows():
                risk_data.append([
                    str(row['risk_id']),
                    Paragraph(row['description'], self.styles['Normal']),
                    row['impact'],
                    row['status'],
                    Paragraph(row['mitigation_action'] or '-', self.styles['Normal'])
                ])
            
            t_risks = Table(risk_data, colWidths=[0.5*inch, 2.2*inch, 0.8*inch, 1*inch, 2.5*inch])
            t_risks.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 8),
                ('TEXTCOLOR', (0,0), (-1,0), colors.gray),
                ('LINEBELOW', (0,0), (-1,0), 1, PRIMARY_COLOR),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTSIZE', (0,1), (-1,-1), 9),
                ('LINEBELOW', (0,1), (-1,-1), 0.5, GRAY_LINE),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            elements_risk.append(t_risks)
        else:
            elements_risk.append(Paragraph("No active risks identified.", self.styles['Normal']))
            
        elements_risk.append(Spacer(1, 20))
        story.append(KeepTogether(elements_risk))
        
        # 4. MILESTONES (If space allows, else break)
        # We assume it fits, if not reportlab handles break.
        # But we want header + table to stick together.
        
        elements_ms = []
        elements_ms.append(Paragraph("Key Milestones", self.styles['SectionHeader']))
        
        baseline = database.get_baseline_schedule(self.project_id)
        if not baseline.empty:
            ms_data = [['ACTIVITY', 'START DATE', 'END DATE', 'STATUS']]
            for idx, row in baseline.head(8).iterrows():
                status = row['status']
                status_color = colors.black
                if status == 'Complete': status_color = SUCCESS_COLOR
                elif status == 'Active': status_color = PRIMARY_COLOR
                
                ms_data.append([
                    Paragraph(row['activity_name'], self.styles['Normal']),
                    row['planned_start'],
                    row['planned_finish'],
                    Paragraph(f"<font color='{status_color.hexval()}'>{status}</font>", self.styles['Normal'])
                ])
                
            t_ms = Table(ms_data, colWidths=[3*inch, 1.2*inch, 1.2*inch, 1.5*inch])
            t_ms.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 8),
                ('TEXTCOLOR', (0,0), (-1,0), colors.gray),
                ('LINEBELOW', (0,0), (-1,0), 1, PRIMARY_COLOR),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('FONTSIZE', (0,1), (-1,-1), 9),
                ('LINEBELOW', (0,1), (-1,-1), 0.5, GRAY_LINE),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            elements_ms.append(t_ms)
        
        story.append(KeepTogether(elements_ms))

        doc.build(story)
        buffer.seek(0)
        return buffer
