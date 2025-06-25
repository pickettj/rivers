#!/usr/bin/env python3
"""
Complete River Evaluation Functions with Real Weather Forecasts

This version uses the updated weather library with multi-day forecast support.
Copy and paste this entire block after updating your weather.py file.
"""

def evaluate_all_rivers(df, home_zip, target_date=None, max_whitewater=None, max_distance=None):
    """
    Evaluate all rivers in the CSV based on water levels and weather conditions.
    
    Args:
        df (pandas.DataFrame): River specifications from CSV
        home_zip (str): Your home ZIP code for distance calculations
        target_date (str, optional): Date in YYYY-MM-DD format. Defaults to today.
        max_whitewater (int, optional): Exclude rivers with whitewater >= this value. 
                                       Use negative value for minimum (e.g., -3 means whitewater >= 3)
        max_distance (int, optional): Exclude rivers more than this many miles away
    
    Returns:
        list: List of river evaluations sorted by overall score
    """
    import math
    from datetime import datetime, date
    import weather
    import usgs_water
    import pandas as pd
    
    # Handle date parameter
    if target_date is None:
        target_date = date.today()
        date_str = target_date.strftime('%Y-%m-%d')
        is_today = True
    else:
        # Parse the provided date
        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            date_str = target_date.strftime('%Y-%m-%d')
            is_today = target_date == date.today()
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
    
    results = []
    excluded_count = 0
    
    # Get home coordinates for distance calculation
    home_lat, home_lon = weather.get_coordinates_from_zip(home_zip)
    if not home_lat or not home_lon:
        print(f"⚠️  Warning: Could not geocode home ZIP {home_zip}")
        home_lat, home_lon = None, None
    
    date_display = "today" if is_today else date_str
    print(f"🏠 Evaluating rivers from home ZIP: {home_zip} for {date_display}")
    print("=" * 70)
    
    for index, river in df.iterrows():
        # Apply whitewater filter first (before processing)
        if max_whitewater is not None:
            if max_whitewater < 0:
                # Negative value means minimum whitewater level
                min_whitewater = abs(max_whitewater)
                if river['Whitewater'] < min_whitewater:
                    print(f"\n⏭️  Skipping: {river['Name']} (Whitewater {river['Whitewater']} < {min_whitewater})")
                    excluded_count += 1
                    continue
            else:
                # Positive value means maximum whitewater level
                if river['Whitewater'] >= max_whitewater:
                    print(f"\n⏭️  Skipping: {river['Name']} (Whitewater {river['Whitewater']} >= {max_whitewater})")
                    excluded_count += 1
                    continue
        
        print(f"\n🔍 Evaluating: {river['Name']} ({river['Route']})")
        
        # Extract CFS values if present
        min_cfs = river.get('Min_cfs')
        max_cfs = river.get('Max_cfs')
        
        # Convert to None if NaN
        if pd.isna(min_cfs):
            min_cfs = None
        if pd.isna(max_cfs):
            max_cfs = None
        
        # Initialize result with ALL needed keys
        result = {
            'name': river['Name'],
            'route': river['Route'],
            'length': river['Length'],
            'whitewater': river['Whitewater'],
            'zipcode': river['Zipcode'],
            'gauge_id': str(river['Gauge_ID']).zfill(8),
            'min_level': river['Min_Level'],
            'max_level': river['Max_Level'],
            'min_cfs': min_cfs,
            'max_cfs': max_cfs,
            'target_date': target_date,
            'date_str': date_str,
            'is_today': is_today,
            'distance_miles': None,
            'water_status': None,
            'weather_status': None,
            'current_conditions': None,
            'overall_score': 0,
            'recommendation': 'unknown',
            'issues': []
        }
        
        # Calculate distance from home
        if home_lat and home_lon:
            river_lat, river_lon = weather.get_coordinates_from_zip(river['Zipcode'])
            if river_lat and river_lon:
                # Haversine formula for distance
                dlat = math.radians(river_lat - home_lat)
                dlon = math.radians(river_lon - home_lon)
                a = (math.sin(dlat/2)**2 + 
                     math.cos(math.radians(home_lat)) * math.cos(math.radians(river_lat)) * 
                     math.sin(dlon/2)**2)
                c = 2 * math.asin(math.sqrt(a))
                distance_miles = 3959 * c  # Earth radius in miles
                result['distance_miles'] = round(distance_miles, 1)
                print(f"   📍 Distance: {result['distance_miles']} miles")
                
                # Apply distance filter after calculating distance
                if max_distance is not None and result['distance_miles'] > max_distance:
                    print(f"   ⏭️  Excluding: Distance {result['distance_miles']} miles > {max_distance} miles")
                    excluded_count += 1
                    continue
        
        # Check water levels (always current - USGS doesn't provide historical/forecast)
        try:
            water_result = usgs_water.check_water_level_range(
                result['gauge_id'],
                result['min_level'], 
                result['max_level'],
                result['min_cfs'],
                result['max_cfs']
            )
            result['water_status'] = water_result
            
            if not is_today:
                print(f"   💧 Water: {water_result['status']} - {water_result['message']} (current data)")
            else:
                print(f"   💧 Water: {water_result['status']} - {water_result['message']}")
        except Exception as e:
            print(f"   ❌ Water level error: {e}")
            result['issues'].append(f"Water data unavailable: {e}")
        
        # Check weather (current for today, forecast for future dates)
        try:
            if is_today:
                # Get current weather for today
                weather_data = weather.get_weather_by_zip(river['Zipcode'])
                if weather_data:
                    weather_assessment = weather.assess_paddling_conditions(weather_data)
                    current_conditions = weather.get_current_conditions(weather_data)
                    result['weather_status'] = weather_assessment
                    result['current_conditions'] = current_conditions
                    print(f"   🌤️  Weather: {weather_assessment['status']} - {weather_assessment['message']}")
                else:
                    result['issues'].append("Weather data unavailable")
                    print(f"   ❌ Weather: Could not retrieve data for ZIP {river['Zipcode']}")
            else:
                # Get forecast for future date
                weather_data = weather.get_weather_by_zip(river['Zipcode'], forecast_days=8)
                if weather_data:
                    # Extract forecast for the specific target date
                    day_forecast = weather.get_forecast_for_date(weather_data, target_date)
                    if day_forecast:
                        # Convert forecast to current_conditions format for compatibility
                        current_conditions = {
                            'temperature': day_forecast['temperature'],
                            'wind_speed': day_forecast['wind_speed'],
                            'wind_direction': day_forecast['wind_direction'],
                            'wind_gusts': day_forecast['wind_gusts'],
                            'wind_direction_name': weather.get_wind_direction_name(day_forecast['wind_direction']),
                            'precipitation': day_forecast['precipitation']
                        }
                        result['current_conditions'] = current_conditions
                        
                        # Assess paddling conditions based on forecast
                        weather_assessment = assess_forecast_conditions(day_forecast)
                        result['weather_status'] = weather_assessment
                        
                        narrative = day_forecast.get('narrative', '')
                        weather_msg = weather_assessment['message']
                        if narrative:
                            weather_msg += f" ({narrative})"
                        
                        print(f"   🌤️  Weather: {weather_assessment['status']} - {weather_msg}")
                    else:
                        result['issues'].append("Forecast data unavailable for target date")
                        print(f"   ❌ Weather: No forecast data for {target_date}")
                else:
                    result['issues'].append("Weather forecast unavailable")
                    print(f"   ❌ Weather: Could not retrieve forecast for ZIP {river['Zipcode']}")
        except Exception as e:
            print(f"   ❌ Weather error: {e}")
            result['issues'].append(f"Weather error: {e}")
        
        # Calculate overall score
        score = calculate_river_score(result)
        result['overall_score'] = score
        result['recommendation'] = get_recommendation(result)
        
        print(f"   🎯 Overall Score: {score}/100 - {result['recommendation']}")
        
        results.append(result)
    
    # Sort by overall score (highest first)
    results.sort(key=lambda x: x['overall_score'], reverse=True)
    
    if excluded_count > 0:
        print(f"\n📊 Excluded {excluded_count} rivers based on filters")
    print(f"✅ Evaluation complete. Found {len(results)} qualifying rivers.")
    return results

