#!/usr/bin/env python3
"""
Composite Log Plot Script
Creates multi-curve composite log visualization from LAS file
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


def create_composite_plot(las_filepath, output_dir="output"):
    """Create composite log plot with multiple tracks"""
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Read LAS file
        df, header_info = read_las_file(las_filepath)
        
        # Check for required columns
        if 'DEPT' not in df.columns:
            raise ValueError("DEPT column not found in LAS file")
        
        # Define track configurations
        tracks = []
        
        # Track 1: Gamma Ray and SP
        track1_curves = []
        if 'GR' in df.columns:
            track1_curves.append(('GR', 'Gamma Ray (API)', 'green', (0, 150), False))
        if 'SP' in df.columns:
            track1_curves.append(('SP', 'SP (mV)', 'red', (-100, 50), False))
        if track1_curves:
            tracks.append(('Natural Logs', track1_curves))
        
        # Track 2: Resistivity
        track2_curves = []
        if 'RT' in df.columns:
            track2_curves.append(('RT', 'Deep Resistivity (ohm-m)', 'red', (0.1, 1000), True))
        if 'RXO' in df.columns:
            track2_curves.append(('RXO', 'Shallow Resistivity (ohm-m)', 'blue', (0.1, 1000), True))
        if track2_curves:
            tracks.append(('Resistivity', track2_curves))
        
        # Track 3: Porosity and Density
        track3_curves = []
        if 'NPHI' in df.columns:
            track3_curves.append(('NPHI', 'Neutron Porosity (v/v)', 'blue', (0, 0.4), False))
        if 'DPHI' in df.columns:
            track3_curves.append(('DPHI', 'Density Porosity (v/v)', 'red', (0, 0.4), False))
        if 'RHOB' in df.columns:
            track3_curves.append(('RHOB', 'Bulk Density (g/cm³)', 'purple', (1.5, 3.0), False))
        if track3_curves:
            tracks.append(('Porosity & Density', track3_curves))
        
        # Track 4: Caliper and Photoelectric Factor
        track4_curves = []
        if 'CALI' in df.columns:
            track4_curves.append(('CALI', 'Caliper (in)', 'brown', (6, 16), False))
        if 'PE' in df.columns:
            track4_curves.append(('PE', 'Photoelectric Factor (b/e)', 'orange', (0, 10), False))
        if track4_curves:
            tracks.append(('Caliper & PE', track4_curves))
        
        if not tracks:
            raise ValueError("No suitable curves found for composite plot")
        
        # Create subplots
        fig, axes = plt.subplots(1, len(tracks), figsize=(4 * len(tracks), 16), sharey=True)
        if len(tracks) == 1:
            axes = [axes]
        
        # Plot each track
        for i, (track_name, curves) in enumerate(tracks):
            ax = axes[i]
            
            for col, label, color, xlim, log_scale in curves:
                if col in df.columns:
                    clean_df = df[['DEPT', col]].dropna()
                    if not clean_df.empty:
                        if log_scale:
                            # Filter positive values for log scale
                            clean_df = clean_df[clean_df[col] > 0]
                            if not clean_df.empty:
                                ax.semilogx(clean_df[col], clean_df['DEPT'], 
                                          color=color, linewidth=1.5, label=col)
                        else:
                            ax.plot(clean_df[col], clean_df['DEPT'], 
                                  color=color, linewidth=1.5, label=col)
            
            # Format each track
            ax.invert_yaxis()
            ax.set_xlabel(f'{track_name}', fontsize=10)
            if i == 0:
                ax.set_ylabel('Depth (ft)', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
            
            # Set appropriate x-axis limits based on first curve in track
            if curves:
                _, _, _, xlim, _ = curves[0]
                ax.set_xlim(xlim)
        
        # Title from well info
        well_name = header_info.get('WELL', 'Unknown Well')
        fig.suptitle(f'{well_name} - Composite Log', fontsize=16, fontweight='bold')
        
        # Tight layout
        plt.tight_layout()
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        well_clean = well_name.replace(' ', '_').replace('-', '_')
        output_filename = f"{well_clean}_composite_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save plot
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_filename
        
    except Exception as e:
        raise ValueError(f"Error creating composite plot: {str(e)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_composite_log.py <las_filename>")
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
        output_filename = create_composite_plot(las_filepath)
        print(f"Composite Log Plot Created: {output_filename}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()