#!/usr/bin/env python3
"""
Pure Python LAS File Parser
No external dependencies - works with standard library only
"""
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


class SimpleLASParser:
    """Pure Python LAS file parser without external dependencies"""
    
    def __init__(self):
        self.well_info = {}
        self.curves = []
        self.data = []
        self.header_sections = {}
    
    def parse_las_file(self, filepath: str) -> Dict[str, Any]:
        """Parse a LAS file and return structured data"""
        try:
            filepath = Path(filepath)
            if not filepath.exists():
                return {'error': f'File not found: {filepath}', 'success': False}
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Parse sections
            current_section = None
            data_section_started = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Section headers
                if line.startswith('~'):
                    current_section = line[1:].strip()
                    if current_section.upper().startswith('A'):  # ASCII data section
                        data_section_started = True
                    continue
                
                # Parse based on current section
                if data_section_started:
                    self._parse_data_line(line)
                elif current_section:
                    if current_section.upper().startswith('W'):  # Well information
                        self._parse_well_info(line)
                    elif current_section.upper().startswith('C'):  # Curve information
                        self._parse_curve_info(line)
                    elif current_section.upper().startswith('P'):  # Parameter information
                        self._parse_parameter_info(line)
            
            # Calculate statistics
            stats = self._calculate_statistics()
            
            return {
                'success': True,
                'filename': filepath.name,
                'well_info': self.well_info,
                'curves': self.curves,
                'curve_count': len(self.curves),
                'data_points': len(self.data),
                'statistics': stats,
                'data_preview': self.data[:10] if self.data else [],  # First 10 rows
                'data_quality': self._assess_data_quality()
            }
            
        except Exception as e:
            return {'error': f'Error parsing LAS file: {str(e)}', 'success': False}
    
    def _parse_well_info(self, line: str):
        """Parse well information line"""
        if '.' in line:
            parts = line.split('.', 1)
            if len(parts) >= 2:
                mnemonic = parts[0].strip()
                rest = parts[1].strip()
                
                # Split on colon or space to separate value and description
                if ':' in rest:
                    value_part, desc_part = rest.split(':', 1)
                    value = value_part.strip()
                    description = desc_part.strip()
                else:
                    # Try to split on multiple spaces
                    parts = rest.split()
                    if parts:
                        value = parts[0]
                        description = ' '.join(parts[1:]) if len(parts) > 1 else ''
                    else:
                        value = rest
                        description = ''
                
                self.well_info[mnemonic] = {
                    'value': value,
                    'description': description
                }
    
    def _parse_curve_info(self, line: str):
        """Parse curve information line"""
        if '.' in line:
            parts = line.split('.', 1)
            if len(parts) >= 2:
                mnemonic = parts[0].strip()
                rest = parts[1].strip()
                
                # Parse unit and description
                if ':' in rest:
                    unit_part, desc_part = rest.split(':', 1)
                    unit = unit_part.strip()
                    description = desc_part.strip()
                else:
                    parts = rest.split()
                    if parts:
                        unit = parts[0]
                        description = ' '.join(parts[1:]) if len(parts) > 1 else ''
                    else:
                        unit = ''
                        description = rest
                
                self.curves.append({
                    'mnemonic': mnemonic,
                    'unit': unit,
                    'description': description
                })
    
    def _parse_parameter_info(self, line: str):
        """Parse parameter information line"""
        if '.' in line:
            parts = line.split('.', 1)
            if len(parts) >= 2:
                mnemonic = parts[0].strip()
                rest = parts[1].strip()
                
                if ':' in rest:
                    value_part, desc_part = rest.split(':', 1)
                    value = value_part.strip()
                    description = desc_part.strip()
                else:
                    value = rest
                    description = ''
                
                if 'parameters' not in self.header_sections:
                    self.header_sections['parameters'] = {}
                
                self.header_sections['parameters'][mnemonic] = {
                    'value': value,
                    'description': description
                }
    
    def _parse_data_line(self, line: str):
        """Parse a data line"""
        try:
            # Split on whitespace and convert to numbers where possible
            values = line.split()
            parsed_values = []
            
            for value in values:
                try:
                    # Try to parse as float
                    if value.upper() in ['NULL', '-999.25', '-999']:
                        parsed_values.append(None)
                    else:
                        parsed_values.append(float(value))
                except ValueError:
                    # Keep as string if not a number
                    parsed_values.append(value)
            
            if parsed_values:
                self.data.append(parsed_values)
                
        except Exception:
            # Skip malformed data lines
            pass
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate basic statistics for each curve"""
        if not self.data or not self.curves:
            return {}
        
        stats = {}
        
        for i, curve in enumerate(self.curves):
            if i >= len(self.data[0]):
                continue
                
            mnemonic = curve['mnemonic']
            values = []
            
            # Extract non-null values for this curve
            for row in self.data:
                if i < len(row) and row[i] is not None:
                    try:
                        values.append(float(row[i]))
                    except (ValueError, TypeError):
                        continue
            
            if values:
                stats[mnemonic] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'mean': sum(values) / len(values),
                    'range': max(values) - min(values)
                }
                
                # Calculate standard deviation
                if len(values) > 1:
                    mean = stats[mnemonic]['mean']
                    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                    stats[mnemonic]['std'] = variance ** 0.5
                else:
                    stats[mnemonic]['std'] = 0
            else:
                stats[mnemonic] = {
                    'count': 0,
                    'min': None,
                    'max': None,
                    'mean': None,
                    'range': None,
                    'std': None
                }
        
        return stats
    
    def _assess_data_quality(self) -> Dict[str, Any]:
        """Assess data quality"""
        if not self.data:
            return {'total_rows': 0, 'quality_score': 0}
        
        total_cells = len(self.data) * len(self.curves)
        null_cells = 0
        
        for row in self.data:
            for value in row:
                if value is None:
                    null_cells += 1
        
        quality_score = ((total_cells - null_cells) / total_cells * 100) if total_cells > 0 else 0
        
        return {
            'total_rows': len(self.data),
            'total_curves': len(self.curves),
            'null_cells': null_cells,
            'total_cells': total_cells,
            'completeness_percent': round(quality_score, 2),
            'quality_rating': 'excellent' if quality_score > 90 else 'good' if quality_score > 75 else 'fair' if quality_score > 50 else 'poor'
        }


def list_las_files() -> Dict[str, Any]:
    """List all available LAS files"""
    try:
        data_dir = Path("data")
        if not data_dir.exists():
            return {'error': 'Data directory not found', 'success': False}
        
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
            except Exception:
                continue
        
        return {
            'success': True,
            'files': sorted(las_files, key=lambda x: x['filename']),
            'total_files': len(las_files),
            'total_size_kb': sum(f['size_kb'] for f in las_files)
        }
        
    except Exception as e:
        return {'error': f'Error listing LAS files: {str(e)}', 'success': False}


def analyze_las_file(filename: str) -> Dict[str, Any]:
    """Analyze a LAS file using pure Python parser"""
    try:
        # Find the file
        data_dir = Path("data")
        las_path = None
        
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {'error': f'LAS file "{filename}" not found', 'success': False}
        
        # Parse the file
        parser = SimpleLASParser()
        result = parser.parse_las_file(las_path)
        
        return result
        
    except Exception as e:
        return {'error': f'Error analyzing LAS file: {str(e)}', 'success': False}


def get_las_data_for_plotting(filename: str, curve_names: List[str] = None) -> Dict[str, Any]:
    """Get LAS data formatted for frontend plotting"""
    try:
        # Parse the file
        parser = SimpleLASParser()
        data_dir = Path("data")
        
        las_path = None
        for path in data_dir.rglob(filename):
            if path.suffix.lower() == '.las':
                las_path = path
                break
        
        if not las_path:
            return {'error': f'LAS file "{filename}" not found', 'success': False}
        
        result = parser.parse_las_file(las_path)
        if not result.get('success'):
            return result
        
        # Format data for plotting
        curves = result['curves']
        data = parser.data
        
        if not data:
            return {'error': 'No data found in LAS file', 'success': False}
        
        # Create plotting data structure
        plot_data = {
            'success': True,
            'filename': filename,
            'curves_available': [curve['mnemonic'] for curve in curves],
            'depth_range': {},
            'plot_series': {}
        }
        
        # Assume first column is depth
        if curves:
            depth_mnemonic = curves[0]['mnemonic']
            depth_values = [row[0] for row in data if row and row[0] is not None]
            
            if depth_values:
                plot_data['depth_range'] = {
                    'min': min(depth_values),
                    'max': max(depth_values),
                    'count': len(depth_values)
                }
                
                # Prepare data for each requested curve
                requested_curves = curve_names or [curve['mnemonic'] for curve in curves[1:6]]  # First 5 non-depth curves
                
                for i, curve in enumerate(curves):
                    if curve['mnemonic'] in requested_curves and i > 0:  # Skip depth column
                        curve_data = []
                        for row in data:
                            if i < len(row) and row[0] is not None and row[i] is not None:
                                curve_data.append({
                                    'depth': row[0],
                                    'value': row[i]
                                })
                        
                        plot_data['plot_series'][curve['mnemonic']] = {
                            'data': curve_data,
                            'unit': curve['unit'],
                            'description': curve['description'],
                            'point_count': len(curve_data)
                        }
        
        return plot_data
        
    except Exception as e:
        return {'error': f'Error preparing plot data: {str(e)}', 'success': False}


if __name__ == "__main__":
    # Command line interface
    if len(sys.argv) < 2:
        print("Usage: python las_parser_pure.py <command> [args]")
        print("Commands:")
        print("  list                    - List all LAS files")
        print("  analyze <filename>      - Analyze a LAS file")
        print("  plot-data <filename>    - Get data for plotting")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        result = list_las_files()
        print(result)
    
    elif command == "analyze":
        if len(sys.argv) < 3:
            print("Error: filename required for analyze command")
            sys.exit(1)
        result = analyze_las_file(sys.argv[2])
        print(result)
    
    elif command == "plot-data":
        if len(sys.argv) < 3:
            print("Error: filename required for plot-data command")
            sys.exit(1)
        result = get_las_data_for_plotting(sys.argv[2])
        print(result)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)