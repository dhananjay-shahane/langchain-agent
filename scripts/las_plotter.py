#!/usr/bin/env python3
"""
LAS File Plotting Script
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import lasio

def create_las_plot(filename: str, curve_type: str = "porosity"):
    """Create a plot from LAS file data"""
    try:
        file_path = Path("data") / filename
        if not file_path.exists():
            print(f"Error: LAS file '{filename}' not found")
            return None
        
        # Read actual LAS file data
        las = lasio.read(file_path)
        
        # Get depth data
        depth = las.depth()
        if depth is None or len(depth) == 0:
            print(f"Error: No depth data found in {filename}")
            return None
        
        # Determine which curve to plot
        curve_name = None
        data = None
        unit = ""
        title = ""
        
        if curve_type.lower() == "porosity":
            # Look for common porosity curve names
            possible_names = ['NPHI', 'PHIN', 'NPOR', 'PHI', 'PHIT', 'PHIE']
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    unit = las.curves[name].unit or "%"
                    title = "Porosity"
                    break
        elif curve_type.lower() == "gamma":
            # Look for common gamma ray curve names
            possible_names = ['GR', 'GRD', 'CGR', 'SGR', 'GAMMA', 'GRS']
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    unit = las.curves[name].unit or "API"
                    title = "Gamma Ray"
                    break
        elif curve_type.lower() == "resistivity":
            # Look for common resistivity curve names
            possible_names = ['RT', 'RES', 'ILD', 'ILM', 'LLD', 'LLS', 'RDEP', 'RMED']
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    unit = las.curves[name].unit or "ohm.m"
                    title = "Resistivity"
                    break
        
        # If no specific curve found, try to find any available curve
        if data is None:
            available_curves = [c.mnemonic for c in las.curves if c.mnemonic != 'DEPT']
            if available_curves:
                curve_name = available_curves[0]
                data = las[curve_name]
                unit = las.curves[curve_name].unit or ""
                title = curve_name
                print(f"Using available curve: {curve_name}")
            else:
                print(f"No suitable curves found in {filename}")
                return None
        
        # Clean the data - remove NaN values
        valid_indices = ~np.isnan(data)
        depth_clean = depth[valid_indices]
        data_clean = data[valid_indices]
        
        if len(data_clean) == 0:
            print(f"No valid data points found for {curve_name}")
            return None
        
        # Create plot
        fig, ax = plt.subplots(figsize=(8, 12))
        
        if curve_type.lower() == "resistivity" and np.any(data_clean > 0):
            ax.semilogx(data_clean, depth_clean, 'r-', linewidth=2)
        else:
            ax.plot(data_clean, depth_clean, 'b-', linewidth=2)
        
        ax.set_ylabel('Depth (ft)', fontsize=14)
        ax.set_xlabel(f'{title} ({unit})', fontsize=14)
        ax.set_title(f'Depth vs {title}\n{filename}', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()  # Depth increases downward
        
        # Add formation markers based on actual depth range
        depth_range = depth_clean.max() - depth_clean.min()
        depth_mid = depth_clean.min() + depth_range / 2
        
        if depth_range > 300:  # Only add markers for significant depth ranges
            formations = [
                ("Formation A", depth_clean.min() + depth_range * 0.2),
                ("Formation B", depth_mid),
                ("Formation C", depth_clean.min() + depth_range * 0.8)
            ]
            
            for name, depth_marker in formations:
                if depth_clean.min() <= depth_marker <= depth_clean.max():
                    ax.axhline(y=depth_marker, color='gray', linestyle='--', alpha=0.7)
                    ax.text(ax.get_xlim()[1] * 0.7, depth_marker + depth_range * 0.01, name, 
                           fontsize=10, style='italic', alpha=0.8)
        
        # Add data statistics
        ax.text(0.02, 0.98, f'Data points: {len(data_clean)}', 
                transform=ax.transAxes, fontsize=10, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
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
