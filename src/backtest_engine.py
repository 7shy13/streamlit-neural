import json
import os
import datetime
from naming_utils import FluidMatcher

# File paths
BETS_FILE = "placed_bets.json"
STATS_FILE = "stats.json"

class BacktestEngine:
    def __init__(self):
        self.bets = self._load_json(BETS_FILE, [])
        self.stats = self._load_json(STATS_FILE, {
            "total_staked": 0.0,
            "total_return": 0.0,
            "net_profit": 0.0,
            "roi": 0.0,
            "hit_rate": 0.0,
            "wins": 0,
            "losses": 0,
            "total_bets": 0,
            "last_sync": ""
        })
        self.matcher = FluidMatcher()

    def _load_json(self, path, default):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default

    def _save_json(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_placed_bet(self, bet_data):
        """
        bet_data: {home, away, outcome, odd, ev, fair, prob, match_time, league}
        """
        # Avoid duplicates
        uid = f"{bet_data['home']}_{bet_data['away']}_{bet_data['outcome']}_{bet_data['match_time']}"
        if any(b.get('uid') == uid for b in self.bets):
            return False
            
        bet_entry = {
            "uid": uid,
            "home": bet_data['home'],
            "away": bet_data['away'],
            "outcome": bet_data['outcome'],
            "odd": float(bet_data['odd']),
            "ev": float(bet_data['ev']),
            "match_time": bet_data['match_time'],
            "league": bet_data['league'],
            "status": "PENDING",
            "result": None,
            "pnl": 0.0,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.bets.append(bet_entry)
        self._save_json(BETS_FILE, self.bets)
        return True

    def settle_bets(self, goal_results):
        """
        goal_results: list of {home, away, score_h, score_a}
        """
        settled_count = 0
        for bet in self.bets:
            if bet['status'] != 'PENDING':
                continue
            
            # Find matching result
            match_res = None
            bet_home_simple = FluidMatcher.simplify(bet['home'])
            bet_away_simple = FluidMatcher.simplify(bet['away'])
            
            for gr in goal_results:
                gr_home_simple = FluidMatcher.simplify(gr['home'])
                gr_away_simple = FluidMatcher.simplify(gr['away'])
                
                if bet_home_simple == gr_home_simple and bet_away_simple == gr_away_simple:
                    match_res = gr
                    break
            
            if match_res:
                sh = match_res['score_h']
                sa = match_res['score_a']
                actual = "MS 1" if sh > sa else ("MS 2" if sa > sh else "MS X")
                
                is_win = (bet['outcome'] == actual)
                bet['status'] = "SETTLED"
                bet['result'] = f"{sh}-{sa}"
                bet['pnl'] = (bet['odd'] - 1.0) if is_win else -1.0
                
                # Update Stats
                self.stats['total_staked'] += 1.0
                self.stats['total_return'] += (bet['odd'] if is_win else 0.0)
                if is_win: self.stats['wins'] += 1
                else: self.stats['losses'] += 1
                
                settled_count += 1
                
        if settled_count > 0:
            self._update_aggregate_stats()
            self._save_json(BETS_FILE, self.bets)
            self._save_json(STATS_FILE, self.stats)
            
        return settled_count

    def _update_aggregate_stats(self):
        s = self.stats
        s['total_bets'] = s['wins'] + s['losses']
        s['net_profit'] = round(s['total_return'] - s['total_staked'], 2)
        if s['total_staked'] > 0:
            s['roi'] = round((s['net_profit'] / s['total_staked']) * 100, 2)
            s['hit_rate'] = round((s['wins'] / s['total_bets']) * 100, 2)
        s['last_sync'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_summary(self):
        return self.stats

if __name__ == "__main__":
    # Test
    be = BacktestEngine()
    print("Stats:", be.get_summary())
