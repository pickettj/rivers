import pandas as pd
import re

def parse_class_range(class_str):
    """
    Parse a class string and return (min_class, max_class) as integers.
    Letters (A, B, C) = 0, Roman numerals I-VI = 1-6
    
    Examples:
    'A' -> (0, 0)
    'I-II' -> (1, 2)
    'III-IV' -> (3, 4)
    'V-VI' -> (5, 6)
    'C-I' -> (0, 1)
    """
    if pd.isna(class_str) or class_str == '':
        return None, None
    
    # Clean up the string
    class_str = str(class_str).strip()
    
    # Mapping for conversion
    class_map = {
        'A': 0, 'B': 0, 'C': 0,
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6
    }
    
    # Split on hyphen if present
    if '-' in class_str:
        parts = class_str.split('-')
        min_part = parts[0].strip()
        max_part = parts[1].strip()
        
        min_class = class_map.get(min_part)
        max_class = class_map.get(max_part)
        
        return min_class, max_class
    else:
        # Single class
        single_class = class_map.get(class_str)
        return single_class, single_class

def river_class(df, class_range):
    """
    Filter rivers by difficulty class range.
    
    Args:
        df (pandas.DataFrame): River data with 'Class' column
        class_range (tuple): (min_class, max_class) where both are integers 0-6
                            0=A/B/C, 1=I, 2=II, 3=III, 4=IV, 5=V, 6=VI
    
    Returns:
        pandas.DataFrame: Filtered dataframe
    
    Examples:
        river_class(df, (2, 3))  # Returns Class II-III ranges
        river_class(df, (0, 2))  # Returns up to Class II
        river_class(df, (3, 6))  # Returns Class III and above
        river_class(df, (0, 0))  # Returns only flat water (A/B/C)
    """
    min_class, max_class = class_range
    
    def matches_criteria(class_str):
        parsed_min, parsed_max = parse_class_range(class_str)
        
        if parsed_min is None or parsed_max is None:
            return False
        
        # Check if the range overlaps with our criteria
        if parsed_max < min_class or parsed_min > max_class:
            return False
        
        return True
    
    mask = df['Class'].apply(matches_criteria)
    return df[mask]

