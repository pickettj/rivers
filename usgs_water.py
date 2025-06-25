#!/usr/bin/env python3
"""
USGS Water Level Library

A clean library for retrieving USGS water level data.
Import this into other scripts for water level functionality.

Required packages:
    pip install dataretrieval requests pandas

Usage:
    import usgs_water
    
    # Get water level data
    df = usgs_water.get_water_level(site_id='03044000', days=7)
    
    # Check if in range
    result = usgs_water.check_water_level_range(site_id='03044000', min_level=3.0, max_level=8.0)
    
    # Get site info
    info = usgs_water.get_site_info(site_id='03044000')
"""

import dataretrieval.nwis as nwis
import requests
import pandas as pd
from datetime import datetime, timedelta

def normalize_site_id(site_id):
    """Ensure site ID is 8-digit string with leading zeros."""
    return str(site_id).zfill(8)

def get_water_level(site_id, days=7):
    """
    Get water level data using the official USGS dataretrieval package.
    
    Args:
        site_id (str): USGS site ID (e.g., '03044000')
        days (int): Number of days of data to retrieve
    
    Returns:
        pandas.DataFrame: Water level data
    """
    try:
        site_id = normalize_site_id(site_id)  # Ensure proper format
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get instantaneous values for gage height (parameter 00065)
        df = nwis.get_record(
            sites=site_id,
            service='iv',  # instantaneous values
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            parameterCd='00065'  # Gage height
        )
        
        return df
        
    except Exception as e:
        print(f"Error retrieving data for site {site_id}: {e}")
        return pd.DataFrame()

def get_discharge(site_id, days=7):
    """
    Get discharge (CFS) data using the official USGS dataretrieval package.
    
    Args:
        site_id (str): USGS site ID (e.g., '03044000')
        days (int): Number of days of data to retrieve
    
    Returns:
        pandas.DataFrame: Discharge data
    """
    try:
        site_id = normalize_site_id(site_id)  # Ensure proper format
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get instantaneous values for discharge (parameter 00060)
        df = nwis.get_record(
            sites=site_id,
            service='iv',  # instantaneous values
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            parameterCd='00060'  # Discharge in CFS
        )
        
        return df
        
    except Exception as e:
        print(f"Error retrieving discharge data for site {site_id}: {e}")
        return pd.DataFrame()

def get_latest_water_level(site_id):
    """
    Get the most recent water level measurement.
    
    Args:
        site_id (str): USGS site ID
    
    Returns:
        dict: {'level': float, 'timestamp': datetime, 'site_id': str} or None if error
    """
    try:
        df = get_water_level(site_id, days=1)
        
        if df.empty:
            return None
        
        # Find the gage height column
        gage_height_col = None
        for col in df.columns:
            if '00065' in col:
                gage_height_col = col
                break
        
        if not gage_height_col:
            return None
            
        latest_level = df.iloc[-1][gage_height_col]
        timestamp = df.index[-1]
        
        return {
            'level': latest_level,
            'timestamp': timestamp,
            'site_id': site_id,
            'column_name': gage_height_col,
            'metric': 'feet'
        }
        
    except Exception as e:
        print(f"Error getting latest water level for site {site_id}: {e}")
        return None

def get_latest_discharge(site_id):
    """
    Get the most recent discharge measurement.
    
    Args:
        site_id (str): USGS site ID
    
    Returns:
        dict: {'level': float, 'timestamp': datetime, 'site_id': str} or None if error
    """
    try:
        df = get_discharge(site_id, days=1)
        
        if df.empty:
            return None
        
        # Find the discharge column
        discharge_col = None
        for col in df.columns:
            if '00060' in col:
                discharge_col = col
                break
        
        if not discharge_col:
            return None
            
        latest_discharge = df.iloc[-1][discharge_col]
        timestamp = df.index[-1]
        
        return {
            'level': latest_discharge,
            'timestamp': timestamp,
            'site_id': site_id,
            'column_name': discharge_col,
            'metric': 'cfs'
        }
        
    except Exception as e:
        print(f"Error getting latest discharge for site {site_id}: {e}")
        return None

def get_water_level_direct_api(site_id, days=7):
    """
    Get water level data using direct API requests (legacy WaterServices).
    
    Args:
        site_id (str): USGS site ID
        days (int): Number of days of data to retrieve
    
    Returns:
        dict: JSON response data or empty dict if error
    """
    try:
        # Build API URL
        base_url = "https://waterservices.usgs.gov/nwis/iv/"
        params = {
            'format': 'json',
            'sites': site_id,
            'parameterCd': '00065',  # Gage height
            'period': f'P{days}D'    # Last N days
        }
        
        # Make request
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        print(f"Error with direct API request for site {site_id}: {e}")
        return {}

def get_site_info(site_id):
    """
    Get basic information about a USGS monitoring site.
    
    Args:
        site_id (str): USGS site ID
    
    Returns:
        pandas.DataFrame: Site information or empty DataFrame if error
    """
    try:
        site_info = nwis.get_record(sites=site_id, service='site')
        return site_info
    except Exception as e:
        print(f"Error getting site info for {site_id}: {e}")
        return pd.DataFrame()

