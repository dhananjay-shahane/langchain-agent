#!/usr/bin/env python3
"""
Porosity Depth Plot Script
Creates depth vs porosity visualization from LAS file
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


def create_porosity_plot(las_filepath, output_dir="output"):
    """Create porosity vs depth plot"""
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Read LAS file
        df, header_info = read_las_file(las_filepath)
        
        # Check for required columns
        if 'DEPT' not in df.columns:
            raise ValueError("DEPT column not found in LAS file")
        
        porosity_cols = []
        if 'NPHI' in df.columns:
            porosity_cols.append(('NPHI', 'Neutron Porosity', 'blue'))
        if 'DPHI' in df.columns:
            porosity_cols.append(('DPHI', 'Density Porosity', 'red'))
        if 'PHIT' in df.columns:
            porosity_cols.append(('PHIT', 'Total Porosity', 'green'))
        
        if not porosity_cols:
            raise ValueError("No porosity columns found (NPHI, DPHI, or PHIT)")
        
        # Create plot
        fig, ax = plt.subplots(figsize=(8, 12))
        
        # Plot porosity curves
        for col, label, color in porosity_cols:
            clean_df = df[['DEPT', col]].dropna()
            if not clean_df.empty:
                ax.plot(clean_df[col], clean_df['DEPT'], color=color, linewidth=1.5, label=label)
        
        # Formatting
        ax.invert_yaxis()
        ax.set_xlabel('Porosity (v/v)', fontsize=12)
        ax.set_ylabel('Depth (ft)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Set x-axis limits for porosity (0 to 0.4 or max value)
        max_porosity = 0
        for col, _, _ in porosity_cols:
            if col in df.columns:
                col_max = df[col].max()
                if not np.isnan(col_max):
                    max_porosity = max(max_porosity, col_max)
        
        if max_porosity > 0:
            ax.set_xlim(0, min(0.4, max_porosity * 1.1))
        
        # Title from well info
        well_name = header_info.get('WELL', 'Unknown Well')
        ax.set_title(f'{well_name} - Porosity Log', fontsize=14, fontweight='bold')
        
        # Tight layout
        plt.tight_layout()
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        well_clean = well_name.replace(' ', '_').replace('-', '_')
        output_filename = f"{well_clean}_porosity_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save plot
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_filename
        
    except Exception as e:
        raise ValueError(f"Error creating porosity plot: {str(e)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_porosity.py <las_filename>")
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
        output_filename = create_porosity_plot(las_filepath)
        print(f"Porosity Plot Created: {output_filename}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()