import os
import json
import pandas as pd
import numpy as np

class AnchorEloManager:
    """Loads ground-truth ratings from ClubElo (Primary) and soccer-rating.com (Secondary)."""
    def __init__(self):
        self.clubelo_anchors = {}
        self.soccer_rating_anchors = {}
        
        base_path = os.path.dirname(__file__)
        
        # 1. Load ClubElo (Gold Standard)
        ce_path = os.path.join(base_path, 'clubelo_data.json')
        if os.path.exists(ce_path):
            try:
                with open(ce_path, 'r', encoding='utf-8') as f:
                    self.clubelo_anchors = json.load(f)
                print(f"[AnchorElo] Loaded {len(self.clubelo_anchors)} ClubElo anchors.")
            except Exception as e:
                print(f"[AnchorElo] Error loading ClubElo anchors: {e}")

        # 2. Load Soccer-Rating (Secondary/National)
        sr_path = os.path.join(base_path, 'soccer_rating_data.json')
        if os.path.exists(sr_path):
            try:
                with open(sr_path, 'r', encoding='utf-8') as f:
                    self.soccer_rating_anchors = json.load(f)
                print(f"[AnchorElo] Loaded {len(self.soccer_rating_anchors)} Soccer-Rating anchors.")
            except Exception as e:
                print(f"[AnchorElo] Error loading Soccer-Rating anchors: {e}")

    def normalize(self, name):
        """Standardizes names for mapping using unified naming_utils."""
        from naming_utils import normalize_turkish
        if not name: return ""
        n = normalize_turkish(name).lower()
        # Suffix stripping for better matching (City, FC, CF, etc.)
        for s in [' fc', ' cf', ' sa', ' as', ' sports', ' city', ' club', ' fk']:
            if n.endswith(s):
                n = n[:len(n)-len(s)].strip()
        return n.strip()

    def get_anchored_rating(self, team_name):
        """
        Prioritizes ClubElo, then Soccer-Rating.
        Uses canonical naming bridge for cross-language matching.
        """
        from naming_utils import FluidMatcher, get_canonical_name
        
        # 1. Bridge the naming gap (Danimarka -> Denmark)
        canonical = get_canonical_name(team_name)
        
        # Priority 1: ClubElo
        ce_keys = list(self.clubelo_anchors.keys())
        
        # Try direct match with canonical
        ce_match = FluidMatcher.match(canonical, ce_keys)
        
        # If no match, try ClubElo-style transcription Bridge
        if not ce_match:
            from naming_utils import normalize_turkish
            ce_trans = normalize_turkish(team_name, clubelo_style=True)
            ce_match = FluidMatcher.match(ce_trans, ce_keys)
            
        if not ce_match:
            # Last ditch: try original name
            ce_match = FluidMatcher.match(team_name, ce_keys)

        if ce_match:
            return float(self.clubelo_anchors[ce_match])

        # Priority 2: Soccer-Rating
        sr_keys = list(self.soccer_rating_anchors.keys())
        sr_match = FluidMatcher.match(canonical, sr_keys) or FluidMatcher.match(team_name, sr_keys)
        if sr_match:
            sr_rating = self.soccer_rating_anchors[sr_match]
            # Calibration: 1500 + (SR_Rating - 1800) * 0.7
            return 1500 + (float(sr_rating) - 1800) * 0.7
            
        return None

# Mapping of League to typical Elo proxy to prevent 1500 default
LEAGUE_TIER_PROXIES = {
    "Premier League": 1850,
    "La Liga": 1820,
    "Bundesliga": 1800,
    "Serie A": 1810,
    "Ligue 1": 1780,
    "Trendyol Süper Lig": 1650,
    "Championship": 1680,
    "Eredivisie": 1680,
    "Liga Portugal": 1700
}

# Fix #2: League-specific goal averages for accurate lambda (xG) base values.
# Source: FBRef / Understat historical season averages for each league.
# Using (avg_home_xg, avg_away_xg) tuples. Default is conservative prior.
LEAGUE_GOAL_AVERAGES = {
    # Top 5 European Leagues
    "premier league":        (1.55, 1.12),
    "la liga":               (1.50, 1.10),
    "bundesliga":            (1.70, 1.30),
    "serie a":               (1.45, 1.08),
    "ligue 1":               (1.35, 1.05),
    # Secondary Leagues
    "süper lig":             (1.52, 1.18),
    "trendyol süper lig":    (1.52, 1.18),
    "championship":          (1.40, 1.10),
    "eredivisie":            (1.70, 1.25),
    "liga portugal":         (1.45, 1.10),
    "süper lig":             (1.52, 1.18),
    # International / National Leagues (usually lower scoring)
    "uluslar ligi":          (1.20, 1.00),
    "nations league":        (1.22, 1.02),
    "avrupa ligi":           (1.30, 1.05),
    "sampiyonlar ligi":      (1.45, 1.10),
    # Default Conservative Prior for unknown leagues
    "default":               (1.40, 1.10),
}

