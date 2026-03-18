# ANTIGRAVITY | Premium Value Analyzer 🚀

ANTIGRAVITY is a high-fidelity quantitative analyzer for football betting markets. It combines Dynamic ELO ratings, Market Value (Financial Proxy) analysis, and Bivariate Poisson simulations (Dixon-Coles) to detect mathematical value in 1X2 and Asian Handicap markets.

## 🌟 Key Features
- **Neural Engine**: Calibrates team strengths using 6000+ historical matches.
- **Financial Proxy**: Integrates Transfermarkt live values to account for squad quality.
- **Squad Strength Decay**: Real-time injury and suspension impact analysis.
- **Dynamic Dashboard**: Interactive Streamlit interface with real-time EV filtering.
- **AI System Coupon**: Automated high-ROI 3/4 system coupon generation.

## 🛠 Project Structure
```text
├── streamlit_app.py        # Main Dashboard (Interactive UI)
├── dashboard.html          # Local/Legacy HTML Dashboard
├── T1_ALL.csv              # Historical Match Database (6000+ entries)
├── requirements.txt        # Project Dependencies
├── placed_bets.json        # Local Bet Storage
├── stats.json              # Real-time Performance Statistics
└── src/                    # Core Analytical Logic
    ├── base_elo_engine.py  # Dynamic ELO & Bayesian Priors
    ├── pricing_engine.py   # Dixon-Coles Poisson Simulations
    ├── iddaa_scraper.py    # Bulletin & Odds Scraping
    ├── live_predictor.py   # CLI-based Prediction Bot
    └── ...                 # Utilities (Scrapers, Naming, Impact)
```

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
