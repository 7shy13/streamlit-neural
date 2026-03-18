import pandas as pd
import numpy as np
from datetime import datetime
from pricing_engine import pricing_engine_pipeline
from base_elo_engine import DynamicEloEngine
from api_adapter import ContextAPIAdapter

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, format="%d/%m/%Y")
    except:
        return pd.to_datetime(date_str)

def process_historical_brier():
    """
    Reads T1_ALL.csv, applies dummy Contextual adjustments (as placeholders 
    for the real xT and Fatigue data), and generates Fair Odds using the 
    Phase 2 Bivariate Poisson Pricing Engine.
    """
    print("Loading T1_ALL.csv...")
    try:
        df = pd.read_csv("T1_ALL.csv")
    except FileNotFoundError:
        print("Error: T1_ALL.csv not found.")
        return

    # Basic cleaning
    df['Date'] = df['Date'].apply(parse_date)
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Initialize Engines
    elo_engine = DynamicEloEngine(k_factor=20, hfa=60, base_elo=1500)
    api_adapter = ContextAPIAdapter(mode='mock')  # Toggles to 'production' when APIs ready
    
    results = []
    
    print(f"Processing {len(df)} matches through the Phase 1 & 2 Pricing Engine...")
    
    for idx, row in df.iterrows():
        home_team = row['HomeTeam']
        away_team = row['AwayTeam']
        
        # PREFETCH ANCHORS: Market Values act as the mean-reverting anchor for the Elo Prior
        home_mv_data = api_adapter.fetch_market_value(home_team, row['Date'])
        away_mv_data = api_adapter.fetch_market_value(away_team, row['Date'])
        home_mv = home_mv_data.get("total_value_eur_m", 0.0)
        away_mv = away_mv_data.get("total_value_eur_m", 0.0)
        
        # PREDICTION PHASE: Get Phase 1 Base Lambdas BEFORE the match occurs
        base_lh, base_la = elo_engine.get_base_lambdas(home_team, away_team, home_mv, away_mv)
        
        # PREDICTION PHASE 2: Fetch Contextual Delta from APIs
        home_context = api_adapter.get_contextual_modifiers(str(idx), home_team, row['Date'])
        away_context = api_adapter.get_contextual_modifiers(str(idx), away_team, row['Date'])
        
        home_xt_loss = home_context["xt_loss_modifier"]
        away_xt_loss = away_context["xt_loss_modifier"]
        
        # Note: Fatigue API returns "Rest Days", but sandbox decay logic expects a "Fatigue Pct (0-100)".
        # In a real model, we use the lambda curve `exp(-tau * max(0, 4 - rest_days))` from `schedule_fatigue.py`.
        # For pipeline integration, we'll map rest days < 4 to an approximate 0-25% drop to match sandbox scale.
        home_fatigue = max(0, (4.0 - home_context["rest_days_modifier"]) * 6.25) # 4 days = 0% penalty, 0 days = 25% penalty
        away_fatigue = max(0, (4.0 - away_context["rest_days_modifier"]) * 6.25)
        
        # Motivation Multiplier (e.g. +5% xG boost per 1.0 Z-Score standard deviation, capped at +/- 15%)
        home_motiv_mult = min(1.15, max(0.85, 1.0 + (home_context["motivation_z_modifier"] * 0.05)))
        away_motiv_mult = min(1.15, max(0.85, 1.0 + (away_context["motivation_z_modifier"] * 0.05)))
        
        # Generate Fair Odds using Phase 2
        from pricing_engine import calculate_1x2_probs, calculate_asian_handicap_fair_odds
        
        # Sandbox capped decay logic
        # Max penalty bounded at 0.60 (40% drop limit)
        decay_h = max(0.60, np.exp(-0.8 * home_xt_loss)) * (1.0 - (home_fatigue / 100.0)) * home_motiv_mult
        decay_a = max(0.60, np.exp(-0.8 * away_xt_loss)) * (1.0 - (away_fatigue / 100.0)) * away_motiv_mult
        
        final_lh = base_lh * decay_h
        final_la = base_la * decay_a
        
        p1, px, p2 = calculate_1x2_probs(final_lh, final_la, rho=0.0087)
        
        # Calculate Multi-Class Brier Score
        actual_outcome = [0, 0, 0] # [1, X, 2]
        if row['FTR'] == 'H': actual_outcome[0] = 1
        elif row['FTR'] == 'D': actual_outcome[1] = 1
        else: actual_outcome[2] = 1
            
        brier = ((p1 - actual_outcome[0])**2 + 
                 (px - actual_outcome[1])**2 + 
                 (p2 - actual_outcome[2])**2)
        
        results.append({
            'Date': row['Date'],
            'Home': row['HomeTeam'],
            'Away': row['AwayTeam'],
            'FT': f"{row['FTHG']}-{row['FTAG']}",
            'Base_LH': round(base_lh, 2),
            'Adj_LH': round(final_lh, 2),
            'Prob_1': round(p1, 3),
            'Prob_X': round(px, 3),
            'Prob_2': round(p2, 3),
            'Brier': brier
        })
        
        # UPDATE PHASE: Update Elo ratings using actual match results
        # This guarantees NO LOOKAHEAD BIAS. Match N informs Match N+1.
        elo_engine.update_ratings(home_team, away_team, row['FTHG'], row['FTAG'], home_mv, away_mv)
        
    res_df = pd.DataFrame(results)
    avg_brier = res_df['Brier'].mean()
    
    print("\n--- PHASE 2 PIPELINE RESULTS ---")
    print(f"Total Matches Processed: {len(res_df)}")
    print(f"Overall Multi-class Brier Score: {avg_brier:.4f}")
    
    if avg_brier < 0.54:
        print("SUCCESS: Target Brier (< 0.54) achieved! Leak-free logic holding.")
    else:
        print("WARNING: Brier Score >= 0.54. Phase 1 Base Lambdas need recalibrating.")
        
    # Save the pipeline output
    res_df.to_csv("Phase2_Pricing_Output.csv", index=False)
    print("Exported results to 'src/Phase2_Pricing_Output.csv'")

if __name__ == "__main__":
    process_historical_brier()