class DynamicEloEngine:
    def __init__(self, k_factor=20, hfa=60, base_elo=1500, c_scale=0.0012):
        """
        Calculates dynamic Elo ratings for football teams.
        k_factor: Learning rate for the Elo system.
        hfa: Home Field Advantage in Elo points.
        base_elo: Starting Elo rating for all teams.
        c_scale: Exponential scaling factor mapping Elo diff to expected goals.
                 0.0012 is even more conservative (standard for high-margin markets).
        """
        self.k_factor = k_factor
        self.hfa = hfa
        self.base_elo = base_elo
        self.c_scale = c_scale
        
        # In-memory dictionary to store current ratings
        # Format: {'TeamName': current_elo}
        self.ratings = {}
        
        # Anchor manager for ground-truth calibration
        self.anchors = AnchorEloManager()
        
        # League averages to act as base multipliers for lambda conversion
        self.avg_home_xg = 1.50
        self.avg_away_xg = 1.20

    def get_rating(self, team, market_value_m=None, league=None):
        """Returns (elo, source) tuple. prioritizes Cache, then Anchors, then Proxies, then MV."""
        # 1. Check in-memory ratings (populated by warm-up or previous matches)
        if team in self.ratings:
            return self.ratings[team], "DYNAMIC"

        # 2. Check for Ground Truth Anchor (Expensive FluidMatcher)
        anchor = self.anchors.get_anchored_rating(team)
        if anchor:
            self.ratings[team] = anchor
            return anchor, "ANCHOR"
            
        # 3. Proxy Elo based on League Tier
        if league and league in LEAGUE_TIER_PROXIES:
            self.ratings[team] = LEAGUE_TIER_PROXIES[league]
            return self.ratings[team], "PROXY"

        # 4. New team initialization (Market Value)
        if market_value_m and market_value_m > 0:
            init_elo = self.base_elo + 50.0 * np.log(max(1.0, market_value_m / 10.0))
            self.ratings[team] = init_elo
            return init_elo, "BUDGET_APPROX"
        else:
            self.ratings[team] = self.base_elo
            return self.base_elo, "DEFAULT_1500"

    def expected_result(self, rating_a, rating_b):
        """Standard Elo expected outcome formula."""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_ratings(self, home_team, away_team, home_goals, away_goals, home_mv=None, away_mv=None):
        """
        Updates the Elo ratings of both teams based on match outcome (Goals).
        Uses margin of victory multiplier for goal-based Elo.
        """
        home_rating = self.get_rating(home_team, home_mv)
        away_rating = self.get_rating(away_team, away_mv)
        
        # Determine actual outcome (1 for Home Win, 0.5 for Draw, 0 for Away Win)
        if home_goals > away_goals:
            actual_home = 1.0
            actual_away = 0.0
        elif home_goals == away_goals:
            actual_home = 0.5
            actual_away = 0.5
        else:
            actual_home = 0.0
            actual_away = 1.0
            
        # Expected outcomes including Home Field Advantage
        home_rating, _ = self.get_rating(home_team, home_mv)
        away_rating, _ = self.get_rating(away_team, away_mv)
        
        exp_home = self.expected_result(home_rating + self.hfa, away_rating)
        exp_away = self.expected_result(away_rating, home_rating + self.hfa)
        
        # Margin of Victory (MoV) multiplier
        goal_diff = abs(home_goals - away_goals)
        mov_multiplier = np.log(goal_diff + 1) * 2.0 if goal_diff > 0 else 1.0
        
        # Update ratings
        new_home_rating = home_rating + self.k_factor * mov_multiplier * (actual_home - exp_home)
        new_away_rating = away_rating + self.k_factor * mov_multiplier * (actual_away - exp_away)
        
        self.ratings[home_team] = new_home_rating
        self.ratings[away_team] = new_away_rating

    def get_base_lambdas(self, home_team, away_team, home_mv=None, away_mv=None, league=None):
        """
        Converts the current Elo difference into predicted Base Lambdas (xG) 
        for the Bivariate Poisson Pricing Engine.
        Returns ((lhBase, laBase), h_meta, a_meta)
        """
        home_rating, h_source = self.get_rating(home_team, home_mv, league=league)
        away_rating, a_source = self.get_rating(away_team, away_mv, league=league)
        
        h_meta = {"elo": round(home_rating, 0), "source": h_source}
        a_meta = {"elo": round(away_rating, 0), "source": a_source}
        
        elo_diff_home = (home_rating + self.hfa) - away_rating
        elo_diff_away = away_rating - (home_rating + self.hfa)
        
        # Fix #2: Use league-specific goal averages instead of global constants
        from naming_utils import normalize_turkish
        league_key = normalize_turkish(league or "").lower().strip() if league else "default"
        # Fuzzy lookup: check if any known league key is a substring of the provided name
        avg_h, avg_a = LEAGUE_GOAL_AVERAGES["default"]
        for k, (lh_avg, la_avg) in LEAGUE_GOAL_AVERAGES.items():
            if k in league_key or league_key in k:
                avg_h, avg_a = lh_avg, la_avg
                break
        
        # Exponential mapping: Lambda = LeagueAvg * exp(c * EloDiff)
        base_lh = avg_h * np.exp(self.c_scale * elo_diff_home)
        base_la = avg_a * np.exp(self.c_scale * elo_diff_away)
        
        # Minimum physical floor for Lambdas to prevent zeroes
        return (max(0.1, base_lh), max(0.1, base_la)), h_meta, a_meta