def assess_forecast_conditions(day_forecast):
    """
    Assess paddling conditions based on forecast data.
    
    Args:
        day_forecast (dict): Forecast data for a specific day
    
    Returns:
        dict: Assessment with status and message
    """
    try:
        wind_speed = day_forecast['wind_speed']
        wind_gusts = day_forecast['wind_gusts']
        precipitation_prob = day_forecast['precipitation_probability']
        temp = day_forecast['temperature']
        
        issues = []
        
        if wind_speed > 15:
            issues.append(f"High wind speed ({wind_speed:.0f} mph)")
        if wind_gusts > 20:
            issues.append(f"Strong wind gusts ({wind_gusts:.0f} mph)")
        if precipitation_prob > 70:
            issues.append(f"High rain chance ({precipitation_prob:.0f}%)")
        if temp < 50:
            issues.append(f"Cold temperature ({temp:.0f}°F)")
        if temp > 95:
            issues.append(f"Very hot temperature ({temp:.0f}°F)")
        
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
            'precipitation_prob': precipitation_prob,
            'temperature': temp,
            'issues': issues
        }
        
    except Exception as e:
        return {'status': 'error', 'message': f'Error assessing forecast conditions: {e}'}

def calculate_river_score(result):
    """
    Calculate an overall score for a river based on water level and wind.
    Distance is only used as a tiebreaker (added as decimal points).
    
    Priorities:
    1. Water level (60 points max) - Must be below max, ideally 30%+ above min
    2. Wind conditions (40 points max) - Anything above 10mph is annoying
    3. Distance (0.99 points max) - Only for tiebreaking
    
    Args:
        result (dict): River evaluation result
    
    Returns:
        float: Score from 0-100.99 (decimal is distance tiebreaker)
    """
    score = 0
    
    # Water level scoring (60 points max) - MOST IMPORTANT
    if result['water_status'] and result['water_status']['status'] != 'error':
        water_status = result['water_status']
        current_level = water_status.get('current_level')
        metric = water_status.get('metric', 'feet')
        
        if current_level is not None:
            # Determine which min/max values to use based on metric
            if metric == 'cfs':
                min_val = result['min_cfs']
                max_val = result['max_cfs']
            else:
                min_val = result['min_level']
                max_val = result['max_level']
            
            if min_val is not None and max_val is not None:
                # Calculate ideal range (30% above minimum)
                ideal_min = min_val + (max_val - min_val) * 0.3
                
                if current_level > max_val:
                    # Too high - dangerous
                    score += 5
                elif current_level < min_val:
                    # Too low - not paddleable  
                    score += 0
                elif current_level >= ideal_min:
                    # Perfect range (30%+ above min, below max)
                    score += 60
                else:
                    # Between min and ideal_min - paddleable but not great
                    # Linear scale from 20 to 45 points
                    progress = (current_level - min_val) / (ideal_min - min_val)
                    score += 20 + (25 * progress)
    
    # Wind scoring (40 points max) - SECOND MOST IMPORTANT
    if result['current_conditions']:
        wind_speed = result['current_conditions']['wind_speed']
        wind_gusts = result['current_conditions']['wind_gusts']
        
        if wind_speed <= 5:
            wind_score = 40  # Perfect
        elif wind_speed <= 10:
            wind_score = 35  # Good
        elif wind_speed <= 15:
            wind_score = 20  # Annoying but manageable
        elif wind_speed <= 20:
            wind_score = 10  # Pretty annoying
        else:
            wind_score = 0   # Too windy
        
        # Reduce score for high gusts
        if wind_gusts > wind_speed + 10:
            wind_score = max(0, wind_score - 10)
        
        score += wind_score
    
    # Distance tiebreaker (0.01 to 0.99 points) - TIEBREAKER ONLY
    distance_bonus = 0
    if result['distance_miles'] is not None:
        if result['distance_miles'] <= 30:
            distance_bonus = 0.99
        elif result['distance_miles'] <= 60:
            distance_bonus = 0.80
        elif result['distance_miles'] <= 100:
            distance_bonus = 0.60
        elif result['distance_miles'] <= 150:
            distance_bonus = 0.40
        elif result['distance_miles'] <= 200:
            distance_bonus = 0.20
        # Over 200 miles gets 0.01 (still better than no data)
        else:
            distance_bonus = 0.01
    else:
        distance_bonus = 0.50  # Neutral if distance unknown
    
    return round(score + distance_bonus, 2)

