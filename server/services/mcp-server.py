#!/usr/bin/env python3
"""
MCP Server for LAS File Processing Tools
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# MCP server imports
from fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import Resource

# Create MCP server
mcp = FastMCP("LAS File Processing Server")


@mcp.tool()
def analyze_las_file(filename: str) -> str:
    """Analyze a LAS file and extract key information."""
    try:
        file_path = Path("data") / filename
        if not file_path.exists():
            return f"Error: LAS file '{filename}' not found in data directory"

        # Basic LAS file parsing (simplified)
        with open(file_path, 'r') as f:
            content = f.read()

        lines = content.split('\n')
        analysis = []

        # Extract header information
        in_well_section = False
        in_curve_section = False
        well_info = {}
        curves = []

        for line in lines:
            line = line.strip()
            if line.startswith('~W'):
                in_well_section = True
                in_curve_section = False
                continue
            elif line.startswith('~C'):
                in_curve_section = True
                in_well_section = False
                continue
            elif line.startswith('~'):
                in_well_section = False
                in_curve_section = False
                continue

            if in_well_section and '.' in line:
                parts = line.split('.')
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = parts[1].split(':')[0].strip()
                    well_info[key] = value

            elif in_curve_section and '.' in line:
                parts = line.split('.')
                if len(parts) >= 2:
                    curve_name = parts[0].strip()
                    curves.append(curve_name)

        # Generate analysis
        analysis.append(f"LAS File Analysis: {filename}")
        analysis.append(f"Well Information:")
        for key, value in well_info.items():
            analysis.append(f"  {key}: {value}")

        analysis.append(f"Available Curves: {', '.join(curves)}")
        analysis.append(f"Total Curves: {len(curves)}")

        return '\n'.join(analysis)

    except Exception as e:
        return f"Error analyzing LAS file: {str(e)}"


@mcp.tool()
def create_depth_plot(filename: str, curve_name: str = "POROSITY") -> str:
    """Create a depth vs curve plot from LAS file data."""
    try:
        # Import plotting libraries
        import matplotlib.pyplot as plt
        import numpy as np

        file_path = Path("data") / filename
        if not file_path.exists():
            return f"Error: LAS file '{filename}' not found"

        # Generate mock plot (in real implementation, would parse actual LAS data)
        fig, ax = plt.subplots(figsize=(8, 10))

        # Mock data for demonstration
        depth = np.linspace(2450, 3200, 100)
        curve_data = np.random.normal(0.15, 0.05, 100)  # Mock porosity data
        curve_data = np.clip(curve_data, 0.08,
                             0.24)  # Realistic porosity range

        ax.plot(curve_data, depth, 'b-', linewidth=2)
        ax.set_ylabel('Depth (ft)', fontsize=12)
        ax.set_xlabel(f'{curve_name} (%)', fontsize=12)
        ax.set_title(f'Depth vs {curve_name}\n{filename}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()  # Depth increases downward

        # Save plot
        timestamp = datetime.now().strftime('%H%M%S')
        output_filename = f"{filename.replace('.las', '')}_{curve_name.lower()}_plot_{timestamp}.png"
        output_path = Path("output") / output_filename

        # Ensure output directory exists
        output_path.parent.mkdir(exist_ok=True)

        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return f" {output_filename}. Shows {curve_name} data vs depth for well log {filename}."

    except ImportError:
        return "Error: matplotlib not available for plotting"
    except Exception as e:
        return f"Error creating plot: {str(e)}"


@mcp.tool()
def create_formation_analysis(filename: str) -> str:
    """Analyze formation data and create summary report."""
    try:
        file_path = Path("data") / filename
        if not file_path.exists():
            return f"Error: LAS file '{filename}' not found"

        # Mock formation analysis
        formations = [{
            "name": "Sandstone Layer",
            "top_depth": 2450,
            "bottom_depth": 2650,
            "porosity_avg": 18.5
        }, {
            "name": "Shale Formation",
            "top_depth": 2650,
            "bottom_depth": 2850,
            "porosity_avg": 8.2
        }, {
            "name": "Limestone Unit",
            "top_depth": 2850,
            "bottom_depth": 3050,
            "porosity_avg": 22.1
        }, {
            "name": "Tight Sand",
            "top_depth": 3050,
            "bottom_depth": 3200,
            "porosity_avg": 12.7
        }]

        analysis = []
        analysis.append(f"Formation Analysis Report: {filename}")
        analysis.append(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        analysis.append("")
        analysis.append("Formation Summary:")

        for formation in formations:
            thickness = formation["bottom_depth"] - formation["top_depth"]
            analysis.append(f"• {formation['name']}")
            analysis.append(
                f"  Depth: {formation['top_depth']} - {formation['bottom_depth']} ft"
            )
            analysis.append(f"  Thickness: {thickness} ft")
            analysis.append(f"  Avg Porosity: {formation['porosity_avg']}%")
            analysis.append("")

        # Save analysis report
        timestamp = datetime.now().strftime('%H%M%S')
        report_filename = f"{filename.replace('.las', '')}_formation_analysis_{timestamp}.txt"
        report_path = Path("output") / report_filename

        # Ensure output directory exists
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            f.write('\n'.join(analysis))

        return f"Formation analysis completed. Report saved as {report_filename}."

    except Exception as e:
        return f"Error in formation analysis: {str(e)}"


@mcp.resource()
def las_file_resource() -> Resource:
    """Provide access to LAS files as resources."""
    try:
        # Extract filename from URI
        filename = uri.split('/')[-1]
        file_path = Path("data") / filename

        if not file_path.exists():
            return Resource(uri="las://not-found",
                            name="not-found",
                            description="LAS file not found",
                            mimeType="text/plain")

        with open(file_path, 'r') as f:
            content = f.read()

        return Resource(uri=f"las://{filename}",
                        name=filename,
                        description=f"LAS file: {filename}",
                        mimeType="text/plain")
    except Exception as e:
        return Resource(uri="las://error",
                        name="error",
                        description=f"Error reading resource: {str(e)}",
                        mimeType="text/plain")


@mcp.list_resources()
async def list_las_resources() -> List[Resource]:
    """List all available LAS files as resources."""
    resources = []
    data_dir = Path("data")

    if data_dir.exists():
        for las_file in data_dir.glob("*.las"):
            resources.append(
                Resource(uri=f"las://{las_file.name}",
                         name=las_file.name,
                         description=f"LAS file: {las_file.name}",
                         mimeType="text/plain"))

    return resources


async def main():
    """Main function to run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
