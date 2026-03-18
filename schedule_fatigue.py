import numpy as np
import pandas as pd

def calculate_adjusted_rest(rest_days, travel_km=0, travel_weight=1.0):
    """
    Calculates Travel-Adjusted Rest Days for Schedule Fatigue determination.
    
    Args:
        rest_days (int/float): Raw days between previous match and current match kickoff.
        travel_km (float): Geographical distance traveled from previous match location.
        travel_weight (float): The penalty per 1000km traveled.
        
    Returns:
        float: Effective rest days.
    """
    # E.g., traveling 3000km shaves off ~3 days of rest if weight = 1.0
    travel_penalty = (travel_km / 1000.0) * travel_weight
    
    r_adj = rest_days - travel_penalty
    return np.maximum(0, r_adj) # Can't have less than 0 rest

def calculate_fatigue_penalty(r_adj, tau=0.5, max_penalty=0.75):
    """
    Calculates the Fatigue Penalty multiplier (gamma) for a team's goal expectancy.
    A team that rests >= 4 days suffers NO penalty (gamma = 1.0).
    A team that rests < 3 days suffers exponential decay (gamma < 1.0),
    but the decay is strictly capped to prevent unrealistic lambda collapse.
    
    Args:
        r_adj (float): Travel-Adjusted Rest Days.
        tau (float): Sensitivity to fatigue.
        max_penalty (float): Maximum drop allowed (e.g. 0.75 means max 25% drop).
        
    Returns:
        float: The gamma multiplier applied to lambda.
    """
    days_short = np.maximum(0, 4.0 - r_adj)
    gamma = np.exp(-tau * days_short)
    
    # Safely cap the penalty so a team doesn't drop to 10% xG just from fatigue
    gamma = np.maximum(gamma, max_penalty)
    
    return gamma

def compute_expanding_motivation_z(df_standings, team, current_week, alpha_m=0.05):
    """
    Computes Motivation Z-Score strictly using an Expanding Window.
    Prevents Lookahead Bias by ignoring the end-of-season table outcomes.
    
    Args:
        df_standings (pd.DataFrame): League matches/standings up to week N-1. 
                                     Must contain pts, goals, team.
        team (str): The team being calculated.
        current_week (int): The current Matchweek.
        alpha_m (float): Sensitivity of lambda boost to motivation.
        
    Returns:
        float: Motivation boost multiplier (M). 1.0 means no extra boost.
    """
    # Simulate partial points thresholds (relegation, title) based purely on history up to week N-1
    # For a real implementation, you'd calculate dynamically if a team is near the top or bottom cutoff.
    # We stub this logic conceptually for the structural math framework:
    
    # Example logic: Assume Z is higher as you near 1st place or 16th place (relegation border)
    # df_history = df_standings[df_standings['MatchWeek'] < current_week]
    # ... logic computing expanding Z ...
    
    z_mod_stub = 0.0 # Stub for purely architectural layout; normally computed per-week dynamically
    
    M = 1.0 + (alpha_m * z_mod_stub)
    return M