def get_recommendation(result):
    """Get a text recommendation based on the score and conditions."""
    score = result['overall_score']
    
    # Extract the main score (ignore distance decimal)
    main_score = int(score)
    
    if main_score >= 85:
        return "🟢 Perfect conditions!"
    elif main_score >= 70:
        return "🟢 Excellent choice!"
    elif main_score >= 50:
        return "🟡 Good option"
    elif main_score >= 30:
        return "🟠 Marginal conditions"
    elif main_score >= 15:
        return "🔴 Poor conditions"
    else:
        return "❌ Avoid"

def print_river_summary(results):
    """Print a nice summary of all river evaluations."""
    if not results:
        print("❌ No river results to display")
        return
        
    print(f"\n🏆 RIVER RECOMMENDATIONS SUMMARY")
    print("=" * 70)
    
    for i, river in enumerate(results[:5], 1):  # Top 5
        print(f"\n{i}. {river['name']} - {river['recommendation']} (Score: {river['overall_score']}/100)")
        print(f"   📍 {river['route']}")
        
        if river.get('distance_miles'):
            print(f"   🚗 Distance: {river['distance_miles']} miles")
        
        if river.get('water_status'):
            level = river['water_status'].get('current_level', 'unknown')
            metric = river['water_status'].get('metric', 'unknown')
            unit = 'CFS' if metric == 'cfs' else 'ft'
            print(f"   💧 Water Level: {level} {unit} ({river['water_status']['status']})")
        
        if river.get('current_conditions'):
            conditions = river['current_conditions']
            print(f"   🌤️  Weather: {conditions['temperature']:.0f}°F, Wind: {conditions['wind_speed']:.0f}mph {conditions['wind_direction_name']}")
            
            # Show water level details
            if river['water_status'] and river['water_status'].get('current_level'):
                current = river['water_status']['current_level']
                metric = river['water_status'].get('metric', 'feet')
                
                if metric == 'cfs':
                    min_val = river.get('min_cfs')
                    max_val = river.get('max_cfs')
                    unit = 'CFS'
                else:
                    min_val = river.get('min_level')
                    max_val = river.get('max_level')
                    unit = 'ft'
                
                if min_val and max_val:
                    ideal_min = min_val + (max_val - min_val) * 0.3
                    
                    if current >= ideal_min and current <= max_val:
                        level_status = "👍 Ideal"
                    elif current >= min_val:
                        level_status = "⚠️  Low but paddleable"
                    else:
                        level_status = "❌ Too low"
                        
                    print(f"   💧 Level: {current:.1f}{unit} {level_status} (Range: {min_val}-{max_val}{unit}, Ideal: {ideal_min:.1f}+{unit})")
        
        if river.get('issues'):
            print(f"   ⚠️  Issues: {', '.join(river['issues'])}")

