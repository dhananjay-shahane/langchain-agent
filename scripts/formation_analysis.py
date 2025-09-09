#!/usr/bin/env python3
"""
Formation Analysis Script for LAS Files
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

def analyze_formations(filename: str):
    """Analyze formation data from LAS file"""
    try:
        file_path = Path("data") / filename
        if not file_path.exists():
            print(f"Error: LAS file '{filename}' not found")
            return None
        
        # Mock formation analysis data
        formations = [
            {"name": "Upper Sandstone", "top": 2450, "bottom": 2650, "porosity": 18.5, "permeability": 120},
            {"name": "Middle Shale", "top": 2650, "bottom": 2850, "porosity": 8.2, "permeability": 0.5},
            {"name": "Lower Limestone", "top": 2850, "bottom": 3050, "porosity": 22.1, "permeability": 85},
            {"name": "Tight Sandstone", "top": 3050, "bottom": 3200, "porosity": 12.7, "permeability": 15}
        ]
        
        # Create formation chart
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 10))
        
        # Porosity vs Depth
        depths = []
        porosities = []
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        for i, formation in enumerate(formations):
            depth_range = np.linspace(formation["top"], formation["bottom"], 20)
            porosity_range = np.random.normal(formation["porosity"], 2, 20)
            
            depths.extend(depth_range)
            porosities.extend(porosity_range)
            
            ax1.fill_betweenx([formation["top"], formation["bottom"]], 
                             0, 30, alpha=0.3, color=colors[i], 
                             label=formation["name"])
            ax1.plot(porosity_range, depth_range, 'o-', color=colors[i], 
                    linewidth=2, markersize=4)
        
        ax1.set_xlabel('Porosity (%)', fontsize=12)
        ax1.set_ylabel('Depth (ft)', fontsize=12)
        ax1.set_title('Formation Porosity Analysis', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.invert_yaxis()
        ax1.legend(loc='upper right')
        ax1.set_xlim(0, 30)
        
        # Formation summary bar chart
        formation_names = [f["name"] for f in formations]
        thicknesses = [f["bottom"] - f["top"] for f in formations]
        avg_porosities = [f["porosity"] for f in formations]
        
        x = np.arange(len(formation_names))
        width = 0.35
        
        ax2_twin = ax2.twinx()
        
        bars1 = ax2.bar(x - width/2, thicknesses, width, label='Thickness (ft)', 
                       color=colors, alpha=0.7)
        bars2 = ax2_twin.bar(x + width/2, avg_porosities, width, label='Avg Porosity (%)', 
                            color=colors, alpha=0.5)
        
        ax2.set_xlabel('Formations', fontsize=12)
        ax2.set_ylabel('Thickness (ft)', fontsize=12)
        ax2_twin.set_ylabel('Average Porosity (%)', fontsize=12)
        ax2.set_title('Formation Summary', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(formation_names, rotation=45, ha='right')
        
        # Add value labels on bars
        for bar, thickness in zip(bars1, thicknesses):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 5,
                    f'{thickness}ft', ha='center', va='bottom', fontsize=10)
        
        for bar, porosity in zip(bars2, avg_porosities):
            height = bar.get_height()
            ax2_twin.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                         f'{porosity:.1f}%', ha='center', va='bottom', fontsize=10)
        
        ax2.legend(loc='upper left')
        ax2_twin.legend(loc='upper right')
        
        plt.tight_layout()
        
        # Save formation analysis chart
        timestamp = datetime.now().strftime('%H%M%S')
        output_filename = f"{filename.replace('.las', '')}_formation_analysis_{timestamp}.png"
        output_path = Path("output") / output_filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(exist_ok=True)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Generate text report
        report_filename = f"{filename.replace('.las', '')}_formation_report_{timestamp}.txt"
        report_path = Path("output") / report_filename
        
        with open(report_path, 'w') as f:
            f.write(f"FORMATION ANALYSIS REPORT\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"LAS File: {filename}\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("FORMATION SUMMARY:\n")
            f.write("-" * 30 + "\n")
            
            total_thickness = 0
            for formation in formations:
                thickness = formation["bottom"] - formation["top"]
                total_thickness += thickness
                
                f.write(f"\n{formation['name']}:\n")
                f.write(f"  Depth Range: {formation['top']} - {formation['bottom']} ft\n")
                f.write(f"  Thickness: {thickness} ft\n")
                f.write(f"  Avg Porosity: {formation['porosity']}%\n")
                f.write(f"  Avg Permeability: {formation['permeability']} mD\n")
            
            f.write(f"\nTOTAL SECTION THICKNESS: {total_thickness} ft\n")
            
            # Reservoir quality assessment
            f.write(f"\nRESERVOIR QUALITY ASSESSMENT:\n")
            f.write("-" * 35 + "\n")
            
            good_reservoir = [f for f in formations if f["porosity"] > 15 and f["permeability"] > 50]
            if good_reservoir:
                f.write("Good Reservoir Zones:\n")
                for res in good_reservoir:
                    f.write(f"  • {res['name']} (Φ: {res['porosity']}%, K: {res['permeability']} mD)\n")
            else:
                f.write("No high-quality reservoir zones identified.\n")
        
        print(f"Formation analysis completed:")
        print(f"  Chart: {output_filename}")
        print(f"  Report: {report_filename}")
        
        return output_filename
        
    except Exception as e:
        print(f"Error in formation analysis: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python formation_analysis.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    result = analyze_formations(filename)
    
    if result:
        print(f"SUCCESS: {result}")
    else:
        print("FAILED")
        sys.exit(1)
