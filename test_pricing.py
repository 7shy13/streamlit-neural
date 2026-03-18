import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pricing_engine import pricing_engine_pipeline

def run_sanity_checks():
    """
    Test the pricing engine with extreme Contextual Alpha parameters to ensure
    no imaginary numbers or negative lambda values occur.
    """
    print("--- RUNNING PHASE 2 CONTEXTUAL INTEGRATION SANITY CHECKS ---")
    print("Test 1: Normal Match (No extreme context)")
    normal_context = {
        'home_delta_xt': 0.0, 'home_fatigue_gamma': 1.0, 'home_motivation_m': 1.0,
        'away_delta_xt': 0.0, 'away_fatigue_gamma': 1.0, 'away_motivation_m': 1.0
    }
    res_normal = pricing_engine_pipeline(1.5, 1.2, normal_context)
    print("Normal Odds:", {k: round(v, 2) for k, v in res_normal.items()})

    print("\nTest 2: Extreme Star Player Missing (High Home xT Loss)")
    missing_star_context = {
        'home_delta_xt': 1.2, # Very high expected threat loss
        'home_fatigue_gamma': 1.0, 'home_motivation_m': 1.0,
    }
    try:
        res_star = pricing_engine_pipeline(1.5, 1.2, missing_star_context)
        print("Missing Star Odds (Should be valid, Home lambda dropped):")
        print({k: round(v, 2) for k, v in res_star.items()})
        assert res_star['Adj_Lambda_H'] > 0
    except Exception as e:
        print(f"FAILED Test 2: {e}")

    print("\nTest 3: Extreme Fatigue & Zero Motivation (Away Team Penalty)")
    extreme_fatigue_context = {
        'away_delta_xt': 0.0, 
        'away_fatigue_gamma': 0.5, # 50% lambda cut due to 1 day rest 
        'away_motivation_m': 0.8,  # Relegated team
    }
    try:
        res_fatigue = pricing_engine_pipeline(1.5, 1.2, extreme_fatigue_context)
        print("Extreme Fatigue Odds (Should be valid, Away lambda dropped):")
        print({k: round(v, 2) for k, v in res_fatigue.items()})
        assert res_fatigue['Adj_Lambda_A'] > 0
    except Exception as e:
        print(f"FAILED Test 3: {e}")
        
    print("\nAll sanity checks passed successfully.")

if __name__ == "__main__":
    run_sanity_checks()
