import sys
import os
import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from backtest_engine import BacktestEngine
from goal_results_scraper import get_results_for_date

def test_settlement():
    print("=" * 60)
    print("ANTIGRAVITY Verification: Settlement Pipeline")
    print("=" * 60)
    
    be = BacktestEngine()
    
    # 1. Check current pending bets
    pending = [b for b in be.bets if b['status'] == 'PENDING']
    print(f"Initial Pending Bets: {len(pending)}")
    for p in pending:
        print(f" - {p['home']} vs {p['away']} | Goal: {p['outcome']} | Odd: {p['odd']}")
        
    # 2. Get results for March 17 (Yesterday)
    # The browser research confirmed data exists for this day.
    target_date = "2026-03-17"
    results = get_results_for_date(target_date)
    
    if not results:
        print("Error: No results found for 2026-03-17. Check internet/scraper.")
        return
        
    # 3. Settle
    settled = be.settle_bets(results)
    print(f"\nSuccessfully settled {settled} bets.")
    
    # 4. Final Stats
    stats = be.get_summary()
    print("\n" + "=" * 60)
    print(f"FINAL STATS (Backtest)")
    print(f"  Total Bets: {stats['total_bets']}")
    print(f"  Wins:       {stats['wins']}")
    print(f"  Losses:     {stats['losses']}")
    print(f"  ROI:        {stats['roi']}%")
    print(f"  Net Profit: {stats['net_profit']} units")
    print("=" * 60)

if __name__ == "__main__":
    test_settlement()