def get_best_river(results):
    """Return the best river option."""
    if not results:
        return None
    
    best = results[0]
    if best['overall_score'] >= 60:
        return best
    else:
        return None

def check_rivers_today(df, home_zip, target_date=None, max_whitewater=None, max_distance=None):
    """
    Main function to check all rivers and get recommendations.
    
    Args:
        df (pandas.DataFrame): River specifications
        home_zip (str): Home ZIP code
        target_date (str, optional): Date in YYYY-MM-DD format. Defaults to today.
        max_whitewater (int, optional): Exclude rivers with whitewater >= this value.
                                       Use negative value for minimum (e.g., -3 means whitewater >= 3)
        max_distance (int, optional): Exclude rivers more than this many miles away
    
    Returns:
        list: Sorted river evaluations
    """
    from datetime import datetime, date
    
    # Handle date display
    if target_date is None:
        date_obj = date.today()
        date_display = date_obj.strftime('%A, %B %d, %Y')
        is_today = True
    else:
        if isinstance(target_date, str):
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            date_obj = target_date
        date_display = date_obj.strftime('%A, %B %d, %Y')
        is_today = date_obj == date.today()
    
    # Add filtering info to header
    filter_info = []
    if max_whitewater is not None:
        if max_whitewater < 0:
            min_whitewater = abs(max_whitewater)
            filter_info.append(f"Whitewater ≥ {min_whitewater}")
        else:
            filter_info.append(f"Whitewater < {max_whitewater}")
    if max_distance is not None:
        filter_info.append(f"Distance ≤ {max_distance} miles")
    
    print(f"🌊 River Paddling Conditions Check")
    if is_today:
        print(f"📅 {date_display} at {datetime.now().strftime('%I:%M %p')}")
    else:
        print(f"📅 {date_display}")
    
    if filter_info:
        print(f"🔍 Filters: {' | '.join(filter_info)}")
    
    # Evaluate all rivers
    results = evaluate_all_rivers(df, home_zip, target_date, max_whitewater, max_distance)
    
    # Print summary
    if results:
        print_river_summary(results)
    else:
        print("❌ No results to display")
    
    # Get best recommendation
    best = get_best_river(results) if results else None
    if best:
        print(f"\n🎯 TOP RECOMMENDATION: {best['name']}")
        print(f"   {best['recommendation']} (Score: {best['overall_score']}/100)")
        if not is_today:
            print(f"   📅 For {date_display}")
    else:
        date_context = f" for {date_display}" if not is_today else ""
        print(f"\n😞 No rivers currently meet good paddling conditions{date_context}.")
        if results:
            print(f"   Best available: {results[0]['name']} (Score: {results[0]['overall_score']}/100)")
    
    return results

