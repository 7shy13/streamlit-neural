# ANTIGRAVITY | Premium Value Analyzer 🚀

ANTIGRAVITY is a high-fidelity quantitative analyzer for football betting markets. It combines Dynamic ELO ratings, Market Value (Financial Proxy) analysis, and Bivariate Poisson simulations (Dixon-Coles) to detect mathematical value in 1X2 and Asian Handicap markets.

## 🌟 Key Features
- **Neural Engine**: Calibrates team strengths using 6000+ historical matches.
- **Financial Proxy**: Integrates Transfermarkt live values to account for squad quality.
- **Squad Strength Decay**: Real-time injury and suspension impact analysis.
- **Dynamic Dashboard**: Interactive Streamlit interface with real-time EV filtering.
- **AI System Coupon**: Automated high-ROI 3/4 system coupon generation.

## 📁 Project Structure

Given the requirements for Streamlit Cloud deployment, the project follows a flattened structure for maximum module resolution stability:

- `streamlit_app.py`          # Main Dashboard & Entry Point
- `base_elo_engine.py`        # Core ELO logic & Anchors
- `pricing_engine.py`         # Bivariate Poisson & AH Pricing
- `iddaa_scraper.py`          # Live match & Injury data
- `live_predictor.py`         # Real-time analysis pipeline
- `git_sync.py`               # Automated GitHub synchronisation
- `T1_ALL.csv`                # Historical match database (6000+ matches)
- `player_data/`              # JSON storage for squad-level metrics
- `requirements.txt`          # Project dependencies (inc. scipy)

## 🚀 Getting Started

### 1. Installation
Ensure you have Python 3.10+ installed. Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Running the Dashboard (Recommended)
Launch the interactive Streamlit application to access the full analytical suite:
```bash
streamlit run streamlit_app.py
```

### 3. Running the CLI Bot
For a lightweight, command-line based prediction interface:
```bash
python src/live_predictor.py
```

## 🧠 Core Methodology
- **Rating System**: Uses a Glicko/ELO hybrid that warms up using historical data to establish baseline team strengths.
- **Goal Expectancy ($\lambda$)**: Generated from relative ELO strengths, further adjusted by market value spreads and injury-induced decay.
- **EV Calculation**: Compares modeled 'Fair Odds' against live market odds from IDDAA/Global markets. If `Market Odds / Fair Odds > 1 + Threshold`, it is flagged as a Value Bet.

## ⚠️ Disclaimer
This tool is for educational and analytical purposes only. Betting involves significant risk. Never wager money you cannot afford to lose.
