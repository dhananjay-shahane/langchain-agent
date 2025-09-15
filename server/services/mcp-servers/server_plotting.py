#!/usr/bin/env python3
"""
Enhanced MCP Plot Server
Handles real data visualization from LAS files and email queries
"""

from mcp.server import Server
import lasio
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import re

server = Server("plotting")

OUTPUT_DIR = Path("output")
DATA_DIR = Path("data")

def log_step(step: str, tool_name: str, details: str = "") -> None:
    """Log processing steps for tracking"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "tool": tool_name,
        "step": step,
        "details": details
    }
    
    log_file = OUTPUT_DIR / "processing_steps.json"
    
    # Load existing logs
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
    else:
        logs = []
    
    logs.append(log_entry)
    
    # Keep only last 100 entries
    if len(logs) > 100:
        logs = logs[-100:]
    
    # Save updated logs
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)
    
    print(f"[{timestamp}] {tool_name}: {step} - {details}")

@server.tool("parse_email_query")
def parse_email_query(email_content: str, subject: str) -> Dict[str, Any]:
    """Parse email content to extract plotting requirements and data requests"""
    log_step("Starting query parsing", "parse_email_query", f"Subject: {subject}")
    
    try:
        content_lower = email_content.lower()
        subject_lower = subject.lower()
        
        # Extract plot types requested
        plot_types = []
        if any(word in content_lower for word in ['porosity', 'poro', 'phi']):
            plot_types.append('porosity')
        if any(word in content_lower for word in ['gamma', 'gr', 'gamma ray']):
            plot_types.append('gamma')
        if any(word in content_lower for word in ['resistivity', 'resistance', 'rt', 'res']):
            plot_types.append('resistivity')
        if any(word in content_lower for word in ['density', 'rhob', 'bulk density']):
            plot_types.append('density')
        
        # If no specific plots mentioned, default to common ones
        if not plot_types:
            plot_types = ['porosity', 'gamma']
        
        # Extract file references
        las_files = []
        # Look for .las files mentioned
        las_pattern = r'(\w+\.las)'
        las_matches = re.findall(las_pattern, content_lower)
        las_files.extend(las_matches)
        
        # Look for well names
        well_names = []
        well_pattern = r'well\s+(\w+)|(\w+)\s+well'
        well_matches = re.findall(well_pattern, content_lower)
        for match in well_matches:
            well_name = match[0] or match[1]
            if well_name:
                well_names.append(well_name)
        
        # Determine urgency
        urgency = "normal"
        if any(word in content_lower for word in ['urgent', 'asap', 'immediately', 'emergency']):
            urgency = "high"
        elif any(word in content_lower for word in ['soon', 'quickly', 'expedite']):
            urgency = "medium"
        
        result = {
            "plot_types": plot_types,
            "las_files": las_files,
            "well_names": well_names,
            "urgency": urgency,
            "requires_analysis": any(word in content_lower for word in ['analysis', 'interpret', 'analyze', 'formation']),
            "response_type": "plot_generation"
        }
        
        log_step("Query parsing completed", "parse_email_query", f"Found {len(plot_types)} plot types, {len(las_files)} files")
        return result
        
    except Exception as e:
        log_step("Query parsing failed", "parse_email_query", f"Error: {str(e)}")
        return {"error": f"Failed to parse email query: {str(e)}"}

@server.tool("create_las_plot")
def create_las_plot(filename: str, curve_type: str = "porosity", output_prefix: str = "") -> str:
    """Create a plot from actual LAS file data"""
    log_step("Starting plot creation", "create_las_plot", f"File: {filename}, Type: {curve_type}")
    
    try:
        # Find the file in data directory or subdirectories
        las_file = None
        for search_path in [DATA_DIR, DATA_DIR / "samples", DATA_DIR / "email-attachments"]:
            potential_file = search_path / filename
            if potential_file.exists():
                las_file = potential_file
                break
        
        if not las_file:
            error_msg = f"LAS file '{filename}' not found in data directories"
            log_step("File not found", "create_las_plot", error_msg)
            return error_msg
        
        log_step("Reading LAS file", "create_las_plot", f"Found file at: {las_file}")
        
        # Read LAS file
        las = lasio.read(las_file)
        
        # Get depth data
        depth = las.depth()
        if depth is None or len(depth) == 0:
            error_msg = f"No depth data found in {filename}"
            log_step("No depth data", "create_las_plot", error_msg)
            return error_msg
        
        # Determine which curve to plot
        curve_name = None
        data = None
        unit = ""
        title = ""
        
        log_step("Identifying curve", "create_las_plot", f"Looking for {curve_type} curves")
        
        if curve_type.lower() == "porosity":
            possible_names = ['NPHI', 'PHIN', 'NPOR', 'PHI', 'PHIT', 'PHIE']
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    unit = las.curves[name].unit or "%"
                    title = "Porosity"
                    break
        elif curve_type.lower() == "gamma":
            possible_names = ['GR', 'GRD', 'CGR', 'SGR', 'GAMMA', 'GRS']
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    unit = las.curves[name].unit or "API"
                    title = "Gamma Ray"
                    break
        elif curve_type.lower() == "resistivity":
            possible_names = ['RT', 'RES', 'ILD', 'ILM', 'LLD', 'LLS', 'RDEP', 'RMED']
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    unit = las.curves[name].unit or "ohm.m"
                    title = "Resistivity"
                    break
        elif curve_type.lower() == "density":
            possible_names = ['RHOB', 'RHOZ', 'DENS', 'BD']
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    unit = las.curves[name].unit or "g/cc"
                    title = "Bulk Density"
                    break
        
        # If no specific curve found, use first available
        if data is None:
            available_curves = [c.mnemonic for c in las.curves if c.mnemonic != 'DEPT']
            if available_curves:
                curve_name = available_curves[0]
                data = las[curve_name]
                unit = las.curves[curve_name].unit or ""
                title = curve_name
                log_step("Using fallback curve", "create_las_plot", f"Using: {curve_name}")
            else:
                error_msg = f"No suitable curves found in {filename}"
                log_step("No curves found", "create_las_plot", error_msg)
                return error_msg
        
        log_step("Processing data", "create_las_plot", f"Curve: {curve_name}, Points: {len(data)}")
        
        # Clean the data
        valid_indices = ~np.isnan(data)
        depth_clean = depth[valid_indices]
        data_clean = data[valid_indices]
        
        if len(data_clean) == 0:
            error_msg = f"No valid data points found for {curve_name}"
            log_step("No valid data", "create_las_plot", error_msg)
            return error_msg
        
        # Create plot
        fig, ax = plt.subplots(figsize=(8, 12))
        
        if curve_type.lower() == "resistivity" and np.any(data_clean > 0):
            ax.semilogx(data_clean, depth_clean, 'r-', linewidth=2)
        else:
            ax.plot(data_clean, depth_clean, 'b-', linewidth=2)
        
        ax.set_ylabel('Depth (ft)', fontsize=14)
        ax.set_xlabel(f'{title} ({unit})', fontsize=14)
        ax.set_title(f'{title} vs Depth\n{filename}', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()
        
        # Add statistics text box
        stats_text = f'Data points: {len(data_clean)}\nDepth range: {depth_clean.min():.1f} - {depth_clean.max():.1f} ft\nValue range: {data_clean.min():.3f} - {data_clean.max():.3f} {unit}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if output_prefix:
            output_filename = f"{output_prefix}_{filename.replace('.las', '')}_{curve_type}_{timestamp}.png"
        else:
            output_filename = f"{filename.replace('.las', '')}_{curve_type}_{timestamp}.png"
        
        output_path = OUTPUT_DIR / output_filename
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        log_step("Plot created successfully", "create_las_plot", f"Saved: {output_filename}")
        return str(output_filename)
        
    except Exception as e:
        error_msg = f"Error creating plot: {str(e)}"
        log_step("Plot creation failed", "create_las_plot", error_msg)
        return error_msg

@server.tool("create_multi_curve_plot")
def create_multi_curve_plot(filename: str, curve_types: List[str], output_prefix: str = "") -> str:
    """Create a multi-track plot showing multiple curves from LAS file"""
    log_step("Starting multi-curve plot", "create_multi_curve_plot", f"File: {filename}, Curves: {curve_types}")
    
    try:
        # Find the file
        las_file = None
        for search_path in [DATA_DIR, DATA_DIR / "samples", DATA_DIR / "email-attachments"]:
            potential_file = search_path / filename
            if potential_file.exists():
                las_file = potential_file
                break
        
        if not las_file:
            error_msg = f"LAS file '{filename}' not found"
            log_step("File not found", "create_multi_curve_plot", error_msg)
            return error_msg
        
        # Read LAS file
        las = lasio.read(las_file)
        depth = las.depth()
        
        if depth is None or len(depth) == 0:
            error_msg = f"No depth data found in {filename}"
            log_step("No depth data", "create_multi_curve_plot", error_msg)
            return error_msg
        
        # Create subplots
        num_tracks = len(curve_types)
        fig, axes = plt.subplots(1, num_tracks, figsize=(4 * num_tracks, 12), sharey=True)
        
        if num_tracks == 1:
            axes = [axes]
        
        curves_plotted = []
        
        for i, curve_type in enumerate(curve_types):
            ax = axes[i]
            
            # Find appropriate curve
            curve_name = None
            data = None
            unit = ""
            title = ""
            color = 'blue'
            
            if curve_type.lower() == "porosity":
                possible_names = ['NPHI', 'PHIN', 'NPOR', 'PHI', 'PHIT', 'PHIE']
                title = "Porosity"
                unit = "%"
                color = 'blue'
            elif curve_type.lower() == "gamma":
                possible_names = ['GR', 'GRD', 'CGR', 'SGR', 'GAMMA', 'GRS']
                title = "Gamma Ray"
                unit = "API"
                color = 'green'
            elif curve_type.lower() == "resistivity":
                possible_names = ['RT', 'RES', 'ILD', 'ILM', 'LLD', 'LLS', 'RDEP', 'RMED']
                title = "Resistivity"
                unit = "ohm.m"
                color = 'red'
            elif curve_type.lower() == "density":
                possible_names = ['RHOB', 'RHOZ', 'DENS', 'BD']
                title = "Bulk Density"
                unit = "g/cc"
                color = 'purple'
            
            # Find the curve
            for name in possible_names:
                if name in las.curves:
                    curve_name = name
                    data = las[name]
                    if las.curves[name].unit:
                        unit = las.curves[name].unit
                    break
            
            if data is not None:
                # Clean data
                valid_indices = ~np.isnan(data)
                depth_clean = depth[valid_indices]
                data_clean = data[valid_indices]
                
                if len(data_clean) > 0:
                    if curve_type.lower() == "resistivity" and np.any(data_clean > 0):
                        ax.semilogx(data_clean, depth_clean, color=color, linewidth=2)
                    else:
                        ax.plot(data_clean, depth_clean, color=color, linewidth=2)
                    
                    ax.set_xlabel(f'{title} ({unit})', fontsize=12)
                    ax.set_title(title, fontsize=14, fontweight='bold')
                    ax.grid(True, alpha=0.3)
                    ax.invert_yaxis()
                    
                    curves_plotted.append(f"{title} ({curve_name})")
        
        # Set common y-axis label
        axes[0].set_ylabel('Depth (ft)', fontsize=14)
        
        # Overall title
        plt.suptitle(f'Well Log Analysis - {filename}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if output_prefix:
            output_filename = f"{output_prefix}_{filename.replace('.las', '')}_multi_track_{timestamp}.png"
        else:
            output_filename = f"{filename.replace('.las', '')}_multi_track_{timestamp}.png"
        
        output_path = OUTPUT_DIR / output_filename
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        log_step("Multi-curve plot completed", "create_multi_curve_plot", f"Plotted: {', '.join(curves_plotted)}")
        return str(output_filename)
        
    except Exception as e:
        error_msg = f"Error creating multi-curve plot: {str(e)}"
        log_step("Multi-curve plot failed", "create_multi_curve_plot", error_msg)
        return error_msg

@server.tool("get_processing_steps")
def get_processing_steps(limit: int = 20) -> Dict[str, Any]:
    """Get recent processing steps for progress tracking"""
    try:
        log_file = OUTPUT_DIR / "processing_steps.json"
        
        if not log_file.exists():
            return {"steps": [], "total": 0}
        
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        # Get the most recent steps
        recent_steps = logs[-limit:] if len(logs) > limit else logs
        
        return {
            "steps": recent_steps,
            "total": len(logs),
            "showing": len(recent_steps)
        }
        
    except Exception as e:
        return {"error": f"Failed to get processing steps: {str(e)}"}

@server.tool("clear_processing_steps")
def clear_processing_steps() -> str:
    """Clear processing steps log"""
    try:
        log_file = OUTPUT_DIR / "processing_steps.json"
        
        if log_file.exists():
            log_file.unlink()
        
        return "Processing steps cleared successfully"
        
    except Exception as e:
        return f"Error clearing processing steps: {str(e)}"

@server.tool("list_available_las_files")
def list_available_las_files() -> List[str]:
    """List all available LAS files in data directories"""
    log_step("Listing available files", "list_available_las_files", "Scanning directories")
    
    try:
        las_files = []
        
        # Search in multiple directories
        search_dirs = [DATA_DIR, DATA_DIR / "samples", DATA_DIR / "email-attachments"]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for las_file in search_dir.glob("*.las"):
                    las_files.append(las_file.name)
        
        log_step("File listing completed", "list_available_las_files", f"Found {len(las_files)} files")
        return sorted(list(set(las_files)))  # Remove duplicates and sort
        
    except Exception as e:
        log_step("File listing failed", "list_available_las_files", f"Error: {str(e)}")
        return []

if __name__ == "__main__":
    server.run()