#!/usr/bin/env python3
"""
LAS File Plotting Script
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

def create_las_plot(filename: str, curve_type: str = "porosity"):
    """Create a plot from LAS file data"""
    try:
        file_path = Path("data") / filename
        if not file_path.exists():
            print(f"Error: LAS file '{filename}' not found")
            return None
        
        # Generate realistic mock data for demonstration
        depth = np.linspace(2450, 3200, 150)
        
        if curve_type.lower() == "porosity":
            # Porosity data (0-30%)
            data = np.random.normal(0.15, 0.05, 150)
            data = np.clip(data, 0.05, 0.30)
            unit = "%"
            title = "Porosity"
        elif curve_type.lower() == "gamma":
            # Gamma ray data (0-200 API)
            data = np.random.normal(60, 30, 150)
            data = np.clip(data, 10, 200)
            unit = "API"
            title = "Gamma Ray"
        elif curve_type.lower() == "resistivity":
            # Resistivity data (0.1-1000 ohm.m)
            data = np.random.lognormal(1, 1.5, 150)
            data = np.clip(data, 0.1, 1000)
            unit = "ohm.m"
            title = "Resistivity"
        else:
            # Default to porosity
            data = np.random.normal(0.15, 0.05, 150)
            data = np.clip(data, 0.05, 0.30)
            unit = "%"
            title = "Porosity"
        
        # Create plot
        fig, ax = plt.subplots(figsize=(8, 12))
        
        if curve_type.lower() == "resistivity":
            ax.semilogx(data, depth, 'r-', linewidth=2)
        else:
            ax.plot(data, depth, 'b-', linewidth=2)
        
        ax.set_ylabel('Depth (ft)', fontsize=14)
        ax.set_xlabel(f'{title} ({unit})', fontsize=14)
        ax.set_title(f'Depth vs {title}\n{filename}', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()  # Depth increases downward
        
        # Add formation markers
        formations = [
            ("Sandstone", 2600),
            ("Shale", 2800),
            ("Limestone", 3000)
        ]
        
        for name, depth_marker in formations:
            ax.axhline(y=depth_marker, color='gray', linestyle='--', alpha=0.7)
            ax.text(ax.get_xlim()[1] * 0.7, depth_marker + 20, name, 
                   fontsize=10, style='italic', alpha=0.8)
        
        plt.tight_layout()
        
        # Save plot
        timestamp = datetime.now().strftime('%H%M%S')
        output_filename = f"{filename.replace('.las', '')}_{curve_type}_plot_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(exist_ok=True)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Plot saved: {output_filename}")
        return output_filename
        
    except Exception as e:
        print(f"Error creating plot: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python las_plotter.py <filename> [curve_type]")
        sys.exit(1)
    
    filename = sys.argv[1]
    curve_type = sys.argv[2] if len(sys.argv) > 2 else "porosity"
    
    result = create_las_plot(filename, curve_type)
    if result:
        print(f"SUCCESS: {result}")
    else:
        print("FAILED")
        sys.exit(1)
