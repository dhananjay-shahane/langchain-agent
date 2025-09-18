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


def create_density_plot(filename: str) -> Dict[str, Any]:
    """Create a real density plot from LAS file data."""
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
        
        # Find density and caliper curves
        rhob_column = None
        cali_column = None
        
        # Try different names for bulk density
        for col in ['RHOB', 'DENSITY', 'DEN', 'RHOZ']:
            if col in df.columns:
                rhob_column = col
                break
        
        # Try different names for caliper
        for col in ['CALI', 'CALIPER', 'CAL', 'BS']:
            if col in df.columns:
                cali_column = col
                break
        
        if rhob_column is None and cali_column is None:
            return {
                'error': f"No density or caliper curves found in {filename}",
                'success': False
            }
        
        # Create subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 12), sharey=True)
        
        depth = df.index
        plot_curves = []
        
        # Plot density on first subplot
        if rhob_column:
            rhob = df[rhob_column]
            mask_rhob = ~(np.isnan(rhob) | np.isnan(depth))
            if mask_rhob.any():
                ax1.plot(rhob[mask_rhob], depth[mask_rhob], 'purple', 
                        linewidth=1.5, label='Bulk Density', alpha=0.8)
                plot_curves.append(f'Density ({rhob_column})')
                
                # Add density interpretation zones
                ax1.axvspan(1.5, 2.2, alpha=0.1, color='blue', label='Water/Shale')
                ax1.axvspan(2.2, 2.6, alpha=0.1, color='yellow', label='Sandstone')
                ax1.axvspan(2.6, 2.9, alpha=0.1, color='green', label='Carbonate')
        
        # Plot caliper on second subplot
        if cali_column:
            cali = df[cali_column]
            mask_cali = ~(np.isnan(cali) | np.isnan(depth))
            if mask_cali.any():
                ax2.plot(cali[mask_cali], depth[mask_cali], 'brown', 
                        linewidth=1.5, label='Caliper', alpha=0.8)
                ax2.fill_betweenx(depth[mask_cali], 0, cali[mask_cali], 
                                alpha=0.3, color='brown')
                plot_curves.append(f'Caliper ({cali_column})')
                
                # Add typical borehole size reference
                bit_size = 8.5  # Typical bit size
                ax2.axvline(bit_size, color='red', linestyle='--', 
                           label=f'Bit Size ({bit_size}")')
        
        # Format density subplot
        if rhob_column:
            ax1.set_xlabel('Bulk Density (g/cm³)', fontsize=12)
            ax1.set_xlim(1.5, 3.0)
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='lower right')
        
        # Format caliper subplot  
        if cali_column:
            ax2.set_xlabel('Caliper (inches)', fontsize=12)
            ax2.set_xlim(6, 16)
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='lower right')
        
        # Common formatting
        ax1.set_ylabel('Depth (ft)', fontsize=12)
        ax1.invert_yaxis()
        fig.suptitle(f'Density & Caliper Log\n{filename}', fontsize=14)
        
        # Add statistics
        stats_lines = [f"Curves: {', '.join(plot_curves)}"]
        if rhob_column and mask_rhob.any():
            rhob_clean = rhob[mask_rhob]
            stats_lines.append(f"Density: {rhob_clean.mean():.2f}±{rhob_clean.std():.2f} g/cm³")
        if cali_column and mask_cali.any():
            cali_clean = cali[mask_cali]
            stats_lines.append(f"Caliper: {cali_clean.mean():.1f}±{cali_clean.std():.1f} in")
            
        stats_text = '\n'.join(stats_lines)
        ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                verticalalignment='top', fontsize=10)
        
        plt.tight_layout()
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_density_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        output_path.parent.mkdir(exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'success': True,
            'output_file': output_filename,
            'curves_plotted': plot_curves,
            'density_column': rhob_column,
            'caliper_column': cali_column
        }
        
    except Exception as e:
        return {
            'error': f"Error creating density plot for {filename}: {str(e)}",
            'success': False
        }


