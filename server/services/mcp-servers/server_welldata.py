#!/usr/bin/env python3
"""
MCP Well Data Server
Handles well data operations for LAS files and well log data
"""

from mcp.server import Server
import lasio
import os
from pathlib import Path

server = Server("well_data")

DATA_DIR = "./data"

@server.tool("list_wells")
def list_wells():
    """List all available well files in the data directory"""
    data_path = Path(DATA_DIR)
    if not data_path.exists():
        return []
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".las")]

@server.tool("get_logs")
def get_logs(well: str, curves: list[str]):
    """Get log curves data for a specific well"""
    try:
        # Sanitize well filename to prevent path traversal
        if not well or '/' in well or '\\' in well or '..' in well:
            return {"error": f"Invalid well filename: {well}"}
        
        well_path = os.path.join(DATA_DIR, well)
        # Ensure the resolved path is still within DATA_DIR
        if not os.path.realpath(well_path).startswith(os.path.realpath(DATA_DIR)):
            return {"error": f"Access denied to file: {well}"}
        
        if not os.path.exists(well_path):
            return {"error": f"Well file {well} not found"}
        
        las = lasio.read(well_path)
        result = {}
        
        for curve in curves:
            if curve in las.curves_dict:
                result[curve] = las[curve].tolist()
            else:
                result[curve] = None
                
        return result
    except Exception as e:
        return {"error": f"Failed to read well data: {str(e)}"}

@server.tool("get_well_info")
def get_well_info(well: str):
    """Get well header information and available curves"""
    try:
        # Sanitize well filename to prevent path traversal
        if not well or '/' in well or '\\' in well or '..' in well:
            return {"error": f"Invalid well filename: {well}"}
        
        well_path = os.path.join(DATA_DIR, well)
        # Ensure the resolved path is still within DATA_DIR
        if not os.path.realpath(well_path).startswith(os.path.realpath(DATA_DIR)):
            return {"error": f"Access denied to file: {well}"}
        
        if not os.path.exists(well_path):
            return {"error": f"Well file {well} not found"}
        
        las = lasio.read(well_path)
        
        return {
            "well_name": las.well.WELL.value if las.well.WELL else well,
            "field": las.well.FLD.value if las.well.FLD else "",
            "location": las.well.LOC.value if las.well.LOC else "",
            "curves": list(las.curves_dict.keys()),
            "depth_range": {
                "start": float(las.well.STRT.value) if las.well.STRT else None,
                "stop": float(las.well.STOP.value) if las.well.STOP else None,
                "step": float(las.well.STEP.value) if las.well.STEP else None
            }
        }
    except Exception as e:
        return {"error": f"Failed to read well info: {str(e)}"}

if __name__ == "__main__":
    server.run()