def get_weekly_river_forecast(df, home_zip, max_whitewater=None, max_distance=None):
    """
    Generate a 7-day forecast for river paddling using real weather forecasts.
    
    Args:
        df (pandas.DataFrame): River specifications from CSV
        home_zip (str): Your home ZIP code for distance calculations
        max_whitewater (int, optional): Exclude rivers with whitewater >= this value.
                                       Use negative value for minimum (e.g., -3 means whitewater >= 3)
        max_distance (int, optional): Exclude rivers more than this many miles away
    
    Returns:
        list: Daily forecasts sorted by best paddling conditions
    """
    from datetime import date, timedelta
    import math
    import weather
    import usgs_water
    import pandas as pd
    
    # Add filtering info to header
    filter_info = []
    if max_whitewater is not None:
        if max_whitewater < 0:
            min_whitewater = abs(max_whitewater)
            filter_info.append(f"Whitewater ≥ {min_whitewater}")
        else:
            filter_info.append(f"Whitewater < {max_whitewater}")
    if max_distance is not None:
        filter_info.append(f"Distance ≤ {max_distance} miles")
    
    print(f"🗓️  WEEKLY RIVER PADDLING FORECAST")
    print(f"🏠 From home ZIP: {home_zip}")
    if filter_info:
        print(f"🔍 Filters: {' | '.join(filter_info)}")
    print("=" * 70)
    
    daily_forecasts = []
    
    # Get home coordinates for distance calculation
    home_lat, home_lon = weather.get_coordinates_from_zip(home_zip)
    
    for day_offset in range(1, 8):  # Tomorrow through next 7 days
        target_date = date.today() + timedelta(days=day_offset)
        day_name = target_date.strftime('%A')
        date_str = target_date.strftime('%B %d')
        
        print(f"\n📅 Analyzing {day_name}, {date_str}...")
        
        day_results = []
        excluded_count = 0
        
        for index, river in df.iterrows():
            # Apply whitewater filter first
            if max_whitewater is not None:
                if max_whitewater < 0:
                    # Negative value means minimum whitewater level
                    min_whitewater = abs(max_whitewater)
                    if river['Whitewater'] < min_whitewater:
                        excluded_count += 1
                        continue
                else:
                    # Positive value means maximum whitewater level
                    if river['Whitewater'] >= max_whitewater:
                        excluded_count += 1
                        continue
            
            # Extract CFS values if present
            min_cfs = river.get('Min_cfs')
            max_cfs = river.get('Max_cfs')
            
            # Convert to None if NaN
            if pd.isna(min_cfs):
                min_cfs = None
            if pd.isna(max_cfs):
                max_cfs = None
            
            # Initialize river result
            river_result = {
                'name': river['Name'],
                'route': river['Route'],
                'min_level': river['Min_Level'],
                'max_level': river['Max_Level'],
                'min_cfs': min_cfs,
                'max_cfs': max_cfs,
                'whitewater': river['Whitewater'],
                'distance_miles': None,
                'water_status': None,
                'weather_status': None,
                'current_conditions': None,
                'day_forecast': None,
                'score': 0
            }
            
            # Calculate distance
            if home_lat and home_lon:
                try:
                    river_lat, river_lon = weather.get_coordinates_from_zip(river['Zipcode'])
                    if river_lat and river_lon:
                        dlat = math.radians(river_lat - home_lat)
                        dlon = math.radians(river_lon - home_lon)
                        a = (math.sin(dlat/2)**2 + 
                             math.cos(math.radians(home_lat)) * math.cos(math.radians(river_lat)) * 
                             math.sin(dlon/2)**2)
                        c = 2 * math.asin(math.sqrt(a))
                        river_result['distance_miles'] = round(3959 * c, 1)
                        
                        # Apply distance filter
                        if max_distance is not None and river_result['distance_miles'] > max_distance:
                            excluded_count += 1
                            continue
                except:
                    pass
            
            # Get current water level (assume constant for forecast)
            try:
                water_result = usgs_water.check_water_level_range(
                    str(river['Gauge_ID']).zfill(8),
                    river['Min_Level'],
                    river['Max_Level'],
                    min_cfs,
                    max_cfs
                )
                river_result['water_status'] = water_result
            except Exception as e:
                print(f"   ❌ {river['Name']}: Water error = {e}")
                continue
            
            # Get weather forecast for this specific date
            try:
                weather_data = weather.get_weather_by_zip(river['Zipcode'], forecast_days=8)
                if weather_data:
                    day_forecast = weather.get_forecast_for_date(weather_data, target_date)
                    if day_forecast:
                        river_result['day_forecast'] = day_forecast
                        
                        # Convert to current_conditions format for scoring
                        current_conditions = {
                            'temperature': day_forecast['temperature'],
                            'wind_speed': day_forecast['wind_speed'],
                            'wind_direction': day_forecast['wind_direction'],
                            'wind_gusts': day_forecast['wind_gusts'],
                            'wind_direction_name': weather.get_wind_direction_name(day_forecast['wind_direction']),
                            'precipitation': day_forecast['precipitation']
                        }
                        river_result['current_conditions'] = current_conditions
                        
                        # Assess conditions
                        weather_assessment = assess_forecast_conditions(day_forecast)
                        river_result['weather_status'] = weather_assessment
                        
                        print(f"   📊 {river['Name']}: {day_forecast['temperature']:.0f}°F, {day_forecast['wind_speed']:.0f}mph, {day_forecast['precipitation_probability']:.0f}% rain")
                    else:
                        print(f"   ❌ {river['Name']}: No forecast for {target_date}")
                        continue
                else:
                    print(f"   ❌ {river['Name']}: No weather data")
                    continue
            except Exception as e:
                print(f"   ❌ {river['Name']}: Weather error = {e}")
                continue
            
            # Calculate score
            score = calculate_weekly_river_score(river_result)
            river_result['score'] = score
            
            day_results.append(river_result)
        
        if excluded_count > 0:
            print(f"   🔍 Excluded {excluded_count} rivers based on filters")
        
        # Sort rivers by score for this day
        day_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Calculate day score (average of top 2 rivers)
        if len(day_results) >= 2:
            day_score = (day_results[0]['score'] + day_results[1]['score']) / 2
        elif len(day_results) == 1:
            day_score = day_results[0]['score']
        else:
            day_score = 0
        
        daily_forecasts.append({
            'date': target_date,
            'day_name': day_name,
            'date_str': date_str,
            'day_score': day_score,
            'rivers': day_results
        })
    
    # Sort days by overall paddling quality
    daily_forecasts.sort(key=lambda x: x['day_score'], reverse=True)
    
    print(f"\n✅ Weekly forecast complete. Found {len(daily_forecasts)} days.")
    return daily_forecasts

