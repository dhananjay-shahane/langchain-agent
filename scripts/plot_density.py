#!/usr/bin/env python3
"""
Density Depth Plot Script
Creates depth vs density visualization from LAS file
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from pathlib import Path


def read_las_file(filepath):
    """Read LAS file and extract data"""
    try:
        # Read the file line by line to parse LAS format
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # Find the data section
        data_start = None
        header_info = {}
        curve_info = []
        
        section = None
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('~'):
                section = line
                continue
                
            if '~ASCII' in section or '~A' in section:
                data_start = i
                break
            elif '~CURVE' in section and line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 1:
                    curve_info.append(parts[0].split('.')[0])
            elif '~WELL' in section and ':' in line and not line.startswith('#'):
                parts = line.split(':')
                if len(parts) >= 2:
                    key = parts[0].split('.')[0].strip()
                    value = parts[1].strip()
                    header_info[key] = value
        
        if data_start is None:
            raise ValueError("Could not find data section in LAS file")
        
        # Read data section
        data_lines = []
        for line in lines[data_start:]:
            line = line.strip()
            if line and not line.startswith('#'):
                data_lines.append(line)
        
        # Convert to DataFrame
        data_rows = []
        for line in data_lines:
            values = line.split()
            if len(values) == len(curve_info):
                data_rows.append([float(v) if v != '-999.25' else np.nan for v in values])
        
        df = pd.DataFrame(data_rows, columns=curve_info)
        return df, header_info
        
    except Exception as e:
        raise ValueError(f"Error reading LAS file: {str(e)}")


def create_density_plot(las_filepath, output_dir="output"):
    """Create density vs depth plot"""
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Read LAS file
        df, header_info = read_las_file(las_filepath)
        
        # Check for required columns
        if 'DEPT' not in df.columns:
            raise ValueError("DEPT column not found in LAS file")
        
        # Look for density columns
        density_cols = []
        if 'RHOB' in df.columns:
            density_cols.append(('RHOB', 'Bulk Density', 'purple'))
        if 'DEN' in df.columns:
            density_cols.append(('DEN', 'Density', 'magenta'))
        if 'RHOZ' in df.columns:
            density_cols.append(('RHOZ', 'Formation Density', 'indigo'))
        
        # Also include caliper if available
        if 'CALI' in df.columns:
            density_cols.append(('CALI', 'Caliper', 'brown'))
        
        if not density_cols:
            raise ValueError("No density columns found (RHOB, DEN, RHOZ) or caliper (CALI)")
        
        # Create subplot layout
        fig, axes = plt.subplots(1, 2, figsize=(12, 12), sharey=True)
        
        # Plot density curves
        density_ax = axes[0]
        caliper_ax = axes[1] if 'CALI' in [col[0] for col in density_cols] else None
        
        for col, label, color in density_cols:
            clean_df = df[['DEPT', col]].dropna()
            if not clean_df.empty:
                if col == 'CALI' and caliper_ax is not None:
                    # Plot caliper on second subplot
                    caliper_ax.plot(clean_df[col], clean_df['DEPT'], color=color, linewidth=1.5, label=label)
                    caliper_ax.fill_betweenx(clean_df['DEPT'], 0, clean_df[col], alpha=0.3, color=color)
                else:
                    # Plot density on first subplot
                    density_ax.plot(clean_df[col], clean_df['DEPT'], color=color, linewidth=1.5, label=label)
        
        # Format density subplot
        density_ax.invert_yaxis()
        density_ax.set_xlabel('Density (g/cm³)', fontsize=12)
        density_ax.set_ylabel('Depth (ft)', fontsize=12)
        density_ax.grid(True, alpha=0.3)
        density_ax.legend()
        
        # Set density axis limits (typical range 1.5 to 3.0 g/cm³)
        density_ax.set_xlim(1.5, 3.0)
        
        # Format caliper subplot if exists
        if caliper_ax is not None:
            caliper_ax.invert_yaxis()
            caliper_ax.set_xlabel('Caliper (inches)', fontsize=12)
            caliper_ax.grid(True, alpha=0.3)
            caliper_ax.legend()
            # Typical caliper range 6 to 16 inches
            caliper_ax.set_xlim(6, 16)
        else:
            # Remove the second subplot if no caliper
            fig.delaxes(axes[1])
        
        # Title from well info
        well_name = header_info.get('WELL', 'Unknown Well')
        fig.suptitle(f'{well_name} - Density Log', fontsize=14, fontweight='bold')
        
        # Tight layout
        plt.tight_layout()
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        well_clean = well_name.replace(' ', '_').replace('-', '_')
        output_filename = f"{well_clean}_density_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save plot
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_filename
        
    except Exception as e:
        raise ValueError(f"Error creating density plot: {str(e)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_density.py <las_filename>")
        sys.exit(1)
    
    las_filename = sys.argv[1]
    
    # Construct full path
    if not os.path.isabs(las_filename):
        # Try different locations
        possible_paths = [
            las_filename,
            os.path.join("data", "samples", las_filename),
            os.path.join("data", "email-attachments", las_filename),
            os.path.join("data", las_filename)
        ]
        
        las_filepath = None
        for path in possible_paths:
            if os.path.exists(path):
                las_filepath = path
                break
        
        if las_filepath is None:
            print(f"Error: LAS file '{las_filename}' not found")
            sys.exit(1)
    else:
        las_filepath = las_filename
    
    try:
        output_filename = create_density_plot(las_filepath)
        print(f"Density Plot Created: {output_filename}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()