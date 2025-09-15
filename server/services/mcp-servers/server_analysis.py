#!/usr/bin/env python3
"""
MCP Analysis Server
Handles petrophysical analysis and zone classification
"""

from mcp.server import Server
from typing import List, Dict, Any

server = Server("analysis")

@server.tool("classify_zones")
def classify_zones(phie: List[float], vsh: List[float], swe: List[float]):
    """Classify reservoir zones based on porosity, shale volume, and water saturation"""
    try:
        flags = []
        for phi, clay, water in zip(phie, vsh, swe):
            if phi >= 0.08 and clay <= 0.5 and water <= 0.7:
                flags.append("PAY")
            elif phi >= 0.08 and clay <= 0.5:
                flags.append("RES")
            elif clay <= 0.5:
                flags.append("ROCK")
            else:
                flags.append("NON-RES")
        return flags
    except Exception as e:
        return {"error": f"Failed to classify zones: {str(e)}"}

@server.tool("compute_averages")
def compute_averages(values: Dict[str, List[float]]):
    """Compute averages for log curves"""
    try:
        result = {}
        for key, val_list in values.items():
            if val_list and len(val_list) > 0:
                # Filter out None values
                clean_values = [v for v in val_list if v is not None]
                if clean_values:
                    result[key] = sum(clean_values) / len(clean_values)
                else:
                    result[key] = None
            else:
                result[key] = None
        return result
    except Exception as e:
        return {"error": f"Failed to compute averages: {str(e)}"}

@server.tool("calculate_net_to_gross")
def calculate_net_to_gross(flags: List[str]):
    """Calculate net-to-gross ratio from zone flags"""
    try:
        if not flags:
            return {"net_to_gross": 0.0, "total_zones": 0, "pay_zones": 0}
        
        total_zones = len(flags)
        pay_zones = sum(1 for flag in flags if flag in ["PAY", "RES"])
        net_to_gross = pay_zones / total_zones if total_zones > 0 else 0.0
        
        return {
            "net_to_gross": net_to_gross,
            "total_zones": total_zones,
            "pay_zones": pay_zones,
            "pay_percentage": net_to_gross * 100
        }
    except Exception as e:
        return {"error": f"Failed to calculate net-to-gross: {str(e)}"}

@server.tool("analyze_formation_quality")
def analyze_formation_quality(porosity: List[float], permeability: List[float] = None):
    """Analyze formation quality based on porosity and permeability"""
    try:
        if not porosity:
            return {"error": "No porosity data provided"}
        
        # Filter out None values
        clean_porosity = [p for p in porosity if p is not None]
        
        if not clean_porosity:
            return {"error": "No valid porosity data"}
        
        avg_porosity = sum(clean_porosity) / len(clean_porosity)
        max_porosity = max(clean_porosity)
        min_porosity = min(clean_porosity)
        
        # Classify formation quality
        if avg_porosity >= 0.15:
            quality = "Excellent"
        elif avg_porosity >= 0.10:
            quality = "Good"
        elif avg_porosity >= 0.06:
            quality = "Fair"
        else:
            quality = "Poor"
        
        result = {
            "quality_rating": quality,
            "average_porosity": avg_porosity,
            "max_porosity": max_porosity,
            "min_porosity": min_porosity,
            "porosity_range": max_porosity - min_porosity
        }
        
        if permeability:
            clean_perm = [p for p in permeability if p is not None]
            if clean_perm:
                result["average_permeability"] = sum(clean_perm) / len(clean_perm)
                result["max_permeability"] = max(clean_perm)
        
        return result
    except Exception as e:
        return {"error": f"Failed to analyze formation quality: {str(e)}"}

if __name__ == "__main__":
    server.run()