def calculate_weekly_river_score(river_result):
    """Calculate score for weekly forecast using forecast data."""
    score = 0
    
    # Water level scoring (60 points max)
    if river_result['water_status']:
        water_status = river_result['water_status']
        current_level = water_status.get('current_level')
        metric = water_status.get('metric', 'feet')
        
        if current_level is not None:
            # Determine which min/max values to use based on metric
            if metric == 'cfs':
                min_val = river_result['min_cfs']
                max_val = river_result['max_cfs']
            else:
                min_val = river_result['min_level']
                max_val = river_result['max_level']
            
            if min_val is not None and max_val is not None:
                ideal_min = min_val + (max_val - min_val) * 0.3
                
                if current_level > max_val:
                    score += 5
                elif current_level < min_val:
                    score += 0
                elif current_level >= ideal_min:
                    score += 60
                else:
                    progress = (current_level - min_val) / (ideal_min - min_val)
                    score += 20 + (25 * progress)
    
    # Wind scoring (40 points max) using forecast data
    if river_result['day_forecast']:
        wind_speed = river_result['day_forecast']['wind_speed']
        wind_gusts = river_result['day_forecast']['wind_gusts']
        
        if wind_speed <= 5:
            wind_score = 40
        elif wind_speed <= 10:
            wind_score = 35
        elif wind_speed <= 15:
            wind_score = 20
        elif wind_speed <= 20:
            wind_score = 10
        else:
            wind_score = 0
        
        if wind_gusts > wind_speed + 10:
            wind_score = max(0, wind_score - 10)
        
        score += wind_score
    
    # Distance tiebreaker
    distance_bonus = 0
    if river_result['distance_miles'] is not None:
        if river_result['distance_miles'] <= 30:
            distance_bonus = 0.99
        elif river_result['distance_miles'] <= 60:
            distance_bonus = 0.80
        elif river_result['distance_miles'] <= 100:
            distance_bonus = 0.60
        elif river_result['distance_miles'] <= 150:
            distance_bonus = 0.40
        elif river_result['distance_miles'] <= 200:
            distance_bonus = 0.20
        else:
            distance_bonus = 0.01
    else:
        distance_bonus = 0.50
    
    return round(score + distance_bonus, 2)

