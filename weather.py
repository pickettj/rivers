#!/usr/bin/env python3
"""
Weather Data Library - Updated with Multi-Day Forecast Support

A clean library for retrieving weather data using Open-Meteo API.
Import this into other scripts for weather functionality.

Required packages:
    pip install requests

Usage:
    import weather
    
    # Get weather by ZIP code with forecast
    data = weather.get_weather_by_zip("15213", forecast_days=7)
    
    # Get weather by city
    data = weather.get_weather_by_city("Pittsburgh, PA", forecast_days=7)
    
    # Get weather by coordinates
    data = weather.get_weather_by_coords(40.4406, -79.9959, forecast_days=7)
    
    # Check paddling conditions
    assessment = weather.assess_paddling_conditions(data)
    
    # Get forecast for specific date
    from datetime import date, timedelta
    target_date = date.today() + timedelta(days=3)
    day_forecast = weather.get_forecast_for_date(data, target_date)
"""

import requests
from datetime import datetime

def get_coordinates_from_zip(zip_code):
    """
    Convert US ZIP code to latitude/longitude using a geocoding service.
    
    Args:
        zip_code (str or int): US ZIP code
    
    Returns:
        tuple: (latitude, longitude) or (None, None) if not found
    """
    try:
        zip_code = str(zip_code).zfill(5)  # Ensure 5-digit string
        url = f"https://api.zippopotam.us/us/{zip_code}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            lat = float(data['places'][0]['latitude'])
            lon = float(data['places'][0]['longitude'])
            return lat, lon
        else:
            return None, None
            
    except Exception as e:
        print(f"Error geocoding ZIP {zip_code}: {e}")
        return None, None

def get_coordinates_from_city(city_name):
    """
    Convert city name to coordinates using OpenStreetMap Nominatim.
    
    Args:
        city_name (str): City name (e.g., "Pittsburgh, PA" or "Pittsburgh")
    
    Returns:
        tuple: (latitude, longitude) or (None, None) if not found
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': city_name,
            'format': 'json',
            'limit': 1
        }
        headers = {'User-Agent': 'RiverPaddlingWeather/1.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon
            else:
                return None, None
        else:
            return None, None
            
    except Exception as e:
        print(f"Error geocoding city {city_name}: {e}")
        return None, None

def get_weather_data(latitude, longitude, forecast_days=1):
    """
    Get weather data from Open-Meteo API with multi-day forecast support.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        forecast_days (int): Number of forecast days (default 1, max 16 for free tier)
    
    Returns:
        dict: Weather data or None if error
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'current': [
                'temperature_2m',
                'relative_humidity_2m',
                'precipitation',
                'wind_speed_10m',
                'wind_direction_10m',
                'wind_gusts_10m'
            ],
            'hourly': [
                'temperature_2m',
                'precipitation_probability',
                'precipitation',
                'wind_speed_10m',
                'wind_direction_10m',
                'wind_gusts_10m'
            ],
            'temperature_unit': 'fahrenheit',
            'wind_speed_unit': 'mph',
            'precipitation_unit': 'inch',
            'timezone': 'auto',
            'forecast_days': min(forecast_days, 16)  # API limit is 16 days for free tier
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None

