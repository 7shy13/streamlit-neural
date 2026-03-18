import json
import sqlite3
import numpy as np
from datetime import datetime

class ContextAPIAdapter:
    """
    Adapter Pattern for connecting the Bivariate Poisson Pricing Engine 
    to External Data Sources (SQL databases or JSON APIs like Sportmonks/Wyscout).
    
    This module enforces strict Data Contracts to ensure the Quant Model
    receives exactly the data shapes it expects.
    """
    
    def __init__(self, mode='mock', api_keys=None, db_path='context_data.db'):
        """
        mode: 'mock' for testing architecture, 'production' for real SQL/API hits.
        """
        self.mode = mode
        self.api_keys = api_keys or {}
        self.db_path = db_path
        
    def _fallback_json(self, data_type):
        """Returns safe default fallback values if an API call fails."""
        fallbacks = {
            'player_impact': {"missing_players": [], "total_xT_loss": 0.0},
            'fatigue': {"rest_days": 7.0, "travel_km": 0.0, "adjusted_rest": 7.0},
            'market_value': {"team_id": "Unknown", "date": "2023-01-01", "total_value_eur_m": 100.0},
            'motivation': {"points_to_title": 99, "points_to_relegation": 99, "z_score": 0.0}
        }
        return fallbacks.get(data_type, {})

    def fetch_player_impact(self, match_id, team_id, match_date):
        """
        DATA CONTRACT (Expected JSON):
        {
            "match_id": str,
            "team_id": str,
            "missing_players": [{"id": str, "name": str, "xT_90": float}],
            "total_xT_loss": float
        }
        """
        if self.mode == 'mock':
            if np.random.random() < 0.15:
                xt_loss = round(np.random.uniform(0.2, 0.8), 2)
                return {
                    "match_id": match_id,
                    "team_id": team_id,
                    "missing_players": [{"id": "P123", "name": "Star Striker", "xT_90": xt_loss}],
                    "total_xT_loss": xt_loss
                }
            return self._fallback_json('player_impact')
            
        elif self.mode == 'production':
            # CONNECT TO SQLITE DATABASE
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT missing_player_id, xt_loss_90 FROM player_impact WHERE match_id=? AND team_id=?", 
                    (match_id, team_id)
                )
                rows = cursor.fetchall()
                conn.close()
                
                if not rows:
                    return self._fallback_json('player_impact')
                    
                total_loss = sum(r[1] for r in rows)
                players = [{"id": r[0], "name": "Unknown", "xT_90": r[1]} for r in rows]
                
                return {
                    "match_id": match_id,
                    "team_id": team_id,
                    "missing_players": players,
                    "total_xT_loss": total_loss
                }
            except sqlite3.Error:
                return self._fallback_json('player_impact')

    def fetch_fixture_fatigue(self, match_id, team_id, current_match_date):
        """
        DATA CONTRACT (Expected JSON):
        {
            "match_id": str,
            "team_id": str,
            "previous_match_date": str (YYYY-MM-DD),
            "rest_days": float,
            "travel_km": float,
            "adjusted_rest": float
        }
        """
        if self.mode == 'mock':
            is_midweek = np.random.random() < 0.20
            rest = np.random.uniform(3.0, 4.0) if is_midweek else np.random.uniform(6.0, 8.0)
            travel = np.random.uniform(200, 1500) if np.random.random() < 0.50 else 0.0
            adj_rest = max(1.0, rest - (travel / 1000.0) * 0.5)
            
            return {
                "match_id": match_id,
                "team_id": team_id,
                "rest_days": round(rest, 1),
                "travel_km": round(travel, 1),
                "adjusted_rest": round(adj_rest, 1)
            }
        elif self.mode == 'production':
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT rest_days, travel_km FROM fixture_fatigue WHERE match_id=? AND team_id=?", 
                    (match_id, team_id)
                )
                row = cursor.fetchone()
                conn.close()
                
                if not row or row[0] is None:
                    return self._fallback_json('fatigue')
                    
                rest, travel = row[0], row[1]
                # Same adjustment formula applied on the real DB values
                adj_rest = max(1.0, rest - (travel / 1000.0) * 0.5)
                
                return {
                    "match_id": match_id,
                    "team_id": team_id,
                    "rest_days": round(rest, 1),
                    "travel_km": round(travel, 1),
                    "adjusted_rest": round(adj_rest, 1)
                }
            except sqlite3.Error:
                return self._fallback_json('fatigue')

    def fetch_market_value(self, team_id, match_date):
        """
        DATA CONTRACT (Expected JSON):
        {
            "team_id": str,
            "date": str (YYYY-MM-DD),
            "total_value_eur_m": float
        }
        """
        if self.mode == 'mock':
            return {
                "team_id": team_id,
                "date": match_date,
                "total_value_eur_m": round(np.random.lognormal(mean=3.5, sigma=1.0), 1)
            }
        elif self.mode == 'production':
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # Use subquery to get the closest past date for point-in-time
                cursor.execute('''
                    SELECT total_value_eur_m FROM market_value 
                    WHERE team_id=? AND date <= ? 
                    ORDER BY date DESC LIMIT 1
                ''', (team_id, match_date))
                row = cursor.fetchone()
                conn.close()
                
                if not row or row[0] is None:
                    return self._fallback_json('market_value')
                    
                return {
                    "team_id": team_id,
                    "date": match_date,
                    "total_value_eur_m": round(row[0], 2)
                }
            except sqlite3.Error:
                return self._fallback_json('market_value')

    def fetch_motivation(self, match_id, team_id):
        """
        DATA CONTRACT (Expected JSON):
        {
            "match_id": str,
            "team_id": str,
            "points_to_title": int,
            "points_to_relegation": int,
            "z_score": float
        }
        """
        if self.mode == 'mock':
            return {
                "match_id": match_id,
                "team_id": team_id,
                "points_to_title": np.random.randint(0, 30),
                "points_to_relegation": np.random.randint(0, 30),
                "z_score": round(np.random.uniform(-1.0, 2.0), 3)
            }
        elif self.mode == 'production':
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT points_to_title, points_to_relegation, z_score FROM motivation_context WHERE match_id=? AND team_id=?", 
                    (match_id, team_id)
                )
                row = cursor.fetchone()
                conn.close()
                
                if not row or row[0] is None:
                    return self._fallback_json('motivation')
                    
                return {
                    "match_id": match_id,
                    "team_id": team_id,
                    "points_to_title": row[0],
                    "points_to_relegation": row[1],
                    "z_score": row[2]
                }
            except sqlite3.Error:
                return self._fallback_json('motivation')

    def get_contextual_modifiers(self, match_id, team_id, match_date):
        """
        Composite method that gathers all data and returns the final scalar numbers
        needed by `historical_pipeline.py`.
        """
        impact_data = self.fetch_player_impact(match_id, team_id, match_date)
        fatigue_data = self.fetch_fixture_fatigue(match_id, team_id, match_date)
        motivation_data = self.fetch_motivation(match_id, team_id)
        
        return {
            "xt_loss_modifier": impact_data["total_xT_loss"],
            "rest_days_modifier": fatigue_data["adjusted_rest"],
            "motivation_z_modifier": motivation_data["z_score"]
        }

if __name__ == "__main__":
    # Test Architecture
    adapter = ContextAPIAdapter(mode='production')
    print("--- API DATABASE DATA OUTPUT ---")
    
    # Query an actual match that exists in context_data.db (Index 100, Team 'Fenerbahce' for example)
    match = "100"
    team = "Fenerbahce"
    print(f"\n1. Player Impact JSON (SQL):")
    print(json.dumps(adapter.fetch_player_impact(match, team, "2023-10-15"), indent=2))
    
    print(f"\n2. Fatigue & Travel JSON (SQL):")
    print(json.dumps(adapter.fetch_fixture_fatigue(match, team, "2023-10-15"), indent=2))
    
    print(f"\n3. Market Value Anchor JSON (SQL):")
    print(json.dumps(adapter.fetch_market_value(team, "2023-10-15"), indent=2))
    
    print(f"\n4. Motivation JSON (SQL):")
    print(json.dumps(adapter.fetch_motivation(match, team), indent=2))
    
    print(f"\n5. Combined Payload Envelope for Pipeline:")
    print(json.dumps(adapter.get_contextual_modifiers(match, team, "2023-10-15"), indent=2))