def print_weekly_forecast_summary(daily_forecasts):
    """Print a comprehensive weekly forecast summary with real weather data."""
    if not daily_forecasts:
        print("❌ No forecast data to display")
        return
        
    print(f"\n🏆 BEST PADDLING DAYS (Next 7 Days)")
    print("=" * 70)
    
    for i, day in enumerate(daily_forecasts, 1):
        if day['day_score'] < 10:  # Skip really bad days
            continue
            
        day_name = day['day_name']
        date_str = day['date_str']
        rivers = day['rivers']
        
        print(f"\n{i}. {day_name}, {date_str} (Score: {day['day_score']:.1f}/100)")
        
        if len(rivers) >= 2:
            best = rivers[0]
            second = rivers[1]
            
            # Primary recommendation
            print(f"   🥇 Best: {best['name']}")
            if best['water_status']:
                level = best['water_status'].get('current_level', 'unknown')
                metric = best['water_status'].get('metric', 'feet')
                unit = 'CFS' if metric == 'cfs' else 'ft'
                print(f"      💧 Level: {level} {unit} ({best['water_status']['status']})")
            if best['day_forecast']:
                forecast = best['day_forecast']
                narrative = forecast.get('narrative', '')
                weather_text = f"🌤️  Weather: {forecast['temperature']:.0f}°F, Wind: {forecast['wind_speed']:.0f}mph, Rain: {forecast['precipitation_probability']:.0f}%"
                if narrative:
                    weather_text += f" ({narrative})"
                print(f"      {weather_text}")
            if best['distance_miles']:
                print(f"      🚗 Distance: {best['distance_miles']} miles")
            
            # Alternative recommendation with comparison
            print(f"   🥈 Alternative: {second['name']}")
            comparison = generate_forecast_comparison(best, second)
            print(f"      {comparison}")
            
        elif len(rivers) == 1:
            best = rivers[0]
            print(f"   🥇 Only option: {best['name']} (Score: {best['score']:.1f}/100)")
            if best['day_forecast']:
                forecast = best['day_forecast']
                print(f"      🌤️  Weather: {forecast['temperature']:.0f}°F, Wind: {forecast['wind_speed']:.0f}mph")
        else:
            print("   😞 No good options this day")

