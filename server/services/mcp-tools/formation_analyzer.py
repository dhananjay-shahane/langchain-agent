#!/usr/bin/env python3
"""
Formation Analyzer MCP Tool
Real formation analysis functionality
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add the packages to path
sys.path.extend([
    '/nix/store/zz7i75jb78idaz0rb1y1i4rzdyxq28vf-sitecustomize/lib/python/site-packages',
    '/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages'
])

import lasio
import numpy as np


def analyze_gamma_ray_lithology(filename: str) -> Dict[str, Any]:
    """Analyze gamma ray data for lithology identification."""
    try:
        # Find and read LAS file
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
        
        # Read LAS file
        las = lasio.read(las_path)
        df = las.df()
        
        # Find gamma ray curve
        gr_column = None
        for col in ['GR', 'GAMMA', 'GAMMA_RAY', 'GRC']:
            if col in df.columns:
                gr_column = col
                break
        
        if gr_column is None:
            return {
                'error': f"No gamma ray curve found in {filename}",
                'success': False
            }
        
        # Clean data
        depth = df.index
        gamma = df[gr_column]
        mask = ~(np.isnan(gamma) | np.isnan(depth))
        depth_clean = depth[mask]
        gamma_clean = gamma[mask]
        
        if len(depth_clean) == 0:
            return {
                'error': f"No valid gamma ray data in {filename}",
                'success': False
            }
        
        # Lithology classification based on gamma ray values
        lithology_zones = []
        
        # Define thresholds
        clean_sand_threshold = 60  # API
        shale_threshold = 100      # API
        
        # Analyze zones (simplified approach - can be made more sophisticated)
        window_size = max(1, len(gamma_clean) // 20)  # Adaptive window size
        
        for i in range(0, len(gamma_clean), window_size):
            start_idx = i
            end_idx = min(i + window_size, len(gamma_clean))
            
            zone_gamma = gamma_clean.iloc[start_idx:end_idx]
            zone_depth_start = depth_clean.iloc[start_idx]
            zone_depth_end = depth_clean.iloc[end_idx - 1]
            
            avg_gamma = zone_gamma.mean()
            
            # Classify lithology
            if avg_gamma < clean_sand_threshold:
                lithology = "Clean Sand"
                quality = "Good reservoir potential"
            elif avg_gamma > shale_threshold:
                lithology = "Shale"
                quality = "Seal rock / source potential"
            else:
                lithology = "Sandy Shale / Carbonate"
                quality = "Moderate reservoir potential"
            
            lithology_zones.append({
                'depth_start': float(zone_depth_start),
                'depth_end': float(zone_depth_end),
                'thickness': float(zone_depth_end - zone_depth_start),
                'lithology': lithology,
                'avg_gamma': float(avg_gamma),
                'quality': quality
            })
        
        # Calculate overall statistics
        total_thickness = depth_clean.max() - depth_clean.min()
        clean_sand_thickness = sum(zone['thickness'] for zone in lithology_zones 
                                 if zone['lithology'] == "Clean Sand")
        shale_thickness = sum(zone['thickness'] for zone in lithology_zones 
                            if zone['lithology'] == "Shale")
        
        # Formation tops (basic identification based on major GR changes)
        formation_tops = identify_formation_tops(depth_clean, gamma_clean)
        
        return {
            'success': True,
            'filename': filename,
            'curve_used': gr_column,
            'total_interval': float(total_thickness),
            'lithology_summary': {
                'clean_sand_percentage': round((clean_sand_thickness / total_thickness) * 100, 1),
                'shale_percentage': round((shale_thickness / total_thickness) * 100, 1),
                'mixed_percentage': round(((total_thickness - clean_sand_thickness - shale_thickness) / total_thickness) * 100, 1)
            },
            'lithology_zones': lithology_zones,
            'formation_tops': formation_tops,
            'statistics': {
                'min_gamma': float(gamma_clean.min()),
                'max_gamma': float(gamma_clean.max()),
                'mean_gamma': float(gamma_clean.mean()),
                'std_gamma': float(gamma_clean.std())
            }
        }
        
    except Exception as e:
        return {
            'error': f"Error analyzing gamma ray lithology for {filename}: {str(e)}",
            'success': False
        }


def identify_formation_tops(depth: np.ndarray, gamma: np.ndarray) -> List[Dict[str, Any]]:
    """Identify potential formation tops based on gamma ray signature changes."""
    try:
        formation_tops = []
        
        # Calculate moving average and derivative
        window = max(5, len(gamma) // 50)
        gamma_smooth = np.convolve(gamma, np.ones(window)/window, mode='valid')
        depth_smooth = depth[window//2:len(depth)-window//2+1]
        
        # Find significant changes in gamma ray
        grad = np.gradient(gamma_smooth)
        
        # Find peaks and troughs in gradient (formation boundaries)
        threshold = np.std(grad) * 2  # Adaptive threshold
        
        significant_changes = []
        for i in range(1, len(grad)-1):
            if abs(grad[i]) > threshold:
                # Check if it's a local extremum
                if (grad[i] > grad[i-1] and grad[i] > grad[i+1]) or \
                   (grad[i] < grad[i-1] and grad[i] < grad[i+1]):
                    significant_changes.append({
                        'depth': float(depth_smooth[i]),
                        'gamma_value': float(gamma_smooth[i]),
                        'gradient': float(grad[i]),
                        'change_type': 'increase' if grad[i] > 0 else 'decrease'
                    })
        
        # Sort by depth and create formation tops
        significant_changes.sort(key=lambda x: x['depth'])
        
        for i, change in enumerate(significant_changes[:10]):  # Limit to 10 major tops
            formation_name = f"Formation_{i+1}"
            
            # Basic formation naming based on gamma signature
            if change['gamma_value'] > 100:
                formation_name = f"Shale_Unit_{i+1}"
            elif change['gamma_value'] < 60:
                formation_name = f"Sand_Unit_{i+1}"
            else:
                formation_name = f"Mixed_Unit_{i+1}"
            
            formation_tops.append({
                'formation_name': formation_name,
                'depth': change['depth'],
                'gamma_value': change['gamma_value'],
                'confidence': 'moderate',
                'description': f"Gamma ray {change['change_type']} at {change['depth']:.0f} ft"
            })
        
        return formation_tops
        
    except Exception as e:
        print(f"Warning: Could not identify formation tops: {e}")
        return []


def analyze_porosity_quality(filename: str) -> Dict[str, Any]:
    """Analyze porosity data for reservoir quality assessment."""
    try:
        # Find and read LAS file
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
        
        # Read LAS file
        las = lasio.read(las_path)
        df = las.df()
        
        # Find porosity curves
        nphi_column = None
        dphi_column = None
        
        for col in ['NPHI', 'NEUTRON', 'PHIN', 'PHI_N']:
            if col in df.columns:
                nphi_column = col
                break
        
        for col in ['DPHI', 'DENSITY_POR', 'PHI_D', 'PHID']:
            if col in df.columns:
                dphi_column = col
                break
        
        if nphi_column is None and dphi_column is None:
            return {
                'error': f"No porosity curves found in {filename}",
                'success': False
            }
        
        depth = df.index
        analysis_results = {
            'success': True,
            'filename': filename,
            'curves_used': [],
            'porosity_zones': [],
            'quality_summary': {}
        }
        
        # Analyze neutron porosity
        if nphi_column:
            analysis_results['curves_used'].append(nphi_column)
            nphi = df[nphi_column]
            mask = ~(np.isnan(nphi) | np.isnan(depth))
            
            if mask.any():
                nphi_clean = nphi[mask]
                depth_clean = depth[mask]
                
                # Classify porosity zones
                for i in range(0, len(nphi_clean), max(1, len(nphi_clean)//20)):
                    end_idx = min(i + len(nphi_clean)//20, len(nphi_clean))
                    zone_phi = nphi_clean.iloc[i:end_idx]
                    zone_depth_start = depth_clean.iloc[i]
                    zone_depth_end = depth_clean.iloc[end_idx-1] if end_idx > i else depth_clean.iloc[i]
                    
                    avg_phi = zone_phi.mean() * 100  # Convert to percentage
                    
                    if avg_phi < 10:
                        quality = "Tight - Poor reservoir"
                    elif avg_phi < 15:
                        quality = "Fair reservoir potential"
                    elif avg_phi < 20:
                        quality = "Good reservoir potential"
                    else:
                        quality = "Excellent reservoir potential"
                    
                    analysis_results['porosity_zones'].append({
                        'depth_start': float(zone_depth_start),
                        'depth_end': float(zone_depth_end),
                        'avg_porosity_percent': round(float(avg_phi), 1),
                        'porosity_type': 'neutron',
                        'quality': quality
                    })
        
        # Calculate overall quality metrics
        if analysis_results['porosity_zones']:
            total_thickness = sum(zone['depth_end'] - zone['depth_start'] 
                                for zone in analysis_results['porosity_zones'])
            
            good_zones = [zone for zone in analysis_results['porosity_zones'] 
                         if zone['avg_porosity_percent'] >= 15]
            good_thickness = sum(zone['depth_end'] - zone['depth_start'] for zone in good_zones)
            
            analysis_results['quality_summary'] = {
                'total_interval_ft': round(float(total_thickness), 1),
                'good_reservoir_ft': round(float(good_thickness), 1),
                'net_to_gross_ratio': round((good_thickness / total_thickness) * 100, 1) if total_thickness > 0 else 0,
                'average_porosity': round(np.mean([zone['avg_porosity_percent'] for zone in analysis_results['porosity_zones']]), 1)
            }
        
        return analysis_results
        
    except Exception as e:
        return {
            'error': f"Error analyzing porosity quality for {filename}: {str(e)}",
            'success': False
        }


def analyze_fluid_contacts(filename: str) -> Dict[str, Any]:
    """Analyze resistivity data for fluid contacts and saturation."""
    try:
        # Find and read LAS file  
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
        
        # Read LAS file
        las = lasio.read(las_path)
        df = las.df()
        
        # Find resistivity curve
        res_column = None
        for col in ['RT', 'RES', 'RESISTIVITY', 'ILD']:
            if col in df.columns:
                res_column = col
                break
        
        if res_column is None:
            return {
                'error': f"No resistivity curve found in {filename}",
                'success': False
            }
        
        depth = df.index
        resistivity = df[res_column]
        mask = ~(np.isnan(resistivity) | np.isnan(depth)) & (resistivity > 0)
        
        if not mask.any():
            return {
                'error': f"No valid resistivity data in {filename}",
                'success': False
            }
        
        depth_clean = depth[mask]
        res_clean = resistivity[mask]
        
        # Analyze fluid contacts based on resistivity patterns
        fluid_zones = []
        window_size = max(5, len(res_clean) // 30)
        
        for i in range(0, len(res_clean), window_size):
            end_idx = min(i + window_size, len(res_clean))
            zone_res = res_clean.iloc[i:end_idx]
            zone_depth_start = depth_clean.iloc[i]
            zone_depth_end = depth_clean.iloc[end_idx-1] if end_idx > i else depth_clean.iloc[i]
            
            avg_res = zone_res.mean()
            
            # Classify fluid type based on resistivity
            if avg_res < 2:
                fluid_type = "Water"
                saturation = ">80% water"
            elif avg_res < 10:
                fluid_type = "Transition Zone"
                saturation = "50-80% water"
            elif avg_res < 50:
                fluid_type = "Oil"
                saturation = "20-50% water"
            else:
                fluid_type = "Gas/Tight Oil"
                saturation = "<20% water"
            
            fluid_zones.append({
                'depth_start': float(zone_depth_start),
                'depth_end': float(zone_depth_end),
                'thickness': float(zone_depth_end - zone_depth_start),
                'avg_resistivity': round(float(avg_res), 2),
                'fluid_type': fluid_type,
                'water_saturation': saturation
            })
        
        # Identify potential contacts
        contacts = []
        for i in range(len(fluid_zones)-1):
            current_zone = fluid_zones[i]
            next_zone = fluid_zones[i+1]
            
            # Look for significant resistivity changes
            res_ratio = next_zone['avg_resistivity'] / current_zone['avg_resistivity']
            
            if res_ratio > 3 or res_ratio < 0.33:  # Significant change
                contact_depth = (current_zone['depth_end'] + next_zone['depth_start']) / 2
                contacts.append({
                    'depth': round(contact_depth, 1),
                    'type': f"{current_zone['fluid_type']} / {next_zone['fluid_type']} contact",
                    'confidence': 'moderate'
                })
        
        return {
            'success': True,
            'filename': filename,
            'curve_used': res_column,
            'fluid_zones': fluid_zones,
            'fluid_contacts': contacts,
            'hydrocarbon_summary': {
                'total_hydrocarbon_ft': sum(zone['thickness'] for zone in fluid_zones 
                                          if 'Oil' in zone['fluid_type'] or 'Gas' in zone['fluid_type']),
                'oil_zones': [zone for zone in fluid_zones if zone['fluid_type'] == 'Oil'],
                'gas_zones': [zone for zone in fluid_zones if 'Gas' in zone['fluid_type']]
            }
        }
        
    except Exception as e:
        return {
            'error': f"Error analyzing fluid contacts for {filename}: {str(e)}",
            'success': False
        }


if __name__ == "__main__":
    # Command line interface for testing
    if len(sys.argv) < 3:
        print("Usage: python formation_analyzer.py <analysis_type> <filename>")
        print("Analysis types: lithology, porosity, fluids")
        sys.exit(1)
    
    analysis_type = sys.argv[1]
    filename = sys.argv[2]
    
    if analysis_type == "lithology":
        result = analyze_gamma_ray_lithology(filename)
    elif analysis_type == "porosity":
        result = analyze_porosity_quality(filename)
    elif analysis_type == "fluids":
        result = analyze_fluid_contacts(filename)
    else:
        print(f"Unknown analysis type: {analysis_type}")
        sys.exit(1)
    
    print(result)