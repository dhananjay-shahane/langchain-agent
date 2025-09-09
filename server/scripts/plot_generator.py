#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
from pathlib import Path

def generate_sample_plot(filename, las_file=""):
    """Generate a sample LAS file analysis plot"""
    try:
        # Create figure
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 8))
        fig.suptitle(f'Well Log Analysis - {las_file}' if las_file else 'Well Log Analysis', fontsize=14)
        
        # Generate sample depth data
        depth = np.linspace(2000, 2500, 100)
        
        # Plot 1: Gamma Ray
        gr = 50 + 30 * np.sin(depth/50) + np.random.normal(0, 5, len(depth))
        ax1.plot(gr, depth, 'g-', linewidth=2)
        ax1.set_xlabel('Gamma Ray (API)')
        ax1.set_ylabel('Depth (ft)')
        ax1.set_title('Gamma Ray Log')
        ax1.grid(True, alpha=0.3)
        ax1.invert_yaxis()
        
        # Plot 2: Porosity
        porosity = 0.15 + 0.1 * np.sin(depth/40) + np.random.normal(0, 0.02, len(depth))
        ax2.plot(porosity, depth, 'b-', linewidth=2)
        ax2.set_xlabel('Porosity (fraction)')
        ax2.set_title('Neutron Porosity')
        ax2.grid(True, alpha=0.3)
        ax2.invert_yaxis()
        
        # Plot 3: Resistivity
        resistivity = 10 + 20 * np.exp(-((depth-2250)/100)**2) + np.random.normal(0, 2, len(depth))
        ax3.semilogx(resistivity, depth, 'r-', linewidth=2)
        ax3.set_xlabel('Resistivity (ohm-m)')
        ax3.set_title('Deep Resistivity')
        ax3.grid(True, alpha=0.3)
        ax3.invert_yaxis()
        
        plt.tight_layout()
        
        # Save to output directory
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / filename
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return True
        
    except Exception as e:
        print(f"Error generating plot: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plot_generator.py <output_filename> [las_file]")
        sys.exit(1)
    
    filename = sys.argv[1]
    las_file = sys.argv[2] if len(sys.argv) > 2 else ""
    
    if generate_sample_plot(filename, las_file):
        print(f"Plot generated successfully: {filename}")
    else:
        print("Failed to generate plot")
        sys.exit(1)