def get_forecast_for_date(weather_data, target_date):
    """
    Extract forecast data for a specific date by parsing timestamps.
    
    Args:
        weather_data (dict): Weather data from API
        target_date (date): Target date object
    
    Returns:
        dict: Forecast data for that date, or None
    """
    try:
        from datetime import datetime
        hourly = weather_data['hourly']
        
        # Find hours that match the target date
        target_hours = []
        for i, time_str in enumerate(hourly['time']):
            # Parse the timestamp (handle both with and without 'Z')
            if time_str.endswith('Z'):
                hour_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
                hour_time = datetime.fromisoformat(time_str)
            
            # Check if this hour is on our target date
            if hour_time.date() == target_date:
                target_hours.append(i)
        
        if not target_hours:
            return None
        
        # Use midday hour (around 12pm) as representative for the day
        midday_hour = target_hours[len(target_hours)//2] if target_hours else target_hours[0]
        
        # Get average conditions for the day
        day_temps = [hourly['temperature_2m'][h] for h in target_hours if h < len(hourly['temperature_2m'])]
        day_winds = [hourly['wind_speed_10m'][h] for h in target_hours if h < len(hourly['wind_speed_10m'])]
        day_precip_probs = [hourly['precipitation_probability'][h] for h in target_hours if h < len(hourly['precipitation_probability'])]
        day_precips = [hourly['precipitation'][h] for h in target_hours if h < len(hourly['precipitation'])]
        day_gusts = [hourly['wind_gusts_10m'][h] for h in target_hours if h < len(hourly['wind_gusts_10m'])]
        day_dirs = [hourly['wind_direction_10m'][h] for h in target_hours if h < len(hourly['wind_direction_10m'])]
        
        # Create forecast using averages and midday values
        day_forecast = {
            'temperature': sum(day_temps) / len(day_temps) if day_temps else hourly['temperature_2m'][midday_hour],
            'wind_speed': sum(day_winds) / len(day_winds) if day_winds else hourly['wind_speed_10m'][midday_hour],
            'wind_direction': day_dirs[len(day_dirs)//2] if day_dirs else hourly['wind_direction_10m'][midday_hour],
            'wind_gusts': max(day_gusts) if day_gusts else hourly['wind_gusts_10m'][midday_hour],
            'precipitation_probability': max(day_precip_probs) if day_precip_probs else hourly['precipitation_probability'][midday_hour],
            'precipitation': sum(day_precips) if day_precips else hourly['precipitation'][midday_hour]
        }
        
        # Generate weather narrative for the day
        day_forecast['narrative'] = generate_weather_narrative_for_date(weather_data, target_date, target_hours)
        
        return day_forecast
        
    except Exception as e:
        print(f"Error parsing forecast for {target_date}: {e}")
        return None

def generate_weather_narrative_for_date(weather_data, target_date, target_hours):
    """
    Generate narrative for a specific date using actual hour indices.
    """
    try:
        if len(target_hours) < 6:  # Need enough hours to analyze
            return ""
        
        hourly = weather_data['hourly']
        
        # Split day into morning, afternoon based on available hours
        morning_hours = target_hours[:len(target_hours)//3]
        afternoon_hours = target_hours[len(target_hours)//3:2*len(target_hours)//3]
        
        if not morning_hours or not afternoon_hours:
            return ""
        
        # Get morning conditions (average of morning hours)
        morning_precip = sum(hourly['precipitation_probability'][h] for h in morning_hours) / len(morning_hours)
        morning_wind = sum(hourly['wind_speed_10m'][h] for h in morning_hours) / len(morning_hours)
        
        # Get afternoon conditions
        afternoon_precip = sum(hourly['precipitation_probability'][h] for h in afternoon_hours) / len(afternoon_hours)
        afternoon_wind = sum(hourly['wind_speed_10m'][h] for h in afternoon_hours) / len(afternoon_hours)
        
        # Generate narrative
        narrative_parts = []
        
        # Morning conditions
        if morning_precip > 60:
            narrative_parts.append("rainy morning")
        elif morning_precip > 30:
            narrative_parts.append("cloudy morning")
        else:
            narrative_parts.append("sunny morning")
        
        # Changes throughout day
        wind_diff = afternoon_wind - morning_wind
        if wind_diff > 5:
            narrative_parts.append("winds increase afternoon")
        elif wind_diff < -5:
            narrative_parts.append("winds calm afternoon")
        
        # Precipitation changes
        if morning_precip < 30 and afternoon_precip > 50:
            if afternoon_precip > 70:
                narrative_parts.append("rain develops afternoon")
            else:
                narrative_parts.append("clouds increase afternoon")
        elif morning_precip > 50 and afternoon_precip < 30:
            narrative_parts.append("clearing afternoon")
        elif afternoon_precip > 60 and "rainy morning" not in narrative_parts:
            narrative_parts.append("afternoon showers")
        
        # Join and format
        if narrative_parts:
            narrative = ", ".join(narrative_parts)
            narrative = narrative[0].upper() + narrative[1:] if narrative else ""
            if len(narrative) > 50:
                narrative = narrative[:47] + "..."
            return narrative
        else:
            return ""
    
    except Exception as e:
        return ""

def get_current_conditions(weather_data):
    """
    Extract current weather conditions from API response.
    
    Args:
        weather_data (dict): Weather data from Open-Meteo API
    
    Returns:
        dict: Current conditions or None if error
    """
    if not weather_data or 'current' not in weather_data:
        return None
    
    try:
        current = weather_data['current']
        
        return {
            'temperature': current['temperature_2m'],
            'humidity': current['relative_humidity_2m'],
            'precipitation': current['precipitation'],
            'wind_speed': current['wind_speed_10m'],
            'wind_direction': current['wind_direction_10m'],
            'wind_gusts': current['wind_gusts_10m'],
            'wind_direction_name': get_wind_direction_name(current['wind_direction_10m'])
        }
        
    except KeyError as e:
        print(f"Error parsing current conditions: Missing key {e}")
        return None

def get_wind_direction_name(degrees):
    """Convert wind direction in degrees to compass direction name."""
    if degrees is None:
        return "Unknown"
    
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    
    index = round(degrees / 22.5) % 16
    return directions[index]

def assess_paddling_conditions(weather_data):
    """
    Assess weather conditions for river paddling.
    
    Args:
        weather_data (dict): Weather data from API
    
    Returns:
        dict: Assessment with status and message
    """
    if not weather_data:
        return {'status': 'no_data', 'message': 'No weather data available'}
    
    try:
        current = weather_data['current']
        wind_speed = current['wind_speed_10m']
        wind_gusts = current['wind_gusts_10m']
        precipitation = current['precipitation']
        temp = current['temperature_2m']
        
        issues = []
        
        if wind_speed > 15:
            issues.append(f"High wind speed ({wind_speed} mph)")
        if wind_gusts > 20:
            issues.append(f"Strong wind gusts ({wind_gusts} mph)")
        if precipitation > 0.1:
            issues.append(f"Active precipitation ({precipitation}\")")
        if temp < 50:
            issues.append(f"Cold temperature ({temp}°F)")
        if temp > 95:
            issues.append(f"Very hot temperature ({temp}°F)")
        
        if not issues:
            status = 'good'
            message = "Conditions look good for paddling!"
        elif len(issues) == 1:
            status = 'caution'
            message = f"Caution: {issues[0]}"
        else:
            status = 'poor'
            message = f"Poor conditions: {', '.join(issues)}"
        
        return {
            'status': status,
            'message': message,
            'wind_speed': wind_speed,
            'wind_gusts': wind_gusts,
            'precipitation': precipitation,
            'temperature': temp,
            'issues': issues
        }
        
    except Exception as e:
        return {'status': 'error', 'message': f'Error assessing conditions: {e}'}

def get_hourly_forecast(weather_data, hours=6):
    """
    Get hourly forecast data.
    
    Args:
        weather_data (dict): Weather data from API
        hours (int): Number of hours to return (default 6)
    
    Returns:
        list: List of hourly forecasts
    """
    if not weather_data or 'hourly' not in weather_data:
        return []
    
    try:
        hourly = weather_data['hourly']
        forecast = []
        
        for i in range(1, min(hours + 1, len(hourly['time']))):
            time_str = hourly['time'][i]
            
            # Parse time for display
            hour_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
            forecast.append({
                'time': hour_time,
                'time_display': hour_time.strftime('%I%p').lstrip('0').lower(),
                'temperature': hourly['temperature_2m'][i],
                'wind_speed': hourly['wind_speed_10m'][i],
                'wind_direction': hourly['wind_direction_10m'][i],
                'wind_gusts': hourly['wind_gusts_10m'][i],
                'precipitation_probability': hourly['precipitation_probability'][i],
                'precipitation': hourly['precipitation'][i]
            })
        
        return forecast
        
    except Exception as e:
        print(f"Error parsing hourly forecast: {e}")
        return []

# Convenience functions for different input types
def get_weather_by_zip(zip_code, forecast_days=1):
    """Get weather by ZIP code with multi-day forecast support."""
    lat, lon = get_coordinates_from_zip(zip_code)
    if lat and lon:
        return get_weather_data(lat, lon, forecast_days)
    return None

def get_weather_by_city(city_name, forecast_days=1):
    """Get weather by city name with multi-day forecast support."""
    lat, lon = get_coordinates_from_city(city_name)
    if lat and lon:
        return get_weather_data(lat, lon, forecast_days)
    return None

def get_weather_by_coords(latitude, longitude, forecast_days=1):
    """Get weather by coordinates with multi-day forecast support."""
    return get_weather_data(latitude, longitude, forecast_days)

def get_weather_summary(location, location_type='zip', forecast_days=1):
    """
    Get a complete weather summary for a location.
    
    Args:
        location (str/int): ZIP code, city name, or coordinates
        location_type (str): 'zip', 'city', or 'coords'
        forecast_days (int): Number of forecast days
    
    Returns:
        dict: Complete weather summary with current conditions and assessment
    """
    # Get weather data based on location type
    if location_type == 'zip':
        weather_data = get_weather_by_zip(location, forecast_days)
    elif location_type == 'city':
        weather_data = get_weather_by_city(location, forecast_days)
    elif location_type == 'coords':
        lat, lon = location  # Expecting tuple
        weather_data = get_weather_by_coords(lat, lon, forecast_days)
    else:
        return {'error': 'Invalid location_type'}
    
    if not weather_data:
        return {'error': 'Could not retrieve weather data'}
    
    # Get current conditions and assessment
    current = get_current_conditions(weather_data)
    assessment = assess_paddling_conditions(weather_data)
    forecast = get_hourly_forecast(weather_data, 6)
    
    return {
        'location': location,
        'current': current,
        'assessment': assessment,
        'forecast': forecast,
        'raw_data': weather_data
    }