def get_site_name(site_id):
    """
    Get the name of a USGS monitoring site.
    
    Args:
        site_id (str): USGS site ID
    
    Returns:
        str: Site name or None if error
    """
    try:
        site_info = get_site_info(site_id)
        if not site_info.empty:
            return site_info.iloc[0].get('station_nm', None)
        return None
    except Exception as e:
        print(f"Error getting site name for {site_id}: {e}")
        return None

def check_water_level_range(site_id, min_level=None, max_level=None, min_cfs=None, max_cfs=None):
    """
    Check if current water level or discharge is within specified range.
    
    Args:
        site_id (str): USGS site ID
        min_level (float, optional): Minimum acceptable water level (feet)
        max_level (float, optional): Maximum acceptable water level (feet)
        min_cfs (float, optional): Minimum acceptable discharge (CFS)
        max_cfs (float, optional): Maximum acceptable discharge (CFS)
    
    Returns:
        dict: Status information with keys:
              - status: 'good', 'too_low', 'too_high', 'no_data', or 'error'
              - current_level: float or None
              - timestamp: datetime or None
              - message: str description
              - min_level/min_cfs: float
              - max_level/max_cfs: float
              - metric: 'feet' or 'cfs'
    """
    try:
        # Determine which metric to use
        use_cfs = (min_cfs is not None and max_cfs is not None and 
                   not (pd.isna(min_cfs) or pd.isna(max_cfs)))
        
        if use_cfs:
            latest = get_latest_discharge(site_id)
            min_val = min_cfs
            max_val = max_cfs
            metric = 'cfs'
            unit = 'CFS'
        else:
            latest = get_latest_water_level(site_id)
            min_val = min_level
            max_val = max_level
            metric = 'feet'
            unit = 'ft'
        
        if not latest:
            return {
                'status': 'no_data', 
                'message': 'No data available', 
                'current_level': None, 
                'timestamp': None,
                'min_level': min_val if metric == 'feet' else None,
                'max_level': max_val if metric == 'feet' else None,
                'min_cfs': min_val if metric == 'cfs' else None,
                'max_cfs': max_val if metric == 'cfs' else None,
                'metric': metric
            }
        
        current_level = latest['level']
        timestamp = latest['timestamp']
        
        # Check range
        if min_val <= current_level <= max_val:
            status = 'good'
            message = f"Water level ({current_level:.2f} {unit}) is in preferred range"
        elif current_level < min_val:
            status = 'too_low'
            message = f"Water level ({current_level:.2f} {unit}) is below minimum ({min_val} {unit})"
        else:
            status = 'too_high'
            message = f"Water level ({current_level:.2f} {unit}) is above maximum ({max_val} {unit})"
        
        result = {
            'status': status,
            'current_level': current_level,
            'timestamp': timestamp,
            'message': message,
            'site_id': site_id,
            'metric': metric
        }
        
        # Add appropriate min/max values based on metric used
        if metric == 'feet':
            result['min_level'] = min_val
            result['max_level'] = max_val
            result['min_cfs'] = None
            result['max_cfs'] = None
        else:
            result['min_cfs'] = min_val
            result['max_cfs'] = max_val
            result['min_level'] = None
            result['max_level'] = None
        
        return result
        
    except Exception as e:
        return {
            'status': 'error', 
            'message': f'Error: {e}',
            'current_level': None, 
            'timestamp': None,
            'min_level': min_level,
            'max_level': max_level,
            'min_cfs': min_cfs,
            'max_cfs': max_cfs,
            'metric': 'unknown'
        }

def get_multiple_sites_status(sites_config):
    """
    Check water level status for multiple sites.
    
    Args:
        sites_config (list): List of dicts with keys: site_id, min_level, max_level, min_cfs, max_cfs
                            Example: [{'site_id': '03044000', 'min_level': 3.0, 'max_level': 8.0, 'min_cfs': None, 'max_cfs': None}]
    
    Returns:
        list: List of status dicts for each site
    """
    results = []
    
    for site_config in sites_config:
        site_id = site_config['site_id']
        min_level = site_config.get('min_level')
        max_level = site_config.get('max_level')
        min_cfs = site_config.get('min_cfs')
        max_cfs = site_config.get('max_cfs')
        
        result = check_water_level_range(site_id, min_level, max_level, min_cfs, max_cfs)
        result['name'] = site_config.get('name', get_site_name(site_id))
        results.append(result)
    
    return results

def get_site_coordinates(site_id):
    """
    Get latitude and longitude coordinates for a USGS site.
    
    Args:
        site_id (str): USGS site ID
    
    Returns:
        tuple: (latitude, longitude) or (None, None) if error
    """
    try:
        site_info = get_site_info(site_id)
        if not site_info.empty:
            info = site_info.iloc[0]
            lat = info.get('dec_lat_va', None)
            lon = info.get('dec_long_va', None)
            return lat, lon
        return None, None
    except Exception as e:
        print(f"Error getting coordinates for site {site_id}: {e}")
        return None, None