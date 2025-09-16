#!/usr/bin/env python3
"""
Log Plotter MCP Tool
Real plotting functionality for LAS files using matplotlib
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add the packages to path
sys.path.extend([
    '/nix/store/zz7i75jb78idaz0rb1y1i4rzdyxq28vf-sitecustomize/lib/python/site-packages',
    '/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages'
])

import lasio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.ticker import MultipleLocator


def create_gamma_ray_plot(filename: str) -> Dict[str, Any]:
    """Create a real gamma ray plot from LAS file data."""
    try:
        # Find and read LAS file
        data_dir = Path("data")
        las_path = None
        
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {
                'error': f"LAS file '{filename}' not found",
                'success': False
            }
        
        # Read LAS file
        las = lasio.read(las_path)
        df = las.df()
        
        # Find gamma ray curve (try different common names)
        gr_column = None
        for col in ['GR', 'GAMMA', 'GAMMA_RAY', 'GRC']:
            if col in df.columns:
                gr_column = col
                break
        
        if gr_column is None:
            return {
                'error': f"No gamma ray curve found in {filename}",
                'success': False
            }
        
        # Create plot
        fig, ax = plt.subplots(figsize=(8, 12))
        
        # Plot gamma ray vs depth
        depth = df.index
        gamma = df[gr_column]
        
        # Remove NaN values
        mask = ~(np.isnan(gamma) | np.isnan(depth))
        depth_clean = depth[mask]
        gamma_clean = gamma[mask]
        
        if len(depth_clean) == 0:
            return {
                'error': f"No valid gamma ray data in {filename}",
                'success': False
            }
        
        # Plot gamma ray log
        ax.plot(gamma_clean, depth_clean, 'g-', linewidth=1, label='Gamma Ray')
        
        # Add shading for lithology interpretation
        gamma_min, gamma_max = gamma_clean.min(), gamma_clean.max()
        
        # Sand zones (low GR)
        ax.axvspan(0, 60, alpha=0.1, color='yellow', label='Clean Sand (<60 API)')
        
        # Shale zones (high GR)
        if gamma_max > 100:
            ax.axvspan(100, gamma_max, alpha=0.1, color='brown', label='Shale (>100 API)')
        
        # Formatting
        ax.set_xlabel('Gamma Ray (API)', fontsize=12)
        ax.set_ylabel('Depth (ft)', fontsize=12)
        ax.set_title(f'Gamma Ray Log\n{filename}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()  # Depth increases downward
        
        # Set reasonable x-axis limits
        ax.set_xlim(0, max(200, gamma_max * 1.1))
        
        # Add statistics
        stats_text = f"""Statistics:
