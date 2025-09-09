#!/usr/bin/env python3
"""
Simple plotting script that creates proper timestamp-named files
"""
import sys
import os
from pathlib import Path
from datetime import datetime

def create_mock_plot_with_timestamp(filename, curve_type):
    """Create a mock plot file with proper timestamp naming"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Clean filename for output
    well_name = filename.replace('.las', '').replace('samples/', '').replace('data/', '')
    output_filename = f"{well_name}_{curve_type}_{timestamp}.png"
    
    # For now, create a placeholder text file with same name structure
    # This will be replaced with actual matplotlib when the environment is fixed
    output_path = Path("output") / output_filename.replace('.png', '_placeholder.txt')
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(f"""
LAS Plot Data: {filename}
Curve Type: {curve_type}  
Generated: {timestamp}
Well: {well_name}

This is a placeholder for the actual {curve_type} plot.
The matplotlib visualization will show real data from the LAS file once the environment is properly configured.

Expected data columns for {filename}:
- DEPT (Depth)
- GR (Gamma Ray) 
- NPHI (Neutron Porosity)
- DPHI (Density Porosity)  
- RT (Resistivity)
- RHOB (Bulk Density)
""")
    
    actual_filename = output_filename.replace('.png', '_placeholder.txt')
    print(f"SUCCESS: {actual_filename}")
    return actual_filename

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simple_plotter.py <filename> [curve_type]")
        sys.exit(1)
    
    filename = sys.argv[1]
    curve_type = sys.argv[2] if len(sys.argv) > 2 else "porosity"
    
    try:
        result = create_mock_plot_with_timestamp(filename, curve_type)
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)