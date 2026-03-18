import pandas as pd
import numpy as np
import json
import os
import sys

# Import our quant models
from base_elo_engine import DynamicEloEngine
from build_mock_db import get_base_mv
from pricing_engine import calculate_1x2_probs

def warm_up_elo_engine():
    """
    Simulates the entire T1_ALL.csv time machine up to the present day to get 
    the EXACT current Elo ratings for all teams. Takes <1 second.
    """
    print("[SYSTEM] Warming up Dynamic Elo Engine with 6000 historical matches...")
    # Use absolute path resolution relative to the script's location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, '..', 'T1_ALL.csv')
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("[ERROR] T1_ALL.csv not found in parent directory.")
        sys.exit(1)
        
    # We don't care about dates here, just the chronological order of results
    df = df.reset_index(drop=True)
    
    elo = DynamicEloEngine(k_factor=20, hfa=60, base_elo=1500, c_scale=0.002)
    
    for _, row in df.iterrows():
        home_team = row['HomeTeam']
        away_team = row['AwayTeam']
        
        # Use our static tier map for Bayesian Priors (as done in Phase 5)
        home_mv = get_base_mv(home_team)
        away_mv = get_base_mv(away_team)
        
        elo.update_ratings(home_team, away_team, row['FTHG'], row['FTAG'], home_mv, away_mv)
        
    print("[SYSTEM] Elo Engine Warmed Up to Present Day.")
    return elo

def load_live_market_values():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'live_market_values.json')
    
    if not os.path.exists(json_path):
        print("[WARNING] live_market_values.json not found. Run 'python tm_scraper.py' first!")
        return {}
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_live_predictor():
    print("\n" + "="*50)
    print(" >>> ANTIGRAVITY LIVE PREDICTOR BOT (FINANCIAL PROXY) <<<")
    print("="*50)
    
    elo = warm_up_elo_engine()
    live_mvs = load_live_market_values()
    
    if not live_mvs:
        print("[ERROR] No live market values loaded. Falling back to static tiers.")
        
    print("\n--- CANLI MAÇ VERİLERİNİ GİRİN ---")
    home_team = input("Ev Sahibi Takım İsmi (Örn: Galatasaray): ").strip()
    away_team = input("Deplasman Takımı İsmi (Örn: Fenerbahce): ").strip()
    
    if home_team not in elo.ratings:
        print(f"[UYARI] '{home_team}' veritabanında yok. Base rating (1500) ile başlıyor.")
    if away_team not in elo.ratings:
        print(f"[UYARI] '{away_team}' veritabanında yok. Base rating (1500) ile başlıyor.")
        
    # Get current Squad Values
    total_home_mv = live_mvs.get(home_team, get_base_mv(home_team))
    total_away_mv = live_mvs.get(away_team, get_base_mv(away_team))
    
    print(f"\n{home_team} Güncel Piyasa Değeri: €{total_home_mv:.2f}m")
    print(f"{away_team} Güncel Piyasa Değeri: €{total_away_mv:.2f}m")
    
    # Get Injuries
    print("\n--- SAKATLIK VE CEZA BİLDİRİMİ (FİNANSAL DÜŞÜŞ) ---")
    missing_h = float(input(f"{home_team} için eksik oyuncuların TOPLAM Piyasa Değeri (€ Milyon): ") or "0")
    missing_a = float(input(f"{away_team} için eksik oyuncuların TOPLAM Piyasa Değeri (€ Milyon): ") or "0")
    
    # Financial Drop Proxy Logic
    # 70% max translation: Losing your ENTIRE squad reduces your xG by 70%.
    drop_h = min(1.0, missing_h / max(0.1, total_home_mv))
    drop_a = min(1.0, missing_a / max(0.1, total_away_mv))
    
    decay_h = max(0.60, 1.0 - (drop_h * 0.70))
    decay_a = max(0.60, 1.0 - (drop_a * 0.70))
    
    print(f"\n{home_team} xG Kaybı Çarpanı: %{((1.0 - decay_h)*100):.1f} düşüş")
    print(f"{away_team} xG Kaybı Çarpanı: %{((1.0 - decay_a)*100):.1f} düşüş")
    
    # Compute Lambdas
    base_lh, base_la = elo.get_base_lambdas(home_team, away_team, total_home_mv, total_away_mv)
    final_lh = base_lh * decay_h
    final_la = base_la * decay_a
    
    # Calculate Poisson Probabilities
    prob_h, prob_d, prob_a = calculate_1x2_probs(final_lh, final_la, rho=0.15)
    
    fair_odds_h = 1 / prob_h if prob_h > 0 else 999.0
    fair_odds_d = 1 / prob_d if prob_d > 0 else 999.0
    fair_odds_a = 1 / prob_a if prob_a > 0 else 999.0
    
    print("\n--- QUANTS MODEL 'SAF' (FAIR) ORANLARI ---")
    print(f"MS 1: {fair_odds_h:.2f} (%{prob_h*100:.1f})")
    print(f"MS X: {fair_odds_d:.2f} (%{prob_d*100:.1f})")
    print(f"MS 2: {fair_odds_a:.2f} (%{prob_a*100:.1f})")
    
    # Iddaa Odds
    print("\n--- GÜNCEL İDDAA (BOOKMAKER) ORANLARINI GİRİN ---")
    iddaa_h = float(input("MS 1: ") or "0")
    iddaa_d = float(input("MS X: ") or "0")
    iddaa_a = float(input("MS 2: ") or "0")
    
    print("\n" + "*"*40)
    print(" >>> VALUE BET ANALİZİ (EXPECTED VALUE) <<<")
    print("*"*40)
    
    def check_value(name, fair, odd, prob):
        if odd <= 0:
            return
        ev = (odd * prob) - 1.0
        if ev > 0.05: # Minimum 5% Edge
            print(f">>> [VALUE BET DETECTED] {name} | İddaa: {odd:.2f} | Pazar Olması Gereken: {fair:.2f} | Beklenen Kâr (EV): +%{(ev*100):.1f} (+)")
        else:
            print(f">>> {name} | Kârlı Değil (EV: %{(ev*100):.1f}) (-)")

    check_value("MS 1", fair_odds_h, iddaa_h, prob_h)
    check_value("MS X", fair_odds_d, iddaa_d, prob_d)
    check_value("MS 2", fair_odds_a, iddaa_a, prob_a)
    
    print("\nAnaliz tamamlandı. Yeni takım aramak için scripti tekrar çalıştırın.")

if __name__ == "__main__":
    run_live_predictor()
