import numpy as np
import pandas as pd

def calculate_player_impact(lambda_base, delta_xt, w_pos=1.0, phi=0.8, max_penalty=0.60):
    """
    Calculates the adjusted goal expectancy (lambda) given missing player's xT/WAR.
    Uses a bounded exponential decay function based on the Sandbox validation.
    
    Args:
        lambda_base (float or pd.Series): Base goal expectancy from the Poisson/Elo model.
        delta_xt (float or pd.Series): The lost Expected Threat or WAR. Must be >= 0 (loss).
        w_pos (float): Weight of the position. >1 for critical playmakers/finishers.
        phi (float): Non-linear shock multiplier (default 0.8 for damping).
        max_penalty (float): The maximum allowed drop in lambda (e.g. 0.60 means team keeps at least 60% of original xG).
        
    Returns:
        float or pd.Series: The adjusted lambda, capped to prevent >40% loss.
    """
    # Ensure delta_xt > 0
    delta_xt = np.maximum(0, delta_xt)
    
    # Exponential decay but damped with phi=0.8
    decay_factor = np.exp(-phi * w_pos * delta_xt)
    
    # Apply hard floor (max penalty cap)
    decay_factor = np.maximum(decay_factor, max_penalty)
    
    lambda_adj = lambda_base * decay_factor
    return lambda_adj

def calculate_opponent_boost(lambda_opp_base, def_delta_xt, w_pos=1.0, phi=0.5, max_boost=1.35):
    """
    Calculates the boost to the OPPONENT's goal expectancy when a team is missing a key defender.
    Now bounded to prevent catastrophic >300% exponentiation.
    
    Args:
        lambda_opp_base (float or pd.Series): Opponent's base goal expectancy.
        def_delta_xt (float or pd.Series): The lost defensive impact.
        w_pos (float): Weight of the defensive position.
        phi (float): Damped exponential growth.
        max_boost (float): The maximum allowed multiplier (e.g. 1.35 means max +35% xG to opp).
        
    Returns:
        float or pd.Series: Boosted opponent lambda safely capped.
    """
    def_delta_xt = np.maximum(0, def_delta_xt)
    
    # Exponential growth on the opponent's lambda (Damped)
    boost_factor = np.exp(phi * w_pos * def_delta_xt)
    
    # Safely cap the growth! A single missing CB shouldn't triple the opponent's xG.
    boost_factor = np.minimum(boost_factor, max_boost)
    
    lambda_opp_adj = lambda_opp_base * boost_factor
    return lambda_opp_adj
