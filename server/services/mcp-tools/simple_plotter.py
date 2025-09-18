#!/usr/bin/env python3
"""
Simple Log Plotter - No NumPy/matplotlib dependencies
Pure Python implementation for basic LAS file plotting
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def read_las_simple(las_path: str) -> Dict[str, Any]:
    """Simple LAS file reader without lasio dependency."""
    try:
        with open(las_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        in_curve_section = False
        in_data_section = False
        headers = []
        data = []
        
        # Parse file sections
        for line in lines:
            line = line.strip()
            
            # Check for section headers
            if line.startswith('~CURVE'):
                in_curve_section = True
                in_data_section = False
                continue
            elif line.startswith('~ASCII'):
                in_curve_section = False
                in_data_section = True
                continue
            elif line.startswith('~'):
                in_curve_section = False
                in_data_section = False
                continue
            
            # Parse curve headers
            if in_curve_section and not line.startswith('#') and '.' in line:
                parts = line.split('.')
                if len(parts) >= 2:
                    curve_name = parts[0].strip()
                    if curve_name and curve_name not in headers:
                        headers.append(curve_name)
            
            # Parse data
            elif in_data_section and line and not line.startswith('#'):
                values = line.split()
                if len(values) >= len(headers) and len(headers) > 0:
                    row = {}
                    for i, header in enumerate(headers):
                        try:
                            value = float(values[i])
                            # Check for null values (-999.25 is common null value)
                            if abs(value + 999.25) < 0.01:
                                value = None
                            row[header] = value
                        except (ValueError, IndexError):
                            row[header] = None
                    data.append(row)
        
        return {
            'headers': headers,
            'data': data,
            'success': True
        }
        
    except Exception as e:
        return {
            'error': f"Error reading LAS file: {str(e)}",
            'success': False
        }


def create_simple_plot(width: int, height: int, title: str) -> Tuple[Image.Image, ImageDraw.Draw]:
    """Create a basic plot image."""
    if not PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is required but not available")
    
    # Create white background
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except:
        font = ImageFont.load_default()
        title_font = font
    
    # Draw title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((width//2 - title_width//2, 10), title, fill='black', font=title_font)
    
    return image, draw


def create_simple_gamma_plot(filename: str) -> Dict[str, Any]:
    """Create a simple gamma ray plot using PIL."""
    try:
        if not PIL_AVAILABLE:
            return {
                'error': "PIL (Pillow) library not available for plotting",
                'success': False
            }
        
        # Find LAS file
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
        
        # Read LAS data
        las_data = read_las_simple(str(las_path))
        if not las_data.get('success'):
            return las_data
        
        headers = las_data['headers']
        data = las_data['data']
        
        # Find gamma ray column
        gr_column = None
        for col in ['GR', 'GAMMA', 'GAMMA_RAY', 'GRC']:
            if col in headers:
                gr_column = col
                break
        
        if not gr_column:
            return {
                'error': f"No gamma ray curve found in {filename}",
                'success': False
            }
        
        # Extract depth and gamma data
        depths = []
        gammas = []
        
        for row in data:
            if row.get('DEPT') is not None and row.get(gr_column) is not None:
                depths.append(row['DEPT'])
                gammas.append(row[gr_column])
        
        if not depths:
            return {
                'error': f"No valid data found in {filename}",
                'success': False
            }
        
        # Create plot
        width, height = 800, 1000
        image, draw = create_simple_plot(width, height, f"Gamma Ray Log - {filename}")
        
        # Plot margins
        left_margin = 100
        right_margin = 50
        top_margin = 60
        bottom_margin = 80
        
        plot_width = width - left_margin - right_margin
        plot_height = height - top_margin - bottom_margin
        
        # Data ranges
        depth_min, depth_max = min(depths), max(depths)
        gamma_min, gamma_max = min(gammas), max(gammas)
        
        if gamma_max == gamma_min:
            gamma_max = gamma_min + 1
        
        # Draw plot area
        draw.rectangle([left_margin, top_margin, width-right_margin, height-bottom_margin], 
                      outline='black', width=2)
        
        # Draw grid lines
        for i in range(5):
            y = top_margin + (i * plot_height // 4)
            draw.line([left_margin, y, width-right_margin, y], fill='lightgray', width=1)
        
        for i in range(5):
            x = left_margin + (i * plot_width // 4)
            draw.line([x, top_margin, x, height-bottom_margin], fill='lightgray', width=1)
        
        # Plot data
        prev_x, prev_y = None, None
        for depth, gamma in zip(depths, gammas):
            # Convert to plot coordinates
            y = top_margin + int((depth - depth_min) / (depth_max - depth_min) * plot_height)
            x = left_margin + int((gamma - gamma_min) / (gamma_max - gamma_min) * plot_width)
            
            # Draw line segment
            if prev_x is not None and prev_y is not None:
                draw.line([prev_x, prev_y, x, y], fill='green', width=2)
            
            prev_x, prev_y = x, y
        
        # Add axis labels
        draw.text((width//2 - 30, height - 30), "Gamma Ray (API)", fill='black')
        
        # Rotate depth label (simplified vertical text)
        draw.text((20, height//2), "D", fill='black')
        draw.text((20, height//2 + 15), "e", fill='black')
        draw.text((20, height//2 + 30), "p", fill='black')
        draw.text((20, height//2 + 45), "t", fill='black')
        draw.text((20, height//2 + 60), "h", fill='black')
        
        # Add scale values
        draw.text((left_margin - 20, top_margin - 5), f"{depth_min:.0f}", fill='black')
        draw.text((left_margin - 20, height - bottom_margin - 5), f"{depth_max:.0f}", fill='black')
        draw.text((left_margin - 10, height - bottom_margin + 20), f"{gamma_min:.0f}", fill='black')
        draw.text((width - right_margin - 30, height - bottom_margin + 20), f"{gamma_max:.0f}", fill='black')
        
        # Save image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_gamma_simple_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        output_path.parent.mkdir(exist_ok=True)
        image.save(output_path, 'PNG')
        
        return {
            'success': True,
            'output_file': output_filename,
            'curve_used': gr_column,
            'data_points': len(depths),
            'depth_range': f"{depth_min:.0f}-{depth_max:.0f} ft",
            'gamma_range': f"{gamma_min:.1f}-{gamma_max:.1f} API"
        }
        
    except Exception as e:
        return {
            'error': f"Error creating simple gamma plot: {str(e)}",
            'success': False
        }


def create_simple_porosity_plot(filename: str) -> Dict[str, Any]:
    """Create a simple porosity plot using PIL."""
    try:
        if not PIL_AVAILABLE:
            return {
                'error': "PIL (Pillow) library not available for plotting",
                'success': False
            }
        
        # Find LAS file and read data
        data_dir = Path("data")
        las_path = None
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {'error': f"LAS file '{filename}' not found", 'success': False}
        
        las_data = read_las_simple(str(las_path))
        if not las_data.get('success'):
            return las_data
        
        headers = las_data['headers']
        data = las_data['data']
        
        # Find porosity columns
        nphi_col = next((col for col in ['NPHI', 'NEUTRON', 'PHIN'] if col in headers), None)
        dphi_col = next((col for col in ['DPHI', 'DENSITY_POR', 'PHID'] if col in headers), None)
        
        if not nphi_col and not dphi_col:
            return {'error': f"No porosity curves found in {filename}", 'success': False}
        
        # Extract data
        depths, nphi_values, dphi_values = [], [], []
        for row in data:
            if row.get('DEPT') is not None:
                depths.append(row['DEPT'])
                nphi_values.append(row.get(nphi_col) if nphi_col else None)
                dphi_values.append(row.get(dphi_col) if dphi_col else None)
        
        if not depths:
            return {'error': f"No valid data found in {filename}", 'success': False}
        
        # Create plot
        width, height = 900, 1000
        image, draw = create_simple_plot(width, height, f"Porosity Log - {filename}")
        
        left_margin, right_margin = 100, 50
        top_margin, bottom_margin = 60, 80
        plot_width = width - left_margin - right_margin
        plot_height = height - top_margin - bottom_margin
        
        depth_min, depth_max = min(depths), max(depths)
        
        # Draw plot area and grid
        draw.rectangle([left_margin, top_margin, width-right_margin, height-bottom_margin], 
                      outline='black', width=2)
        for i in range(5):
            y = top_margin + (i * plot_height // 4)
            draw.line([left_margin, y, width-right_margin, y], fill='lightgray', width=1)
        
        # Plot porosity data (convert to percentage)
        if nphi_col and any(v is not None for v in nphi_values):
            clean_nphi = [v*100 if v is not None else 0 for v in nphi_values]
            prev_x, prev_y = None, None
            for depth, nphi in zip(depths, clean_nphi):
                y = top_margin + int((depth - depth_min) / (depth_max - depth_min) * plot_height)
                x = left_margin + int(min(nphi, 40) / 40 * plot_width)
                if prev_x is not None:
                    draw.line([prev_x, prev_y, x, y], fill='blue', width=2)
                prev_x, prev_y = x, y
        
        # Add labels
        draw.text((width//2 - 30, height - 30), "Porosity (%)", fill='black')
        draw.text((20, height//2), "Depth", fill='black')  # Simplified
        
        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_porosity_simple_{timestamp}.png"
        output_path = Path("output") / output_filename
        output_path.parent.mkdir(exist_ok=True)
        image.save(output_path, 'PNG')
        
        return {
            'success': True,
            'output_file': output_filename,
            'curves_used': [col for col in [nphi_col, dphi_col] if col],
            'data_points': len(depths)
        }
        
    except Exception as e:
        return {'error': f"Error creating porosity plot: {str(e)}", 'success': False}


def create_simple_resistivity_plot(filename: str) -> Dict[str, Any]:
    """Create a simple resistivity plot using PIL."""
    try:
        if not PIL_AVAILABLE:
            return {'error': "PIL (Pillow) library not available", 'success': False}
        
        # Find and read LAS file
        data_dir = Path("data")
        las_path = None
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {'error': f"LAS file '{filename}' not found", 'success': False}
        
        las_data = read_las_simple(str(las_path))
        if not las_data.get('success'):
            return las_data
        
        headers = las_data['headers']
        data = las_data['data']
        
        # Find resistivity column
        rt_col = next((col for col in ['RT', 'RES', 'RESISTIVITY', 'ILD'] if col in headers), None)
        if not rt_col:
            return {'error': f"No resistivity curve found in {filename}", 'success': False}
        
        # Extract data
        depths, resistivity_values = [], []
        for row in data:
            if row.get('DEPT') is not None and row.get(rt_col) is not None:
                depths.append(row['DEPT'])
                resistivity_values.append(row[rt_col])
        
        if not depths:
            return {'error': f"No valid data found in {filename}", 'success': False}
        
        # Create plot
        width, height = 800, 1000
        image, draw = create_simple_plot(width, height, f"Resistivity Log - {filename}")
        
        left_margin, right_margin = 100, 50
        top_margin, bottom_margin = 60, 80
        plot_width = width - left_margin - right_margin
        plot_height = height - top_margin - bottom_margin
        
        depth_min, depth_max = min(depths), max(depths)
        res_min, res_max = min(resistivity_values), max(resistivity_values)
        
        # Use log scale approximation for resistivity
        import math
        log_res_values = [math.log10(max(r, 0.1)) for r in resistivity_values]
        log_min, log_max = min(log_res_values), max(log_res_values)
        if log_max == log_min:
            log_max = log_min + 1
        
        # Draw plot area
        draw.rectangle([left_margin, top_margin, width-right_margin, height-bottom_margin], 
                      outline='black', width=2)
        
        # Plot resistivity with log scaling
        prev_x, prev_y = None, None
        for depth, log_res in zip(depths, log_res_values):
            y = top_margin + int((depth - depth_min) / (depth_max - depth_min) * plot_height)
            x = left_margin + int((log_res - log_min) / (log_max - log_min) * plot_width)
            if prev_x is not None:
                draw.line([prev_x, prev_y, x, y], fill='red', width=2)
            prev_x, prev_y = x, y
        
        # Labels
        draw.text((width//2 - 40, height - 30), "Resistivity (Ω.m)", fill='black')
        
        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_resistivity_simple_{timestamp}.png"
        output_path = Path("output") / output_filename
        output_path.parent.mkdir(exist_ok=True)
        image.save(output_path, 'PNG')
        
        return {
            'success': True,
            'output_file': output_filename,
            'curve_used': rt_col,
            'data_points': len(depths)
        }
        
    except Exception as e:
        return {'error': f"Error creating resistivity plot: {str(e)}", 'success': False}


def create_simple_density_plot(filename: str) -> Dict[str, Any]:
    """Create a simple density plot using PIL."""
    try:
        if not PIL_AVAILABLE:
            return {'error': "PIL (Pillow) library not available", 'success': False}
        
        # Find and read LAS file
        data_dir = Path("data")
        las_path = None
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {'error': f"LAS file '{filename}' not found", 'success': False}
        
        las_data = read_las_simple(str(las_path))
        if not las_data.get('success'):
            return las_data
        
        headers = las_data['headers']
        data = las_data['data']
        
        # Find density and caliper columns
        rhob_col = next((col for col in ['RHOB', 'DENSITY', 'DEN'] if col in headers), None)
        cali_col = next((col for col in ['CALI', 'CALIPER', 'CAL'] if col in headers), None)
        
        if not rhob_col and not cali_col:
            return {'error': f"No density or caliper curves found in {filename}", 'success': False}
        
        # Extract data
        depths = []
        rhob_values = []
        cali_values = []
        
        for row in data:
            if row.get('DEPT') is not None:
                depths.append(row['DEPT'])
                rhob_values.append(row.get(rhob_col) if rhob_col else None)
                cali_values.append(row.get(cali_col) if cali_col else None)
        
        if not depths:
            return {'error': f"No valid data found in {filename}", 'success': False}
        
        # Create plot
        width, height = 1000, 1000
        image, draw = create_simple_plot(width, height, f"Density & Caliper Log - {filename}")
        
        # Split into two tracks
        left_margin = 80
        middle = width // 2
        right_margin = 50
        top_margin, bottom_margin = 60, 80
        plot_height = height - top_margin - bottom_margin
        track_width = (middle - left_margin - 20)
        
        depth_min, depth_max = min(depths), max(depths)
        
        # Draw plot areas
        draw.rectangle([left_margin, top_margin, middle-10, height-bottom_margin], 
                      outline='black', width=2)
        draw.rectangle([middle+10, top_margin, width-right_margin, height-bottom_margin], 
                      outline='black', width=2)
        
        # Plot density if available
        if rhob_col and any(v is not None for v in rhob_values):
            clean_rhob = [v for v in rhob_values if v is not None]
            if clean_rhob:
                rhob_min, rhob_max = min(clean_rhob), max(clean_rhob)
                prev_x, prev_y = None, None
                for depth, rhob in zip(depths, rhob_values):
                    if rhob is not None:
                        y = top_margin + int((depth - depth_min) / (depth_max - depth_min) * plot_height)
                        x = left_margin + int((rhob - rhob_min) / max(rhob_max - rhob_min, 0.1) * track_width)
                        if prev_x is not None:
                            draw.line([prev_x, prev_y, x, y], fill='purple', width=2)
                        prev_x, prev_y = x, y
        
        # Plot caliper if available
        if cali_col and any(v is not None for v in cali_values):
            clean_cali = [v for v in cali_values if v is not None]
            if clean_cali:
                cali_min, cali_max = min(clean_cali), max(clean_cali)
                prev_x, prev_y = None, None
                for depth, cali in zip(depths, cali_values):
                    if cali is not None:
                        y = top_margin + int((depth - depth_min) / (depth_max - depth_min) * plot_height)
                        x = middle + 10 + int((cali - cali_min) / max(cali_max - cali_min, 0.1) * track_width)
                        if prev_x is not None:
                            draw.line([prev_x, prev_y, x, y], fill='brown', width=2)
                        prev_x, prev_y = x, y
        
        # Labels
        if rhob_col:
            draw.text((left_margin + 20, height - 30), "Density (g/cm³)", fill='black')
        if cali_col:
            draw.text((middle + 30, height - 30), "Caliper (in)", fill='black')
        
        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_density_simple_{timestamp}.png"
        output_path = Path("output") / output_filename
        output_path.parent.mkdir(exist_ok=True)
        image.save(output_path, 'PNG')
        
        return {
            'success': True,
            'output_file': output_filename,
            'curves_used': [col for col in [rhob_col, cali_col] if col],
            'data_points': len(depths)
        }
        
    except Exception as e:
        return {'error': f"Error creating density plot: {str(e)}", 'success': False}


def create_simple_composite_plot(filename: str) -> Dict[str, Any]:
    """Create a simple composite log plot using PIL."""
    try:
        if not PIL_AVAILABLE:
            return {'error': "PIL (Pillow) library not available", 'success': False}
        
        # Read LAS file
        data_dir = Path("data")
        las_path = None
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {'error': f"LAS file '{filename}' not found", 'success': False}
        
        las_data = read_las_simple(str(las_path))
        if not las_data.get('success'):
            return las_data
        
        headers = las_data['headers']
        data = las_data['data']
        
        # Find available curves for tracks
        gr_col = next((col for col in ['GR', 'GAMMA'] if col in headers), None)
        rt_col = next((col for col in ['RT', 'RES'] if col in headers), None)
        nphi_col = next((col for col in ['NPHI', 'NEUTRON'] if col in headers), None)
        rhob_col = next((col for col in ['RHOB', 'DENSITY'] if col in headers), None)
        
        available_curves = [col for col in [gr_col, rt_col, nphi_col, rhob_col] if col]
        if not available_curves:
            return {'error': f"No suitable curves found for composite plot", 'success': False}
        
        # Create wide plot for multiple tracks
        num_tracks = len(available_curves)
        width = 200 * num_tracks + 100
        height = 1200
        image, draw = create_simple_plot(width, height, f"Composite Log - {filename}")
        
        left_margin = 80
        top_margin, bottom_margin = 80, 100
        track_width = (width - left_margin - 50) // num_tracks
        plot_height = height - top_margin - bottom_margin
        
        # Extract depths
        depths = [row['DEPT'] for row in data if row.get('DEPT') is not None]
        if not depths:
            return {'error': f"No depth data found", 'success': False}
        
        depth_min, depth_max = min(depths), max(depths)
        
        # Plot each track
        for i, curve in enumerate(available_curves):
            track_left = left_margin + i * track_width
            track_right = track_left + track_width - 10
            
            # Draw track boundary
            draw.rectangle([track_left, top_margin, track_right, height-bottom_margin], 
                          outline='black', width=1)
            
            # Extract curve data
            curve_data = []
            for row in data:
                if row.get('DEPT') is not None and row.get(curve) is not None:
                    curve_data.append((row['DEPT'], row[curve]))
            
            if curve_data:
                curve_values = [v[1] for v in curve_data]
                curve_min, curve_max = min(curve_values), max(curve_values)
                if curve_max == curve_min:
                    curve_max = curve_min + 1
                
                # Plot curve
                prev_x, prev_y = None, None
                color = ['green', 'red', 'blue', 'purple'][i % 4]
                
                for depth, value in curve_data:
                    y = top_margin + int((depth - depth_min) / (depth_max - depth_min) * plot_height)
                    x = track_left + int((value - curve_min) / (curve_max - curve_min) * (track_width - 20)) + 10
                    
                    if prev_x is not None:
                        draw.line([prev_x, prev_y, x, y], fill=color, width=2)
                    prev_x, prev_y = x, y
                
                # Track label
                draw.text((track_left + 10, height - 60), curve, fill='black')
        
        # Depth axis
        draw.text((20, height//2), "Depth", fill='black')
        
        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        well_name = filename.replace('.las', '').replace('/', '_')
        output_filename = f"{well_name}_composite_simple_{timestamp}.png"
        output_path = Path("output") / output_filename
        output_path.parent.mkdir(exist_ok=True)
        image.save(output_path, 'PNG')
        
        return {
            'success': True,
            'output_file': output_filename,
            'tracks': num_tracks,
            'curves_plotted': available_curves,
            'data_points': len(depths)
        }
        
    except Exception as e:
        return {'error': f"Error creating composite plot: {str(e)}", 'success': False}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simple_plotter.py <plot_type> <filename>")
        print("Plot types: gamma, porosity, resistivity, density, composite")
        sys.exit(1)
    
    plot_type = sys.argv[1]
    filename = sys.argv[2]
    
    if plot_type == "gamma":
        result = create_simple_gamma_plot(filename)
    elif plot_type == "porosity":
        result = create_simple_porosity_plot(filename)
    elif plot_type == "resistivity":
        result = create_simple_resistivity_plot(filename)
    elif plot_type == "density":
        result = create_simple_density_plot(filename)
    elif plot_type == "composite":
        result = create_simple_composite_plot(filename)
    else:
        result = {
            'error': f"Plot type '{plot_type}' not implemented in simple plotter",
            'success': False
        }
    
    print(json.dumps(result))