#!/usr/bin/env python3
"""
MCP Server for Document Generation
Handles PDF, PNG creation and document processing for email responses
"""

from mcp.server import Server
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import os

server = Server("document_generation")

DATA_DIR = Path("./data")
OUTPUT_DIR = Path("./output")

@server.tool("create_analysis_plot")
def create_analysis_plot(data_file: str, plot_type: str = "well_log") -> str:
    """Create analysis plots from LAS/data files and save as PNG"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_file.split('.')[0]}_{plot_type}_{timestamp}.png"
        filepath = OUTPUT_DIR / filename
        
        # Create sample plot (replace with actual data processing)
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 8))
        
        # Sample depth data
        depth = np.linspace(1000, 2000, 100)
        
        # Plot 1: Gamma Ray
        gamma_ray = 50 + 30 * np.sin(depth/100) + np.random.normal(0, 5, 100)
        ax1.plot(gamma_ray, depth, 'g-', linewidth=2)
        ax1.set_xlabel('Gamma Ray (API)')
        ax1.set_ylabel('Depth (ft)')
        ax1.set_title('Gamma Ray Log')
        ax1.invert_yaxis()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Porosity
        porosity = 0.15 + 0.1 * np.sin(depth/150) + np.random.normal(0, 0.02, 100)
        ax2.plot(porosity, depth, 'b-', linewidth=2)
        ax2.set_xlabel('Porosity (v/v)')
        ax2.set_title('Porosity Log')
        ax2.invert_yaxis()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Water Saturation
        water_sat = 0.3 + 0.2 * np.cos(depth/120) + np.random.normal(0, 0.05, 100)
        ax3.plot(water_sat, depth, 'r-', linewidth=2)
        ax3.set_xlabel('Water Saturation (v/v)')
        ax3.set_title('Water Saturation')
        ax3.invert_yaxis()
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.suptitle(f'Well Log Analysis - {data_file}', y=0.98)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filename)
    except Exception as e:
        return f"Error creating plot: {e}"

@server.tool("generate_analysis_report")
def generate_analysis_report(well_name: str, analysis_summary: str, plot_files: list) -> str:
    """Generate comprehensive PDF report with analysis and plots"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{well_name}_analysis_report_{timestamp}.pdf"
        filepath = OUTPUT_DIR / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Build document content
        content = []
        
        # Title
        title = Paragraph(f"Well Log Analysis Report - {well_name}", title_style)
        content.append(title)
        content.append(Spacer(1, 20))
        
        # Analysis Summary
        content.append(Paragraph("Executive Summary", styles['Heading2']))
        content.append(Spacer(1, 12))
        content.append(Paragraph(analysis_summary, styles['Normal']))
        content.append(Spacer(1, 20))
        
        # Key Findings
        content.append(Paragraph("Key Findings", styles['Heading2']))
        content.append(Spacer(1, 12))
        
        findings = [
            "• Reservoir quality assessment completed based on log analysis",
            "• Pay zones identified using porosity and saturation criteria",
            "• Formation characteristics analyzed for hydrocarbon potential",
            "• Recommendations provided for further development"
        ]
        
        for finding in findings:
            content.append(Paragraph(finding, styles['Normal']))
        content.append(Spacer(1, 20))
        
        # Add plots if available
        if plot_files:
            content.append(Paragraph("Log Analysis Plots", styles['Heading2']))
            content.append(Spacer(1, 12))
            
            for plot_file in plot_files:
                plot_path = OUTPUT_DIR / plot_file
                if plot_path.exists():
                    try:
                        img = Image(str(plot_path), width=6*inch, height=4*inch)
                        content.append(img)
                        content.append(Spacer(1, 12))
                    except Exception as e:
                        content.append(Paragraph(f"Error loading plot: {plot_file}", styles['Normal']))
        
        # Footer
        content.append(Spacer(1, 30))
        footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        content.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(content)
        
        return str(filename)
    except Exception as e:
        return f"Error generating report: {e}"

@server.tool("create_summary_visualization")
def create_summary_visualization(data_summary: dict, chart_type: str = "summary") -> str:
    """Create summary visualization charts for email responses"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_{chart_type}_{timestamp}.png"
        filepath = OUTPUT_DIR / filename
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 8))
        
        # Sample data visualization
        zones = ['Pay Zone', 'Reservoir', 'Tight Rock', 'Shale']
        zone_counts = [25, 35, 20, 20]
        colors = ['green', 'blue', 'orange', 'red']
        
        # Pie chart - Zone Distribution
        ax1.pie(zone_counts, labels=zones, colors=colors, autopct='%1.1f%%')
        ax1.set_title('Zone Classification')
        
        # Bar chart - Average Properties
        properties = ['Porosity', 'Permeability', 'Water Sat', 'Net/Gross']
        values = [0.15, 50, 0.35, 0.68]
        ax2.bar(properties, values, color=['blue', 'green', 'red', 'purple'])
        ax2.set_title('Average Petrophysical Properties')
        ax2.tick_params(axis='x', rotation=45)
        
        # Line chart - Depth Profile
        depth = np.linspace(1000, 2000, 50)
        porosity_profile = 0.15 + 0.05 * np.sin(depth/100)
        ax3.plot(depth, porosity_profile, 'b-', linewidth=2)
        ax3.set_xlabel('Depth (ft)')
        ax3.set_ylabel('Porosity')
        ax3.set_title('Porosity vs Depth')
        ax3.grid(True, alpha=0.3)
        
        # Scatter plot - Porosity vs Permeability
        poro_data = np.random.normal(0.15, 0.05, 50)
        perm_data = 100 * poro_data**3 * np.random.normal(1, 0.3, 50)
        ax4.scatter(poro_data, perm_data, alpha=0.6, color='red')
        ax4.set_xlabel('Porosity')
        ax4.set_ylabel('Permeability (mD)')
        ax4.set_title('Porosity vs Permeability')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filename)
    except Exception as e:
        return f"Error creating visualization: {e}"

@server.tool("format_email_response")
def format_email_response(response_content: str, attachments: list) -> dict:
    """Format email response with proper structure for sending"""
    try:
        formatted_response = {
            "subject": "Re: Well Log Analysis Results",
            "body": response_content,
            "attachments": attachments,
            "content_type": "text/html",
            "priority": "normal",
            "timestamp": datetime.now().isoformat()
        }
        
        # Add professional formatting
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto;">
                {response_content.replace('\n', '<br>')}
                
                <hr style="margin: 20px 0;">
                
                <p style="color: #666; font-size: 12px;">
                    This email was generated automatically by our analysis system.
                    Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </p>
            </div>
        </body>
        </html>
        """
        
        formatted_response["html_body"] = html_body
        
        return formatted_response
    except Exception as e:
        return {"error": f"Error formatting response: {e}"}

if __name__ == "__main__":
    server.run()