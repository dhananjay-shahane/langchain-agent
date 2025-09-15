#!/usr/bin/env python3
"""
MCP Reporting Server
Handles plot generation and report creation
"""

from mcp.server import Server
import matplotlib.pyplot as plt
from pathlib import Path
import time
from typing import Dict, List, Any

server = Server("reporting")

@server.tool("plot_logs")
def plot_logs(well: str, logs: Dict[str, List[float]]):
    """Create well log plots"""
    try:
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        plt.figure(figsize=(6, 8))
        for curve, values in logs.items():
            if values:
                plt.plot(values, label=curve)
        
        plt.legend()
        plt.title(f"Well Log - {well}")
        plt.xlabel("Value")
        plt.ylabel("Depth Points")
        plt.grid(True, alpha=0.3)
        
        timestamp = int(time.time())
        fname = f"{well}_logs_{timestamp}.png"
        filepath = output_dir / fname
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(fname)
    except Exception as e:
        return {"error": f"Failed to create plot: {str(e)}"}

@server.tool("make_report")
def make_report(well: str, summary: str, plots: List[str]):
    """Generate analysis report"""
    try:
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        docname = f"{well}_report_{timestamp}.txt"
        filepath = output_dir / docname
        
        report_content = f"""
WELL LOG ANALYSIS REPORT
========================
Well: {well}
Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY
-------
{summary}

GENERATED PLOTS
--------------
"""
        
        for plot in plots:
            if plot:
                report_content += f"- {plot}\n"
        
        report_content += f"""

ANALYSIS DETAILS
---------------
This report contains comprehensive analysis of well log data.
All plots and analysis results are available in the output directory.

Report generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open(filepath, 'w') as f:
            f.write(report_content.strip())
        
        return str(docname)
    except Exception as e:
        return {"error": f"Failed to create report: {str(e)}"}

@server.tool("create_summary_chart")
def create_summary_chart(well: str, data_summary: Dict[str, Any]):
    """Create summary visualization chart"""
    try:
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # Zone distribution
        zones = data_summary.get("zones", ["Zone 1", "Zone 2", "Zone 3", "Zone 4"])
        values = data_summary.get("zone_values", [0.18, 0.15, 0.12, 0.20])
        
        ax1.bar(zones, values, color=['skyblue', 'lightgreen', 'orange', 'lightcoral'])
        ax1.set_title('Property Distribution by Zone')
        ax1.set_ylabel('Average Value')
        
        # Property pie chart
        properties = data_summary.get("properties", ["Porosity", "Permeability", "Water Sat", "Net Pay"])
        prop_values = data_summary.get("property_values", [25, 30, 20, 25])
        
        ax2.pie(prop_values, labels=properties, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Property Distribution')
        
        # Quality scatter
        quality_data = data_summary.get("quality", [0.7, 0.8, 0.6, 0.9])
        depths = list(range(len(quality_data)))
        
        ax3.scatter(quality_data, depths, alpha=0.7, color='green', s=50)
        ax3.set_xlabel('Quality Index')
        ax3.set_ylabel('Zone')
        ax3.set_title('Quality vs Zone')
        
        # Completion potential
        intervals = data_summary.get("intervals", ["Int 1", "Int 2", "Int 3", "Int 4"])
        potential = data_summary.get("potential", [8.5, 7.2, 9.1, 6.8])
        
        ax4.barh(intervals, potential, color='orange')
        ax4.set_xlabel('Completion Potential (1-10)')
        ax4.set_title('Completion Potential')
        
        plt.tight_layout()
        
        timestamp = int(time.time())
        fname = f"{well}_summary_{timestamp}.png"
        filepath = output_dir / fname
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(fname)
    except Exception as e:
        return {"error": f"Failed to create summary chart: {str(e)}"}

if __name__ == "__main__":
    server.run()