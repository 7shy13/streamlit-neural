import itertools
import numpy as np
import time

def calculate_kelly_stake(ev, odd, bankroll, fraction=0.15, cap=0.05):
    """
    Calculates the stake based on Fractional Kelly and a Bankroll Cap.
    Stake = Bankroll * fraction * (EV / (Odd - 1))
    """
    if ev <= 0 or odd <= 1:
        return 0
    
    # Kelly Formula: (bp - q) / b  where b is odd-1
    # Simplified: EV / (Odd - 1)
    kelly_b = odd - 1
    raw_kelly_percentage = ev / kelly_b
    
    proposed_percentage = raw_kelly_percentage * fraction
    stake = bankroll * proposed_percentage
    
    # Apply hard cap (5% of bankroll) and minimum (5 units)
    max_stake = bankroll * cap
    final_stake = max(5, min(stake, max_stake))
    
    return round(float(final_stake), 2)

def build_system_coupon(results, bankroll=1000):
    """
    Builds a single optimized system coupon from analysis results.
    1. Filter and sort by EV.
    2. Select top 4 unique matches.
    3. Determine system type (Full or n-1).
    4. Calculate cumulative properties.
    """
    # 1. Get all value bets across all matches
    all_value_bets = []
    for r in results:
        # Req #1: Filter by time (next 4 days only)
        match_time = r.get('match_time', 0)
        now = time.time()
        if match_time > 0 and (match_time - now) > (4 * 24 * 3600):
            continue # Too far in the future
        if match_time > 0 and (match_time < now - 3600):
            continue # Already started/finished (buffer 1hr)
            
        for vb in r.get('value_bets', []):
            if vb.get('is_value'):
                # Add match context to the bet
                all_value_bets.append({
                    "home": r['home'],
                    "away": r['away'],
                    "outcome": vb['outcome'],
                    "iddaa_odd": vb['iddaa_odd'],
                    "fair_odd": vb['fair_odd'],
                    "prob": vb['prob'] / 100.0,
                    "ev": vb['ev'],
                    "match_id": r.get('match_id', f"{r['home']}-{r['away']}"),
                    "match_time": match_time
                })
    
    # Sort by EV descending
    all_value_bets.sort(key=lambda x: x['ev'], reverse=True)
    
    # Select top 4 unique matches
    selected_bets = []
    used_matches = set()
    for bet in all_value_bets:
        m_key = bet['match_id']
        if m_key not in used_matches:
            selected_bets.append(bet)
            used_matches.add(m_key)
        if len(selected_bets) >= 4:
            break
            
    n = len(selected_bets)
    if n < 2:
        return None  # Need at least 2 matches for a coupon
        
    is_full_system = n <= 3
    k = n if is_full_system else n - 1  # 2/2, 3/3, or 3/4
    
    # Calculate System EV and Stats
    # For a system k/n, the number of combinations is C(n, k)
    indices = list(range(n))
    combinations = list(itertools.combinations(indices, k))
    num_combos = len(combinations)
    
    total_expected_return = 0
    total_odd_sum = 0
    
    # We assume equal stake per combination (Standard System Bet)
    # Unit Stake = 1.0 (Total Stake = num_combos)
    for combo in combinations:
        combo_odd = 1.0
        combo_prob = 1.0
        for idx in combo:
            combo_odd *= selected_bets[idx]['iddaa_odd']
            combo_prob *= selected_bets[idx]['prob']
        
        total_expected_return += (combo_odd * combo_prob)
        total_odd_sum += combo_odd
        
    system_avg_odd = total_odd_sum / num_combos
    system_total_ev = (total_expected_return / num_combos) - 1.0
    
    if system_total_ev <= 0:
        return None # No value in the combination
        
    # Calculate Stake
    # Note: For Kelly in systems, we use the average odd and total EV as a proxy
    stake = calculate_kelly_stake(system_total_ev, system_avg_odd, bankroll, fraction=0.15)
    
    return {
        "type": f"{k}/{n} System",
        "legs": selected_bets,
        "num_combinations": num_combos,
        "avg_odd": round(system_avg_odd, 2),
        "total_ev": round(system_total_ev, 4),
        "suggested_stake": stake,
        "is_full_system": is_full_system
    }
