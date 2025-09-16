#!/usr/bin/env python3
"""
Unified MCP Server - Integration of all MCP tools
Real functionality without mock/demo code
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List

# Add MCP tools to path
sys.path.append(str(Path(__file__).parent / "mcp-tools"))

from fastmcp import FastMCP
from mcp.server.stdio import stdio_server

# Import all MCP tool functions
from las_analyzer import analyze_las_file, list_las_files, validate_las_file
from log_plotter import create_gamma_ray_plot, create_porosity_plot, create_resistivity_plot
from formation_analyzer import analyze_gamma_ray_lithology, analyze_porosity_quality, analyze_fluid_contacts
from email_processor import process_email_content, analyze_email_content, handle_email_attachments

# Create unified MCP server
mcp = FastMCP("Unified LAS Analysis and Email Processing Server")

# ===== LAS FILE ANALYSIS TOOLS =====

@mcp.tool()
def list_available_las_files() -> str:
    """List all available LAS files in the data directory."""
    result = list_las_files()
    if result.get('success'):
        return json.dumps(result, indent=2)
    else:
        return f"Error: {result.get('error', 'Failed to list LAS files')}"

@mcp.tool()
def analyze_las_file_data(filename: str) -> str:
    """Analyze a LAS file and extract comprehensive information."""
    result = analyze_las_file(filename)
    if result.get('success'):
        return json.dumps(result, indent=2)
    else:
        return f"Error: {result.get('error', 'Failed to analyze LAS file')}"

@mcp.tool()
def validate_las_file_structure(filename: str) -> str:
    """Validate LAS file structure and data quality."""
    result = validate_las_file(filename)
    if result.get('success'):
        return json.dumps(result, indent=2)
    else:
        return f"Error: {result.get('error', 'Failed to validate LAS file')}"

# ===== LOG PLOTTING TOOLS =====

@mcp.tool()
def plot_gamma_ray_log(filename: str) -> str:
    """Create a gamma ray log plot from LAS file data."""
    result = create_gamma_ray_plot(filename)
    if result.get('success'):
        return f"✅ Gamma ray plot created successfully: {result['output_file']}\n" + \
               f"📊 Data points: {result.get('data_points', 'N/A')}\n" + \
               f"📏 Depth range: {result.get('depth_range', 'N/A')}\n" + \
               f"⚡ Gamma range: {result.get('gamma_range', 'N/A')}"
    else:
        return f"❌ Error creating gamma ray plot: {result.get('error', 'Unknown error')}"

@mcp.tool()
def plot_porosity_log(filename: str) -> str:
    """Create a porosity log plot from LAS file data."""
    result = create_porosity_plot(filename)
    if result.get('success'):
        return f"✅ Porosity plot created successfully: {result['output_file']}\n" + \
               f"📊 Curves plotted: {', '.join(result.get('curves_plotted', []))}\n" + \
               f"🧪 Neutron column: {result.get('neutron_column', 'N/A')}\n" + \
               f"🏗️ Density column: {result.get('density_column', 'N/A')}"
    else:
        return f"❌ Error creating porosity plot: {result.get('error', 'Unknown error')}"

@mcp.tool()
def plot_resistivity_log(filename: str) -> str:
    """Create a resistivity log plot from LAS file data."""
    result = create_resistivity_plot(filename)
    if result.get('success'):
        return f"✅ Resistivity plot created successfully: {result['output_file']}\n" + \
               f"📊 Curves plotted: {', '.join(result.get('curves_plotted', []))}"
    else:
        return f"❌ Error creating resistivity plot: {result.get('error', 'Unknown error')}"

# ===== FORMATION ANALYSIS TOOLS =====

@mcp.tool()
def analyze_lithology_from_gamma_ray(filename: str) -> str:
    """Analyze gamma ray data to identify lithology and formation characteristics."""
    result = analyze_gamma_ray_lithology(filename)
    if result.get('success'):
        summary = f"🔬 Gamma Ray Lithology Analysis for {filename}\n\n"
        summary += f"📏 Total interval: {result.get('total_interval', 'N/A')} ft\n"
        
        lithology_summary = result.get('lithology_summary', {})
        summary += f"🏖️ Clean sand: {lithology_summary.get('clean_sand_percentage', 0)}%\n"
        summary += f"🪨 Shale: {lithology_summary.get('shale_percentage', 0)}%\n"
        summary += f"🔀 Mixed: {lithology_summary.get('mixed_percentage', 0)}%\n\n"
        
        zones = result.get('lithology_zones', [])
        summary += f"📊 Found {len(zones)} lithology zones\n"
        
        formation_tops = result.get('formation_tops', [])
        if formation_tops:
            summary += f"🏔️ Identified {len(formation_tops)} formation tops\n"
        
        return summary
    else:
        return f"❌ Error analyzing lithology: {result.get('error', 'Unknown error')}"

@mcp.tool()
def analyze_reservoir_porosity_quality(filename: str) -> str:
    """Analyze porosity data for reservoir quality assessment."""
    result = analyze_porosity_quality(filename)
    if result.get('success'):
        summary = f"🧪 Porosity Quality Analysis for {filename}\n\n"
        
        quality_summary = result.get('quality_summary', {})
        if quality_summary:
            summary += f"📏 Total interval: {quality_summary.get('total_interval_ft', 'N/A')} ft\n"
            summary += f"✅ Good reservoir: {quality_summary.get('good_reservoir_ft', 'N/A')} ft\n"
            summary += f"📊 Net-to-gross: {quality_summary.get('net_to_gross_ratio', 'N/A')}%\n"
            summary += f"🕳️ Average porosity: {quality_summary.get('average_porosity', 'N/A')}%\n"
        
        zones = result.get('porosity_zones', [])
        summary += f"\n📋 Analyzed {len(zones)} porosity zones\n"
        summary += f"📊 Curves used: {', '.join(result.get('curves_used', []))}"
        
        return summary
    else:
        return f"❌ Error analyzing porosity quality: {result.get('error', 'Unknown error')}"

@mcp.tool()
def analyze_fluid_saturation_contacts(filename: str) -> str:
    """Analyze resistivity data for fluid contacts and hydrocarbon identification."""
    result = analyze_fluid_contacts(filename)
    if result.get('success'):
        summary = f"⚡ Fluid Contacts Analysis for {filename}\n\n"
        summary += f"📊 Curve used: {result.get('curve_used', 'N/A')}\n\n"
        
        fluid_zones = result.get('fluid_zones', [])
        summary += f"🌊 Found {len(fluid_zones)} fluid zones\n"
        
        hydrocarbon_summary = result.get('hydrocarbon_summary', {})
        if hydrocarbon_summary:
            summary += f"🛢️ Total hydrocarbon: {hydrocarbon_summary.get('total_hydrocarbon_ft', 0)} ft\n"
            summary += f"🛢️ Oil zones: {len(hydrocarbon_summary.get('oil_zones', []))}\n"
            summary += f"⛽ Gas zones: {len(hydrocarbon_summary.get('gas_zones', []))}\n"
        
        contacts = result.get('fluid_contacts', [])
        if contacts:
            summary += f"\n🔄 Identified {len(contacts)} potential fluid contacts"
        
        return summary
    else:
        return f"❌ Error analyzing fluid contacts: {result.get('error', 'Unknown error')}"

# ===== EMAIL PROCESSING TOOLS =====

@mcp.tool()
def process_incoming_email(sender_email: str, subject: str, body: str) -> str:
    """Process an incoming email and generate comprehensive analysis and response."""
    result = process_email_content(subject, body, sender_email)
    if result.get('success'):
        summary = f"📧 Email Processing Results\n\n"
        summary += f"👤 From: {result.get('sender', 'N/A')}\n"
        summary += f"📋 Subject: {result.get('subject', 'N/A')}\n\n"
        
        processing_results = result.get('processing_results', {})
        
        # Content analysis
        content_analysis = processing_results.get('content_analysis', {})
        if content_analysis:
            summary += f"📊 Analysis:\n"
            summary += f"  • Type: {content_analysis.get('type', 'N/A')}\n"
            summary += f"  • Priority: {content_analysis.get('priority_level', 'N/A')}\n"
            summary += f"  • Action required: {content_analysis.get('action_required', False)}\n"
        
        # Sentiment
        sentiment = processing_results.get('sentiment', {})
        if sentiment:
            summary += f"🎭 Sentiment: {sentiment.get('sentiment', 'N/A')} ({sentiment.get('confidence', 0)}% confidence)\n"
        
        # Priority
        priority = processing_results.get('priority', {})
        if priority:
            summary += f"⚡ Priority: {priority.get('priority_level', 'N/A')} - {priority.get('response_time_expectation', 'N/A')}\n"
        
        summary += f"\n✅ Email processing completed successfully"
        return summary
    else:
        return f"❌ Error processing email: {result.get('error', 'Unknown error')}"

@mcp.tool()
def handle_email_attachments_processing(attachments: str) -> str:
    """Process email attachments, particularly LAS files."""
    # Convert string to list (assuming comma-separated)
    attachment_list = [att.strip() for att in attachments.split(',') if att.strip()]
    
    result = handle_email_attachments(attachment_list)
    if result.get('error'):
        return f"❌ Error handling attachments: {result['error']}"
    
    summary = f"📎 Attachment Processing Results\n\n"
    summary += f"📋 Total attachments: {result.get('attachment_count', 0)}\n"
    
    attachment_summary = result.get('summary', {})
    if attachment_summary:
        summary += f"📁 LAS files: {attachment_summary.get('las_files', 0)}\n"
        summary += f"📄 Other files: {attachment_summary.get('other_files', 0)}\n"
        summary += f"⚙️ Ready for analysis: {attachment_summary.get('ready_for_analysis', 0)}\n"
    
    las_files = result.get('las_files_found', [])
    if las_files:
        summary += f"\n🔍 LAS files ready for analysis:\n"
        for las_file in las_files:
            summary += f"  • {las_file}\n"
    
    return summary

# ===== INTEGRATED WORKFLOW TOOLS =====

@mcp.tool()
def run_complete_las_analysis(filename: str) -> str:
    """Run complete LAS file analysis including validation, analysis, and plotting."""
    results = []
    
    # Step 1: Validate file
    validation = validate_las_file(filename)
    if not validation.get('success'):
        return f"❌ File validation failed: {validation.get('error', 'Unknown error')}"
    results.append("✅ File validation passed")
    
    # Step 2: Basic analysis
    analysis = analyze_las_file(filename)
    if analysis.get('success'):
        results.append(f"✅ Basic analysis completed - {analysis.get('curve_count', 0)} curves found")
    
    # Step 3: Lithology analysis
    lithology = analyze_gamma_ray_lithology(filename)
    if lithology.get('success'):
        results.append("✅ Gamma ray lithology analysis completed")
    
    # Step 4: Porosity analysis
    porosity = analyze_porosity_quality(filename)
    if porosity.get('success'):
        results.append("✅ Porosity quality analysis completed")
    
    # Step 5: Create plots
    gamma_plot = create_gamma_ray_plot(filename)
    if gamma_plot.get('success'):
        results.append(f"✅ Gamma ray plot created: {gamma_plot['output_file']}")
    
    porosity_plot = create_porosity_plot(filename)
    if porosity_plot.get('success'):
        results.append(f"✅ Porosity plot created: {porosity_plot['output_file']}")
    
    summary = f"🔄 Complete LAS Analysis Results for {filename}\n\n"
    summary += '\n'.join(results)
    summary += f"\n\n📊 Analysis completed with {len(results)} successful steps"
    
    return summary

async def main():
    """Main function to run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())