def generate_forecast_comparison(best_river, second_river):
    """Generate a comparison between two rivers using forecast data."""
    comparisons = []
    
    # Compare wind using forecast data
    if best_river['day_forecast'] and second_river['day_forecast']:
        best_wind = best_river['day_forecast']['wind_speed']
        second_wind = second_river['day_forecast']['wind_speed']
        
        if second_wind > best_wind + 3:
            comparisons.append(f"windier ({second_wind:.0f}mph vs {best_wind:.0f}mph)")
        elif best_wind > second_wind + 3:
            comparisons.append(f"less windy ({second_wind:.0f}mph vs {best_wind:.0f}mph)")
    
    # Compare distance
    if best_river['distance_miles'] and second_river['distance_miles']:
        best_dist = best_river['distance_miles']
        second_dist = second_river['distance_miles']
        
        if second_dist > best_dist + 15:
            comparisons.append(f"farther ({second_dist:.0f}mi vs {best_dist:.0f}mi)")
        elif best_dist > second_dist + 15:
            comparisons.append(f"closer ({second_dist:.0f}mi vs {best_dist:.0f}mi)")
    
    # Compare water levels
    if best_river['water_status'] and second_river['water_status']:
        best_status = best_river['water_status']['status']
        second_status = second_river['water_status']['status']
        
        if second_status == 'too_low' and best_status == 'good':
            comparisons.append("lower water")
        elif second_status == 'good' and best_status != 'good':
            comparisons.append("better water level")
    
    # Compare precipitation probability
    if best_river['day_forecast'] and second_river['day_forecast']:
        best_rain = best_river['day_forecast']['precipitation_probability']
        second_rain = second_river['day_forecast']['precipitation_probability']
        
        if second_rain > best_rain + 20:
            comparisons.append(f"rainier ({second_rain:.0f}% vs {best_rain:.0f}% chance)")
        elif best_rain > second_rain + 20:
            comparisons.append(f"less rain ({second_rain:.0f}% vs {best_rain:.0f}% chance)")
    
    if comparisons:
        return f"Similar option, but {', '.join(comparisons)}"
    else:
        return f"Similar conditions (Score: {second_river['score']:.1f}/100)"

def get_multiple_sites_status(sites_config):
    """
    Check water level status for multiple sites.
    
    Args:
        sites_config (list): List of dicts with keys: site_id, min_level, max_level, min_cfs, max_cfs
                            Example: [{'site_id': '03044000', 'min_level': 3.0, 'max_level': 8.0, 'min_cfs': None, 'max_cfs': None}]
    
    Returns:
        list: List of status dicts for each site
    """
    import usgs_water
    
    results = []
    
    for site_config in sites_config:
        site_id = site_config['site_id']
        min_level = site_config.get('min_level')
        max_level = site_config.get('max_level')
        min_cfs = site_config.get('min_cfs')
        max_cfs = site_config.get('max_cfs')
        
        result = usgs_water.check_water_level_range(site_id, min_level, max_level, min_cfs, max_cfs)
        result['name'] = site_config.get('name', usgs_water.get_site_name(site_id))
        results.append(result)
    
    return results

def whitewater_forecast(df, home_zip, print_summary=True):
    """
    Generate a 7-day forecast for whitewater paddling (Class III+ rapids only).
    
    Args:
        df (pandas.DataFrame): River specifications from CSV
        home_zip (str): Your home ZIP code for distance calculations
        print_summary (bool): Whether to automatically print the formatted summary
    
    Returns:
        list: Daily forecasts sorted by best paddling conditions
    """
    results = get_weekly_river_forecast(df=df, home_zip=home_zip, max_whitewater=-3)
    if print_summary:
        print_weekly_forecast_summary(results)
    return results

def casual_forecast(df, home_zip, proximity=None, print_summary=True):
    """
    Generate a 7-day forecast for casual paddling (Class II and below only).
    
    Args:
        df (pandas.DataFrame): River specifications from CSV
        home_zip (str): Your home ZIP code for distance calculations
        proximity (str, optional): "close" to limit to rivers within 30 miles
        print_summary (bool): Whether to automatically print the formatted summary
    
    Returns:
        list: Daily forecasts sorted by best paddling conditions
    """
    max_distance = 30 if proximity == "close" else None
    results = get_weekly_river_forecast(df=df, home_zip=home_zip, max_whitewater=3, max_distance=max_distance)
    if print_summary:
        print_weekly_forecast_summary(results)
    return results