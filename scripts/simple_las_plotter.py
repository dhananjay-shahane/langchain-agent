#!/usr/bin/env python3
"""
Simple LAS File Plotting Script without numpy dependency issues
"""
import sys
import re
from pathlib import Path
from datetime import datetime


def read_las_file(filepath):
    """Read LAS file and extract data"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Parse LAS file sections
        well_info = {}
        curves = {}
        data = []

        lines = content.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Detect sections
            if line.startswith('~'):
                current_section = line[1:].split()[0].upper()
                continue

            # Parse well information
            if current_section == 'WELL':
                if '.' in line and ':' in line:
                    parts = line.split('.')
                    if len(parts) >= 2:
                        key = parts[0].strip()
                        rest = parts[1].split(':')
                        if len(rest) >= 2:
                            value = rest[0].strip()
                            desc = rest[1].strip()
                            well_info[key] = {'value': value, 'desc': desc}

            # Parse curve information
            elif current_section == 'CURVE':
                if '.' in line and ':' in line:
                    parts = line.split('.')
                    if len(parts) >= 2:
                        curve_name = parts[0].strip()
                        rest = parts[1].split(':')
                        if len(rest) >= 2:
                            unit = rest[0].strip()
                            desc = rest[1].strip()
                            curves[curve_name] = {'unit': unit, 'desc': desc}

            # Parse ASCII data
            elif current_section == 'ASCII':
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        row = [
                            float(x) if x != '-999.25' else None for x in parts
                        ]
                        data.append(row)
                    except ValueError:
                        continue

        return well_info, curves, data

    except Exception as e:
        print(f"Error reading LAS file: {e}")
        return None, None, None


def create_simple_plot(filename, curve_type="gamma"):
    """Create a simple matplotlib plot from LAS data"""

    # Import matplotlib here to handle potential issues
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
    except ImportError as e:
        print(f"Error importing matplotlib: {e}")
        return None

    # Find the file
    file_path = Path("data") / "samples" / filename
    if not file_path.exists():
        file_path = Path("data") / filename
        if not file_path.exists():
            print(f"Error: LAS file '{filename}' not found")
            return None

    print(f"Reading file: {file_path}")

    # Read LAS file
    well_info, curves, data = read_las_file(file_path)
    if not data or not curves:
        print("Error: Could not read LAS file data")
        return None

    print(f"Found {len(data)} data points and {len(curves)} curves")
    print(f"Available curves: {list(curves.keys())}")

    # Get curve names
    curve_names = list(curves.keys())
    if not curve_names:
        print("No curves found")
        return None

    # Find depth column (usually first or named DEPT)
    depth_col = 0
    depth_name = "DEPT"
    if "DEPT" in curves:
        depth_col = curve_names.index("DEPT")
        depth_name = "DEPT"

    # Find target curve
    target_col = 1  # default to second column
    target_name = curve_names[1] if len(curve_names) > 1 else curve_names[0]
    title = "Log Data"
    unit = ""

    if curve_type.lower() == "gamma":
        for name in ["GR", "GAMMA", "GRD"]:
            if name in curves:
                target_col = curve_names.index(name)
                target_name = name
                title = "Gamma Ray"
                unit = curves[name].get('unit', 'API')
                break
    elif curve_type.lower() == "porosity":
        for name in ["NPHI", "PHIN", "DPHI", "PHI"]:
            if name in curves:
                target_col = curve_names.index(name)
                target_name = name
                title = "Porosity"
                unit = curves[name].get('unit', 'v/v')
                break
    elif curve_type.lower() == "resistivity":
        for name in ["RT", "RES", "ILD", "LLD"]:
            if name in curves:
                target_col = curve_names.index(name)
                target_name = name
                title = "Resistivity"
                unit = curves[name].get('unit', 'ohm.m')
                break

    print(f"Using depth column: {depth_name} (col {depth_col})")
    print(f"Using data column: {target_name} (col {target_col})")

    # Extract data
    depths = []
    values = []

    for row in data:
        if len(row) > max(depth_col, target_col):
            depth_val = row[depth_col]
            data_val = row[target_col]
            if depth_val is not None and data_val is not None:
                depths.append(depth_val)
                values.append(data_val)

    if not depths or not values:
        print("No valid data points found")
        return None

    print(f"Plotting {len(depths)} data points")
    print(f"Depth range: {min(depths)} to {max(depths)} ft")
    print(f"Data range: {min(values)} to {max(values)} {unit}")

    # Create plot
    fig, ax = plt.subplots(figsize=(8, 12))

    # Plot data
    if curve_type.lower() == "resistivity":
        # Use log scale for resistivity
        ax.semilogx(values, depths, 'r-', linewidth=2)
    else:
        ax.plot(values, depths, 'b-', linewidth=2)

    # Format plot
    ax.set_ylabel('Depth (ft)', fontsize=14)
    ax.set_xlabel(f'{title} ({unit})', fontsize=14)

    # Get well name for title
    well_name = filename.replace('.las', '')
    if 'WELL' in well_info:
        well_name = well_info['WELL'].get('value', well_name)

    ax.set_title(f'{title} Log\n{well_name}', fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.invert_yaxis()  # Depth increases downward

    # Add data info
    info_text = f'Points: {len(depths)}\nDepth: {min(depths):.0f}-{max(depths):.0f} ft'
    ax.text(0.02,
            0.98,
            info_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()

    # Save with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    well_name_clean = re.sub(r'[^\w\-_]', '_', well_name)
    output_filename = f"{well_name_clean}_{curve_type}_{timestamp}.png"
    output_path = Path("output") / output_filename

    # Ensure output directory exists
    output_path.parent.mkdir(exist_ok=True)

    try:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"SUCCESS: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Error saving plot: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simple_las_plotter.py <filename> [curve_type]")
        sys.exit(1)

    filename = sys.argv[1]
    curve_type = sys.argv[2] if len(sys.argv) > 2 else "gamma"

    result = create_simple_plot(filename, curve_type)
    if result:
        print(f"SUCCESS: {result}")
    else:
        print("FAILED")
        sys.exit(1)
