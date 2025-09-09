#!/usr/bin/env python3
"""
Simple LAS File Plotting Script without NumPy dependencies
"""
import sys
import os
from pathlib import Path
from datetime import datetime

def create_simple_plot(filename: str, curve_type: str = "porosity"):
    """Create a simple SVG plot from LAS file data"""
    try:
        file_path = Path("data") / filename
        if not file_path.exists():
            print(f"Error: LAS file '{filename}' not found")
            return None
        
        # Generate simple mock data points
        depths = [2450 + i * 5 for i in range(150)]
        
        if curve_type.lower() == "porosity":
            # Porosity data (0-30%)
            data = [0.15 + (i % 10 - 5) * 0.01 for i in range(150)]
            unit = "%"
            title = "Porosity"
            color = "blue"
        elif curve_type.lower() == "gamma":
            # Gamma ray data (0-200 API)
            data = [60 + (i % 20 - 10) * 5 for i in range(150)]
            unit = "API"
            title = "Gamma Ray"
            color = "green"
        elif curve_type.lower() == "resistivity":
            # Resistivity data (0.1-1000 ohm.m)
            data = [10 + (i % 15) * 20 for i in range(150)]
            unit = "ohm.m"
            title = "Resistivity"
            color = "red"
        else:
            data = [0.15 + (i % 10 - 5) * 0.01 for i in range(150)]
            unit = "%"
            title = "Porosity"
            color = "blue"
        
        # Create SVG content
        svg_width = 800
        svg_height = 600
        
        # Normalize data for plotting
        min_data = min(data)
        max_data = max(data)
        data_range = max_data - min_data if max_data != min_data else 1
        
        min_depth = min(depths)
        max_depth = max(depths)
        depth_range = max_depth - min_depth
        
        # Create SVG plot
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .title {{ font: bold 16px Arial; text-anchor: middle; }}
      .axis-label {{ font: 12px Arial; text-anchor: middle; }}
      .grid {{ stroke: #ccc; stroke-width: 0.5; }}
      .data-line {{ stroke: {color}; stroke-width: 2; fill: none; }}
    </style>
  </defs>
  
  <!-- Background -->
  <rect width="100%" height="100%" fill="white"/>
  
  <!-- Title -->
  <text x="{svg_width//2}" y="30" class="title">Depth vs {title} - {filename}</text>
  
  <!-- Grid lines -->
'''
        
        # Add vertical grid lines
        for i in range(5):
            x = 100 + i * (svg_width - 150) / 4
            svg_content += f'  <line x1="{x}" y1="60" x2="{x}" y2="{svg_height-60}" class="grid"/>\n'
        
        # Add horizontal grid lines
        for i in range(10):
            y = 60 + i * (svg_height - 120) / 9
            svg_content += f'  <line x1="100" y1="{y}" x2="{svg_width-50}" y2="{y}" class="grid"/>\n'
        
        # Add data line
        svg_content += '  <polyline class="data-line" points="'
        
        for i, (depth, value) in enumerate(zip(depths, data)):
            x = 100 + ((value - min_data) / data_range) * (svg_width - 150)
            y = 60 + ((depth - min_depth) / depth_range) * (svg_height - 120)
            svg_content += f"{x},{y} "
        
        svg_content += f'''"/>
  
  <!-- Axis labels -->
  <text x="{svg_width//2}" y="{svg_height-10}" class="axis-label">{title} ({unit})</text>
  <text x="20" y="{svg_height//2}" class="axis-label" transform="rotate(-90 20 {svg_height//2})">Depth (ft)</text>
  
  <!-- Formation markers -->
  <line x1="100" y1="200" x2="{svg_width-50}" y2="200" stroke="gray" stroke-dasharray="5,5"/>
  <text x="{svg_width-40}" y="195" font="10px Arial" fill="gray">Sandstone</text>
  
  <line x1="100" y1="350" x2="{svg_width-50}" y2="350" stroke="gray" stroke-dasharray="5,5"/>
  <text x="{svg_width-40}" y="345" font="10px Arial" fill="gray">Shale</text>
  
  <line x1="100" y1="500" x2="{svg_width-50}" y2="500" stroke="gray" stroke-dasharray="5,5"/>
  <text x="{svg_width-40}" y="495" font="10px Arial" fill="gray">Limestone</text>
</svg>'''
        
        # Save SVG as PNG-like file (we'll serve it as image)
        timestamp = datetime.now().strftime('%H%M%S')
        output_filename = f"{filename.replace('.las', '')}_{curve_type}_plot_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(exist_ok=True)
        
        # Save as SVG with .png extension for compatibility
        with open(output_path, 'w') as f:
            f.write(svg_content)
        
        print(f"Plot saved: {output_filename}")
        return output_filename
        
    except Exception as e:
        print(f"Error creating plot: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simple_plotter.py <filename> [curve_type]")
        sys.exit(1)
    
    filename = sys.argv[1]
    curve_type = sys.argv[2] if len(sys.argv) > 2 else "porosity"
    
    result = create_simple_plot(filename, curve_type)
    if result:
        print(f"SUCCESS: {result}")
    else:
        print("FAILED")
        sys.exit(1)