def create_composite_plot(filename: str) -> Dict[str, Any]:
    """Create a composite log plot with multiple tracks."""
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
        depth = df.index
        
        # Define available tracks
        tracks = []
        
        # Track 1: Natural logs (GR, SP)
        track1_curves = []
        if any(col in df.columns for col in ['GR', 'GAMMA']):
            gr_col = next((col for col in ['GR', 'GAMMA'] if col in df.columns), None)
            track1_curves.append((gr_col, 'Gamma Ray (API)', 'green', (0, 150)))
        if 'SP' in df.columns:
            track1_curves.append(('SP', 'SP (mV)', 'red', (-100, 50)))
        if track1_curves:
            tracks.append(('Natural Logs', track1_curves))
        
        # Track 2: Resistivity
        track2_curves = []
        for col in ['RT', 'RES', 'ILD']:
            if col in df.columns:
                track2_curves.append((col, f'{col} (Ω.m)', 'blue', (0.1, 1000)))
                break
        if track2_curves:
            tracks.append(('Resistivity', track2_curves))
        
        # Track 3: Porosity
        track3_curves = []
        if 'NPHI' in df.columns:
            track3_curves.append(('NPHI', 'Neutron (%)', 'blue', (0, 40)))
        if 'DPHI' in df.columns:
            track3_curves.append(('DPHI', 'Density (%)', 'red', (0, 40)))
        if track3_curves:
            tracks.append(('Porosity', track3_curves))
        
        # Track 4: Density & Caliper
        track4_curves = []
        if 'RHOB' in df.columns:
            track4_curves.append(('RHOB', 'Density (g/cm³)', 'purple', (1.5, 3.0)))
        if 'CALI' in df.columns:
            track4_curves.append(('CALI', 'Caliper (in)', 'brown', (6, 16)))
        if track4_curves:
            tracks.append(('Density/Caliper', track4_curves))
        
        if not tracks:
            return {
                'error': f"No suitable curves found for composite plot in {filename}",
                'success': False
            }
        
        # Create subplots
        fig, axes = plt.subplots(1, len(tracks), figsize=(4 * len(tracks), 16), 
                                sharey=True, tight_layout=True)
        if len(tracks) == 1:
            axes = [axes]
        
        plotted_curves = []
        
        # Plot each track
        for i, (track_name, curves) in enumerate(tracks):
            ax = axes[i]
            colors = ['blue', 'red', 'green', 'orange', 'purple']
            
            for j, (col, label, default_color, xlim) in enumerate(curves):
                if col in df.columns:
                    data = df[col]
                    mask = ~(np.isnan(data) | np.isnan(depth))
                    
                    if mask.any():
                        color = colors[j % len(colors)] if j < len(colors) else default_color
                        
                        # Use log scale for resistivity
                        if 'resistivity' in track_name.lower() or col in ['RT', 'RES', 'ILD']:
                            mask = mask & (data > 0)
                            if mask.any():
                                ax.semilogx(data[mask], depth[mask], color=color,
                                          linewidth=1.5, label=col, alpha=0.8)
                        else:
                            # Convert porosity to percentage
                            if col in ['NPHI', 'DPHI'] and data[mask].max() <= 1:
                                data = data * 100
                            ax.plot(data[mask], depth[mask], color=color,
                                  linewidth=1.5, label=col, alpha=0.8)
                        
                        plotted_curves.append(f"{col} ({track_name})")
            
            # Format subplot
            ax.invert_yaxis()
            ax.set_xlabel(track_name, fontsize=10)
            if i == 0:
                ax.set_ylabel('Depth (ft)', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8, loc='lower right')
            
            # Set x-axis limits based on first curve
            if curves:
                _, _, _, xlim = curves[0]
                ax.set_xlim(xlim)
        
        fig.suptitle(f'Composite Log\n{filename}', fontsize=16, fontweight='bold')
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_composite_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        output_path.parent.mkdir(exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'success': True,
            'output_file': output_filename,
            'tracks_plotted': len(tracks),
            'curves_plotted': plotted_curves,
            'track_names': [track[0] for track in tracks]
        }
        
    except Exception as e:
        return {
            'error': f"Error creating composite plot for {filename}: {str(e)}",
            'success': False
        }


if __name__ == "__main__":
    # Command line interface for testing
    if len(sys.argv) < 3:
        print("Usage: python log_plotter.py <plot_type> <filename>")
        print("Plot types: gamma, porosity, resistivity, density, composite")
        sys.exit(1)
    
    plot_type = sys.argv[1]
    filename = sys.argv[2]
    
    if plot_type == "gamma":
        result = create_gamma_ray_plot(filename)
    elif plot_type == "porosity":
        result = create_porosity_plot(filename)
    elif plot_type == "resistivity":
        result = create_resistivity_plot(filename)
    elif plot_type == "density":
        result = create_density_plot(filename)
    elif plot_type == "composite":
        result = create_composite_plot(filename)
    else:
        print(f"Unknown plot type: {plot_type}")
        sys.exit(1)
    
    print(result)