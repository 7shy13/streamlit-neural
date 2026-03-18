import numpy as np
import pandas as pd
from datetime import timedelta

def compute_prior_elo(market_value, beta_0=1000, beta_1=100):
    """
    Computes a 'Wisdom of the Crowds' Prior Elo rating from a team's Market Value.
    
    Args:
        market_value (float): Point-in-time market value in millions of EUR.
        beta_0 (float): Base prior Elo intercept.
        beta_1 (float): Logarithmic scaling factor.
        
    Returns:
        float: Calculated Prior Elo (mu_prior).
    """
    # Prevent negative or zero logs 
    mv_safe = np.maximum(market_value, 1.0)
    mu_prior = beta_0 + (beta_1 * np.log(mv_safe))
    return mu_prior

def calculate_anchor_weight(match_week, kappa_0=0.75, decay_rate=0.25):
    """
    Calculates the exponential decay of the Prior Market Value Anchor over match weeks.
    As the season progresses, the real on-pitch performance trumps paper value.
    
    Args:
        match_week (int): The current round/week of the season (1-indexed).
        kappa_0 (float): Initial weight of the anchor at Week 1.
        decay_rate (float): Rate at which the anchor's importance fades.
        
    Returns:
        float: The anchor weight kappa_w.
    """
    week_safe = np.maximum(0, match_week - 1)
    kappa_w = kappa_0 * np.exp(-decay_rate * week_safe)
    return kappa_w

def join_tm_point_in_time(matches_df, tm_df):
    """
    A robust temporal cross-join to prevent Lookahead Bias when merging
    Transfermarkt valuations into historical match data.
    
    Args:
        matches_df (pd.DataFrame): Must contain 'MatchDate', 'HomeTeam', 'AwayTeam'
        tm_df (pd.DataFrame): Must contain 'Team', 'ValuationDate', 'MarketValue'
        
    Returns:
        pd.DataFrame: matches_df merged with Point-in-Time HomeMarketValue and AwayMarketValue
    """
    # Sort both just to be safe
    matches = matches_df.sort_values('MatchDate')
    tm_vals = tm_df.sort_values('ValuationDate')
    
    # Use pandas merge_asof: exact backward match
    # Joins the latest valuation WHERE ValuationDate <= MatchDate
    merged = pd.merge_asof(
        matches.sort_values('MatchDate'),
        tm_vals.rename(columns={'Team': 'HomeTeam', 'MarketValue': 'HomeMarketValue'}),
        left_on='MatchDate',
        right_on='ValuationDate',
        by='HomeTeam',
        direction='backward' # Strictly looks backward
    ).drop(columns=['ValuationDate'], errors='ignore')
    
    merged = pd.merge_asof(
        merged,
        tm_vals.rename(columns={'Team': 'AwayTeam', 'MarketValue': 'AwayMarketValue'}),
        left_on='MatchDate',
        right_on='ValuationDate',
        by='AwayTeam',
        direction='backward'
    ).drop(columns=['ValuationDate'], errors='ignore')
    
    return merged