Min: {gamma_clean.min():.1f} API
Max: {gamma_clean.max():.1f} API  
Mean: {gamma_clean.mean():.1f} API
Depth: {depth_clean.min():.0f}-{depth_clean.max():.0f} ft"""
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                verticalalignment='top', fontsize=10)
        
        ax.legend(loc='lower right')
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_gamma_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        output_path.parent.mkdir(exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'success': True,
            'output_file': output_filename,
            'curve_used': gr_column,
            'data_points': len(depth_clean),
            'depth_range': f"{depth_clean.min():.0f}-{depth_clean.max():.0f} ft",
            'gamma_range': f"{gamma_clean.min():.1f}-{gamma_clean.max():.1f} API",
            'statistics': {
                'min': float(gamma_clean.min()),
                'max': float(gamma_clean.max()),
                'mean': float(gamma_clean.mean()),
                'std': float(gamma_clean.std())
            }
        }
        
    except Exception as e:
        return {
            'error': f"Error creating gamma ray plot for {filename}: {str(e)}",
            'success': False
        }


def create_porosity_plot(filename: str) -> Dict[str, Any]:
    """Create a real porosity plot from LAS file data."""
    try:
        # Find and read LAS file
        data_dir = Path("data")
        las_path = None
        
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {
                'error': f"LAS file '{filename}' not found",
                'success': False
            }
        
        # Read LAS file
        las = lasio.read(las_path)
        df = las.df()
        
        # Find porosity curves
        nphi_column = None
        dphi_column = None
        
        # Try different common names for neutron porosity
        for col in ['NPHI', 'NEUTRON', 'PHIN', 'PHI_N']:
            if col in df.columns:
                nphi_column = col
                break
        
        # Try different common names for density porosity
        for col in ['DPHI', 'DENSITY_POR', 'PHI_D', 'PHID']:
            if col in df.columns:
                dphi_column = col
                break
        
        if nphi_column is None and dphi_column is None:
            return {
                'error': f"No porosity curves found in {filename}",
                'success': False
            }
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 12))
        
        depth = df.index
        plot_legend = []
        
        # Plot neutron porosity if available
        if nphi_column:
            nphi = df[nphi_column]
            mask_nphi = ~(np.isnan(nphi) | np.isnan(depth))
            if mask_nphi.any():
                ax.plot(nphi[mask_nphi] * 100, depth[mask_nphi], 'b-', 
                       linewidth=1.5, label='Neutron Porosity', alpha=0.8)
                plot_legend.append(f'Neutron ({nphi_column})')
        
        # Plot density porosity if available
        if dphi_column:
            dphi = df[dphi_column]
            mask_dphi = ~(np.isnan(dphi) | np.isnan(depth))
            if mask_dphi.any():
                ax.plot(dphi[mask_dphi] * 100, depth[mask_dphi], 'r--', 
                       linewidth=1.5, label='Density Porosity', alpha=0.8)
                plot_legend.append(f'Density ({dphi_column})')
        
        # Add porosity quality zones
        ax.axvspan(0, 10, alpha=0.1, color='red', label='Tight (<10%)')
        ax.axvspan(10, 20, alpha=0.1, color='yellow', label='Fair (10-20%)')
        ax.axvspan(20, 100, alpha=0.1, color='green', label='Good (>20%)')
        
        # Formatting
        ax.set_xlabel('Porosity (%)', fontsize=12)
        ax.set_ylabel('Depth (ft)', fontsize=12)
        ax.set_title(f'Porosity Log\n{filename}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()
        ax.set_xlim(0, 40)  # Typical porosity range
        
        # Add statistics
        stats_lines = [f"Curves plotted: {', '.join(plot_legend)}"]
        
        if nphi_column and mask_nphi.any():
            nphi_clean = nphi[mask_nphi] * 100
            stats_lines.append(f"Neutron: {nphi_clean.mean():.1f}±{nphi_clean.std():.1f}%")
        
        if dphi_column and mask_dphi.any():
            dphi_clean = dphi[mask_dphi] * 100
            stats_lines.append(f"Density: {dphi_clean.mean():.1f}±{dphi_clean.std():.1f}%")
        
        stats_text = '\n'.join(stats_lines)
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                verticalalignment='top', fontsize=10)
        
        ax.legend(loc='lower right')
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_porosity_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        output_path.parent.mkdir(exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'success': True,
            'output_file': output_filename,
            'curves_plotted': plot_legend,
            'neutron_column': nphi_column,
            'density_column': dphi_column
        }
        
    except Exception as e:
        return {
            'error': f"Error creating porosity plot for {filename}: {str(e)}",
            'success': False
        }


def create_resistivity_plot(filename: str) -> Dict[str, Any]:
    """Create a real resistivity plot from LAS file data."""
    try:
        # Find and read LAS file
        data_dir = Path("data")
        las_path = None
        
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {
                'error': f"LAS file '{filename}' not found",
                'success': False
            }
        
        # Read LAS file
        las = lasio.read(las_path)
        df = las.df()
        
        # Find resistivity curves
        res_columns = []
        for col in ['RT', 'RES', 'RESISTIVITY', 'ILD', 'AT90']:
            if col in df.columns:
                res_columns.append(col)
        
        if not res_columns:
            return {
                'error': f"No resistivity curves found in {filename}",
                'success': False
            }
        
        # Create plot with log scale
        fig, ax = plt.subplots(figsize=(8, 12))
        
        depth = df.index
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        
        for i, res_col in enumerate(res_columns[:5]):  # Limit to 5 curves
            res_data = df[res_col]
            mask = ~(np.isnan(res_data) | np.isnan(depth)) & (res_data > 0)
            
            if mask.any():
                ax.semilogx(res_data[mask], depth[mask], 
                           color=colors[i % len(colors)], 
                           linewidth=1.5, label=res_col, alpha=0.8)
        
        # Add resistivity interpretation zones
        ax.axvspan(0.1, 2, alpha=0.1, color='blue', label='Water (0.1-2 Ω.m)')
        ax.axvspan(2, 20, alpha=0.1, color='yellow', label='Transition (2-20 Ω.m)')
        ax.axvspan(20, 1000, alpha=0.1, color='green', label='Oil/Gas (>20 Ω.m)')
        
        # Formatting
        ax.set_xlabel('Resistivity (Ω.m)', fontsize=12)
        ax.set_ylabel('Depth (ft)', fontsize=12)
        ax.set_title(f'Resistivity Log\n{filename}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()
        ax.set_xlim(0.1, 1000)
        
        # Add statistics
        stats_lines = [f"Curves: {', '.join(res_columns)}"]
        for res_col in res_columns[:3]:
            if res_col in df.columns:
                res_clean = df[res_col].dropna()
                if len(res_clean) > 0:
                    stats_lines.append(f"{res_col}: {res_clean.median():.1f} Ω.m (median)")
        
        stats_text = '\n'.join(stats_lines)
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                verticalalignment='top', fontsize=10)
        
        ax.legend(loc='lower right')
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_resistivity_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        output_path.parent.mkdir(exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'success': True,
            'output_file': output_filename,
            'curves_plotted': res_columns
        }
        
    except Exception as e:
        return {
            'error': f"Error creating resistivity plot for {filename}: {str(e)}",
            'success': False
        }


if __name__ == "__main__":
    # Command line interface for testing
    if len(sys.argv) < 3:
        print("Usage: python log_plotter.py <plot_type> <filename>")
        print("Plot types: gamma, porosity, resistivity")
        sys.exit(1)
    
    plot_type = sys.argv[1]
    filename = sys.argv[2]
    
    if plot_type == "gamma":
        result = create_gamma_ray_plot(filename)
    elif plot_type == "porosity":
        result = create_porosity_plot(filename)
    elif plot_type == "resistivity":
        result = create_resistivity_plot(filename)
    else:
        print(f"Unknown plot type: {plot_type}")
        sys.exit(1)
    
    print(result)