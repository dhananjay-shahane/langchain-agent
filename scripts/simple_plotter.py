#!/usr/bin/env python3
"""
Updated plotting script that uses pure Python LAS parser
Returns JSON data for frontend plotting instead of generating matplotlib plots
"""
import sys
import os
import json
from pathlib import Path

# Add MCP tools to path
sys.path.append(str(Path(__file__).parent.parent / "server" / "services" / "mcp-tools"))

from las_parser_pure import get_las_data_for_plotting, analyze_las_file


def main():
    """Main function to process LAS files and return data for frontend plotting"""
    if len(sys.argv) < 2:
        print("Usage: python simple_plotter.py <filename> [curve_type]")
        print("Curve types: gamma, porosity, resistivity, all")
        sys.exit(1)
    
    filename = sys.argv[1]
    curve_type = sys.argv[2] if len(sys.argv) > 2 else "all"
    
    try:
        if curve_type.lower() == "gamma":
            # Get data for gamma ray plotting
            result = get_las_data_for_plotting(filename, ['GR', 'GAMMA', 'GAMMA_RAY'])
            if result.get('success'):
                # Create success output with plot data
                output = {
                    'success': True,
                    'plot_type': 'gamma_ray',
                    'filename': filename,
                    'plot_data': result,
                    'message': f"Gamma ray data prepared for plotting from {filename}",
                    'frontend_action': 'Use this data with the chart component to create gamma ray plots'
                }
                print(f"SUCCESS: {json.dumps(output)}")
            else:
                print(f"ERROR: {result.get('error', 'Failed to get gamma ray data')}")
                sys.exit(1)
                
        elif curve_type.lower() == "porosity":
            # Get data for porosity plotting
            result = get_las_data_for_plotting(filename, ['NPHI', 'DPHI', 'NEUTRON', 'DENSITY_POR'])
            if result.get('success'):
                output = {
                    'success': True,
                    'plot_type': 'porosity',
                    'filename': filename,
                    'plot_data': result,
                    'message': f"Porosity data prepared for plotting from {filename}",
                    'frontend_action': 'Use this data with the chart component to create porosity plots'
                }
                print(f"SUCCESS: {json.dumps(output)}")
            else:
                print(f"ERROR: {result.get('error', 'Failed to get porosity data')}")
                sys.exit(1)
                
        elif curve_type.lower() == "resistivity":
            # Get data for resistivity plotting
            result = get_las_data_for_plotting(filename, ['RT', 'RES', 'RESISTIVITY', 'ILD'])
            if result.get('success'):
                output = {
                    'success': True,
                    'plot_type': 'resistivity',
                    'filename': filename,
                    'plot_data': result,
                    'message': f"Resistivity data prepared for plotting from {filename}",
                    'frontend_action': 'Use this data with the chart component to create resistivity plots'
                }
                print(f"SUCCESS: {json.dumps(output)}")
            else:
                print(f"ERROR: {result.get('error', 'Failed to get resistivity data')}")
                sys.exit(1)
                
        elif curve_type.lower() == "all":
            # Get complete analysis and all available data
            analysis_result = analyze_las_file(filename)
            if analysis_result.get('success'):
                # Get plot data for all curves
                plot_result = get_las_data_for_plotting(filename)
                
                output = {
                    'success': True,
                    'plot_type': 'complete_analysis',
                    'filename': filename,
                    'analysis': analysis_result,
                    'plot_data': plot_result,
                    'message': f"Complete LAS analysis and plot data prepared for {filename}",
                    'frontend_action': 'Use this comprehensive data to create multiple plots and analysis views'
                }
                print(f"SUCCESS: {json.dumps(output)}")
            else:
                print(f"ERROR: {analysis_result.get('error', 'Failed to analyze LAS file')}")
                sys.exit(1)
        
        else:
            print(f"ERROR: Unknown curve type '{curve_type}'. Supported types: gamma, porosity, resistivity, all")
            sys.exit(1)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()