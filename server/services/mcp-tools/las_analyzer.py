#!/usr/bin/env python3
"""
LAS File Analyzer MCP Tool
Real LAS file analysis functionality without mock data
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the packages to path
sys.path.extend([
    '/nix/store/zz7i75jb78idaz0rb1y1i4rzdyxq28vf-sitecustomize/lib/python/site-packages',
    '/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages'
])

import lasio
import numpy as np
from fastmcp import FastMCP


def analyze_las_file(filename: str) -> Dict[str, Any]:
    """Analyze a LAS file and extract real information."""
    try:
        # Find the file in data directory or subdirectories
        data_dir = Path("data")
        las_path = None
        
        # Search for the file
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path or not las_path.exists():
            return {
                'error': f"LAS file '{filename}' not found in data directory",
                'success': False
            }
        
        # Read the LAS file using lasio
        las = lasio.read(las_path)
        
        # Extract well information
        well_info = {}
        for item in las.well:
            if item.value is not None:
                well_info[item.mnemonic] = {
                    'value': str(item.value),
                    'unit': item.unit,
                    'description': item.descr
                }
        
        # Get curve information
        curves = []
        for curve in las.curves:
            curves.append({
                'mnemonic': curve.mnemonic,
                'unit': curve.unit,
                'description': curve.descr,
                'api_code': getattr(curve, 'API_code', None)
            })
        
        # Get data statistics
        df = las.df()
        data_stats = {}
        for col in df.columns:
            if col != 'DEPT':  # Skip depth column for stats
                data_stats[col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'count': int(df[col].count()),
                    'null_count': int(df[col].isnull().sum())
                }
        
        # Calculate depth range
        depth_stats = {
            'start_depth': float(df.index.min()),
            'end_depth': float(df.index.max()),
            'total_interval': float(df.index.max() - df.index.min()),
            'sample_count': len(df)
        }
        
        result = {
            'success': True,
            'filename': filename,
            'well_info': well_info,
            'curves': curves,
            'curve_count': len(curves),
            'depth_stats': depth_stats,
            'data_stats': data_stats,
            'data_quality': {
                'total_samples': len(df),
                'complete_samples': len(df.dropna()),
                'missing_data_percentage': (len(df) - len(df.dropna())) / len(df) * 100
            }
        }
        
        return result
        
    except Exception as e:
        return {
            'error': f"Error analyzing LAS file {filename}: {str(e)}",
            'success': False
        }


def list_las_files() -> Dict[str, Any]:
    """List all available LAS files with real information."""
    try:
        data_dir = Path("data")
        if not data_dir.exists():
            return {
                'error': "Data directory not found",
                'success': False
            }
        
        # Find all LAS files recursively
        las_files = []
        for las_path in data_dir.rglob("*.las"):
            try:
                stat = las_path.stat()
                las_files.append({
                    'filename': las_path.name,
                    'path': str(las_path.relative_to(data_dir)),
                    'size_bytes': stat.st_size,
                    'size_kb': round(stat.st_size / 1024, 2),
                    'last_modified': stat.st_mtime
                })
            except Exception as e:
                print(f"Warning: Could not get stats for {las_path}: {e}")
        
        return {
            'success': True,
            'files': sorted(las_files, key=lambda x: x['filename']),
            'total_files': len(las_files),
            'total_size_kb': sum(f['size_kb'] for f in las_files)
        }
        
    except Exception as e:
        return {
            'error': f"Error listing LAS files: {str(e)}",
            'success': False
        }


def validate_las_file(filename: str) -> Dict[str, Any]:
    """Validate LAS file structure and data quality."""
    try:
        data_dir = Path("data")
        las_path = None
        
        # Search for the file
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {
                'error': f"LAS file '{filename}' not found",
                'success': False
            }
        
        # Read and validate
        las = lasio.read(las_path)
        df = las.df()
        
        validation_results = {
            'success': True,
            'filename': filename,
            'has_header': bool(las.header),
            'has_well_info': len(las.well) > 0,
            'has_curves': len(las.curves) > 0,
            'has_data': len(df) > 0,
            'required_curves': {},
            'data_continuity': {},
            'issues': []
        }
        
        # Check for standard curve types
        standard_curves = ['DEPT', 'GR', 'NPHI', 'RHOB', 'RT']
        for curve in standard_curves:
            validation_results['required_curves'][curve] = curve in df.columns
            if curve not in df.columns:
                validation_results['issues'].append(f"Missing standard curve: {curve}")
        
        # Check data continuity
        for col in df.columns:
            null_pct = (df[col].isnull().sum() / len(df)) * 100
            validation_results['data_continuity'][col] = {
                'null_percentage': round(null_pct, 2),
                'has_major_gaps': null_pct > 10
            }
            if null_pct > 20:
                validation_results['issues'].append(f"High null percentage in {col}: {null_pct:.1f}%")
        
        # Overall quality score
        quality_score = 100
        quality_score -= len(validation_results['issues']) * 10
        validation_results['quality_score'] = max(0, quality_score)
        
        return validation_results
        
    except Exception as e:
        return {
            'error': f"Error validating LAS file {filename}: {str(e)}",
            'success': False
        }


if __name__ == "__main__":
    # Command line interface for testing
    if len(sys.argv) < 2:
        print("Usage: python las_analyzer.py <command> [args]")
        print("Commands:")
        print("  analyze <filename>    - Analyze a LAS file")
        print("  list                  - List all LAS files") 
        print("  validate <filename>   - Validate LAS file structure")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "analyze":
        if len(sys.argv) < 3:
            print("Error: filename required for analyze command")
            sys.exit(1)
        result = analyze_las_file(sys.argv[2])
        print(result)
    
    elif command == "list":
        result = list_las_files()
        print(result)
    
    elif command == "validate":
        if len(sys.argv) < 3:
            print("Error: filename required for validate command")
            sys.exit(1)
        result = validate_las_file(sys.argv[2])
        print(result)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)