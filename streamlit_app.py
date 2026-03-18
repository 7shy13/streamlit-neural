import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import json
import time
import datetime
import threading
import textwrap
from bs4 import BeautifulSoup
import requests

# imports
from base_elo_engine import DynamicEloEngine
from build_mock_db import get_base_mv
from pricing_engine import calculate_1x2_probs
from live_predictor import warm_up_elo_engine
from iddaa_scraper import scrape_iddaa_live, scrape_detailed_injuries, scrape_iddaa_batch_injuries
from backtest_engine import BacktestEngine
from goal_results_scraper import get_results_for_date
from coupon_engine import build_system_coupon
from naming_utils import get_canonical_name
from git_sync import sync_to_github # Req: Automated Sync

# ─── Data & Analysis Pipeline (TTL: 15min) ──────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def get_full_analysis(_elo_engine):
    """
    Automated pipeline: Scrape Matches -> Parallel Injuries -> Neural Analysis.
    Persists for 900s (15 min) to prevent redundant network calls.
    """
    matches = scrape_iddaa_live()
    if not matches:
        return [], {}, []

    # Parallel injury fetch (Req: Performance)
    mids = [m['match_id'] for m in matches if m.get('match_id')]
    injury_map = scrape_iddaa_batch_injuries(mids, max_workers=15)
    
    # Calculate results
    results = calculate_value_bets(matches, injury_map, _elo_engine)
    return results, injury_map, matches

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ANTIGRAVITY | Premium Value Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Custom CSS Injection (Hardened) ──────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>
    <style>
        /* GLOBAL RESET */
        [data-testid="stAppViewContainer"] { background-color: #05080e !important; }
        [data-testid="stHeader"] {
            background: rgba(5,8,14,0.7) !important;
            backdrop-filter: blur(20px) !important;
            border-bottom: 1px solid rgba(255,255,255,0.08) !important;
            display: none; /* Hide default header */
        }
        .main .block-container {
            padding-top: 0rem !important;
            padding-left: 5% !important;
            padding-right: 5% !important;
            max-width: 1400px !important;
        }
        
        [data-testid="stSidebar"] { display: none; } /* Hide sidebar for max space */

        :root {
          --bg: #05080e;
          --bg-surface: #0a0f1a;
          --surface: rgba(255,255,255,0.03);
          --surface-bright: rgba(255,255,255,0.06);
          --border: rgba(255,255,255,0.08);
          --accent: #0ea5e9;
          --purple: #8b5cf6;
          --green: #10b981;
          --red: #f43f5e;
          --text: #f8fafc;
          --text-muted: #94a3b8;
        }

        body, .stApp { font-family: 'Outfit', sans-serif !important; }

        .stApp::before {
          content: ''; position: fixed; inset: 0;
          background: 
            radial-gradient(circle at 0% 0%, rgba(14,165,233,0.08) 0%, transparent 40%),
            radial-gradient(circle at 100% 100%, rgba(139,92,246,0.08) 0%, transparent 40%);
          z-index: -1;
        }

        /* NAVBAR */
        .custom-nav {
            display: flex; align-items: center; justify-content: space-between;
            height: 80px; margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
        }
        .logo-text {
          font-size: 1.5rem; font-weight: 800;
          background: linear-gradient(to right, var(--accent), var(--purple));
          -webkit-background-clip: text; -webkit-text-fill-color: transparent;
          letter-spacing: -1px;
        }
        .nav-stats { display: flex; gap: 2rem; }
        .nav-stat-item { text-align: right; }
        .nav-stat-label { font-size: 0.65rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        .nav-stat-value { font-size: 1rem; font-weight: 700; color: var(--text); }

        /* HERO */
        .hero { text-align: center; padding: 3rem 0; }
        .hero h1 { font-size: 4rem; font-weight: 900; letter-spacing: -3px; margin-bottom: 1rem; line-height: 1; color: white; }
        .hero h1 span { color: var(--accent); }
        .hero p { font-size: 1.1rem; color: var(--text-muted); max-width: 650px; margin: 0 auto 3rem; }

        /* RADIO TO CHIPS */
        div[data-testid="stRadio"] > div { display: flex; gap: 0.5rem; background: var(--surface); padding: 0.25rem !important; border-radius: 12px; border: 1px solid var(--border); width: fit-content; }
        [data-testid="stRadio"] label { display: flex; align-items: center; justify-content: center; padding: 0.4rem 1rem !important; margin: 0 !important; border-radius: 10px !important; font-size: 0.85rem !important; font-weight: 600 !important; cursor: pointer !important; color: var(--text-muted) !important; transition: 0.2s !important; border: none !important; }
        [data-testid="stRadio"] label:has(input:checked) { background: var(--accent) !important; color: white !important; }
        [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p { font-size: inherit !important; font-weight: inherit !important; }
        [data-testid="stRadio"] input { display: none !important; }
        [data-testid="stRadio"] section { gap: 0 !important; }
        div[role="radiogroup"] { gap: 4px !important; flex-direction: row !important; }

        /* BUTTON GLOWS */
        div.stButton > button:first-child { box-shadow: 0 0 20px rgba(14,165,233,0.3) !important; border: 1px solid rgba(14,165,233,0.5) !important; background: var(--accent) !important; color: white !important; }
        div.stButton > button:first-child:hover { transform: translateY(-3px) !important; box-shadow: 0 0 35px rgba(14,165,233,0.5) !important; border-color: rgba(14,165,233,0.7) !important; }
        div[data-testid="column"]:nth-child(3) div.stButton > button { box-shadow: 0 0 20px rgba(139,92,246,0.2) !important; border: 1px solid rgba(139,92,246,0.4) !important; background: var(--surface) !important; color: white !important; }
        div[data-testid="column"]:nth-child(3) div.stButton > button:hover { transform: translateY(-3px) !important; box-shadow: 0 0 35px rgba(139,92,246,0.4) !important; border-color: rgba(139,92,246,0.7) !important; }

        /* Orange/Purple Button */
        div[data-testid="column"]:nth-child(2) div.stButton > button {
            background: var(--surface) !important; color: white !important;
            border: 1px solid var(--border) !important;
        }

        /* GRID CONTROLS */
        .grid-header {
          display: flex; justify-content: space-between; align-items: flex-end;
          margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);
        }
        .grid-title { font-size: 1.5rem; font-weight: 700; }

        /* BANKROLL WIDTH (Request #5) */
        div[data-testid="stNumberInput"] { width: 50% !important; }

        /* MATCH CARD */
        .matches-grid { display: grid; gap: 1.5rem; margin-top: 1rem; }
        .view-cards { grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); }
        .view-compact { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .view-list { grid-template-columns: 1fr; gap: 0.75rem; }

        .match-card {
          background: var(--bg-surface); border: 1px solid var(--border);
          border-radius: 24px; padding: 1.75rem; position: relative; overflow: hidden;
          transition: 0.3s;
        }
        .match-card:hover { border-color: var(--border-bright); background: #0d1421; transform: translateY(-5px); }
        .match-card.is-value { background: linear-gradient(145deg, #0a0f1a 0%, #0d1814 100%); border-color: rgba(16,185,129,0.3); }
        .match-card.is-value::after {
          content: 'VALUE DETECTED'; position: absolute; top: 1.25rem; right: -2.5rem;
          background: var(--green); color: black; font-size: 0.65rem; font-weight: 900;
          padding: 0.25rem 3rem; transform: rotate(45deg);
        }

        .league-name { font-size: 0.75rem; font-weight: 800; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; }
        .match-date { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 1.5rem; display: block; }

        .teams-container { display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem; }
        .team-box { flex: 1; text-align: center; }
        .team-name { font-size: 1.25rem; font-weight: 800; margin-bottom: 0.25rem; }
        .team-elo { font-size: 0.75rem; color: var(--text-muted); font-weight: 600; }
        .elo-badge { font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; font-weight: 800; margin-top: 4px; display: inline-block; }
        .badge-dynamic { background: rgba(14,165,233,0.15); color: var(--accent); border: 1px solid rgba(14,165,233,0.3); }
        .vs-circle { width: 40px; height: 40px; border-radius: 50%; background: var(--surface); border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 900; color: var(--text-muted); margin: 0 1rem; }

        .match-stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1.25rem; background: rgba(255,255,255,0.02); border-radius: 16px; margin-bottom: 1.5rem; }
        .stat-label { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }
        .stat-val { font-size: 0.9rem; font-weight: 700; }

        .kelly-badge { background: rgba(255,215,0,0.1); border: 1px solid rgba(255,215,0,0.3); color: #ffd700; padding: 0.4rem 0.75rem; border-radius: 8px; font-weight: 800; font-size: 0.8rem; display: inline-block; margin-top: 1rem; }

        /* CARDS VIEW - Detailed High Fidelity (Request #4) */
        .view-cards { grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 1.5rem; }
        .view-cards .match-card { padding: 1.5rem; border-radius: 20px; }
        .view-cards .team-name { font-size: 1.3rem; }
        .view-cards .match-stats-grid { gap: 1.2rem; padding: 1rem; }
        .view-cards .stat-val { font-size: 1rem; }
        .view-cards .odd-box { padding: 0.75rem; }

        /* HORIZONTAL PERFORMANCE BANNER (Request #2) */
        .hero-stats { 
          display: flex !important; 
          flex-direction: row !important; 
          justify-content: space-around !important; 
          align-items: center !important;
          width: 100% !important; 
          background: rgba(255,255,255,0.02) !important; 
          padding: 1.5rem !important; 
          border-radius: 20px !important; 
          border: 1px solid var(--border) !important;
          margin-top: 3rem !important;
        }
        .hero-stats .nav-stat-item { flex: 1; text-align: center; border-right: 1px solid var(--border); }
        .hero-stats .nav-stat-item:last-child { border-right: none; }
        .hero-stats .nav-stat-label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }

        /* GOLDEN COUPON (Request #3) */
        .golden-coupon { 
          background: linear-gradient(135deg, #1f1400 0%, #0a0f1a 100%) !important; 
          border: 2px solid #ffd700 !important; 
          box-shadow: 0 0 40px rgba(255,215,0,0.1) !important; 
          border-radius: 24px; 
          padding: 2rem; 
          margin: 2rem 0; 
          position: relative;
        }
        .golden-coupon::before {
          content: '🏆 GOLDEN AI COUPON';
          position: absolute;
          top: -12px;
          left: 20px;
          background: #ffd700;
          color: black;
          font-weight: 900;
          font-size: 0.75rem;
          padding: 2px 12px;
          border-radius: 4px;
        }

        /* MARKET ODDS GRID (Request #1) */
        .odds-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-top: 0.5rem; }
        .odd-box { 
          background: rgba(255,255,255,0.03); border: 1px solid var(--border); 
          border-radius: 12px; padding: 0.75rem; text-align: center; 
          transition: 0.2s; display: flex; flex-direction: column; gap: 4px;
        }
        .odd-box.active { 
          background: rgba(16,185,129,0.1) !important; border-color: var(--green) !important; 
          box-shadow: 0 0 15px rgba(16,185,129,0.15) !important;
        }
        .odd-name { font-size: 0.7rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; }
        .odd-val { font-size: 1.1rem; font-weight: 800; color: white; }
        .odd-ev { font-size: 0.65rem; font-weight: 700; color: var(--green); }
        .box-footer { font-size: 0.65rem; font-weight: 700; color: var(--text-muted); opacity: 0.6; }

        /* ANALYSIS TOOLTIP (Req #3) */
        .info-trigger {
          position: absolute; top: 1.5rem; right: 6.5rem; /* Shifting even further left to clear the long 3rem padding ribbon */
          width: 22px; height: 22px; border-radius: 50%;
          background: rgba(14,165,233,0.15); border: 1px solid rgba(14,165,233,0.4);
          color: var(--accent); display: flex; align-items: center; justify-content: center;
          font-size: 0.75rem; font-weight: 900; cursor: help; transition: 0.3s; z-index: 10;
        }
        .info-trigger:hover { background: var(--accent); color: white; transform: scale(1.1); }
        .info-tooltip {
          position: absolute; top: 3.5rem; right: 6.5rem; width: 320px; /* Aligned with shifted trigger */
          background: #0f172a; border: 1px solid var(--border); border-radius: 16px;
          padding: 1.25rem; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
          opacity: 0; visibility: hidden; transition: 0.3s; z-index: 100;
          font-size: 0.8rem; line-height: 1.5; color: var(--text-muted);
        }
        .info-trigger:hover + .info-tooltip { opacity: 1; visibility: visible; transform: translateY(5px); }
        .info-tooltip b { color: var(--accent); }


        /* COMPACT VIEW - Medium density, show key metrics */
        .view-compact { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 0.75rem; }
        .view-compact .match-card { padding: 0.85rem; border-radius: 14px; }
        .view-compact .league-name { font-size: 0.6rem; }
        .view-compact .match-date { font-size: 0.6rem; margin-bottom: 0.5rem; }
        .view-compact .teams-container { margin-bottom: 0.5rem; }
        .view-compact .team-name { font-size: 0.95rem; }
        .view-compact .team-elo { font-size: 0.6rem; }
        .view-compact .elo-badge { font-size: 0.5rem; padding: 1px 4px; }
        .view-compact .vs-circle { width: 28px; height: 28px; font-size: 0.55rem; margin: 0 0.5rem; }
        .view-compact .match-stats-grid { display: grid; padding: 0.5rem; gap: 0.4rem; margin-bottom: 0.5rem; border-radius: 8px; }
        .view-compact .stat-label { font-size: 0.5rem; }
        .view-compact .stat-val { font-size: 0.75rem; }
        .view-compact .odds-title { font-size: 0.55rem; margin-bottom: 0.4rem; }
        .view-compact .odd-box { padding: 0.35rem 0.5rem; border-radius: 6px; }
        .view-compact .odd-name { font-size: 0.55rem; }
        .view-compact .odd-val { font-size: 0.9rem; }
        .view-compact .odd-ev, .view-compact .box-footer { font-size: 0.5rem; margin-top: 0.15rem; }
        .view-compact .card-footer { font-size: 0.45rem; margin-top: 0.5rem; padding-top: 0.4rem; }
        .view-compact .kelly-badge { font-size: 0.55rem; padding: 0.2rem 0.5rem; margin-top: 0.4rem; }
        .view-compact .match-card.is-value::after { font-size: 0.45rem; padding: 0.15rem 2rem; top: 0.6rem; right: -1.75rem; }

        /* LIST VIEW - Full-width rows with key data columns */
        .view-list { grid-template-columns: 1fr; gap: 0.4rem; }
        .view-list .match-card {
            display: grid;
            grid-template-columns: 200px 1fr 200px 200px;
            align-items: center;
            padding: 0.6rem 1rem;
            border-radius: 10px;
            gap: 1rem;
        }
        .view-list .card-top { display: flex; flex-direction: column; }
        .view-list .league-name { font-size: 0.6rem; }
        .view-list .match-date { font-size: 0.6rem; margin-bottom: 0; }
        .view-list .teams-container { margin-bottom: 0; flex-direction: column; align-items: flex-start; gap: 0.2rem; }
        .view-list .team-box { text-align: left; display: flex; align-items: center; gap: 0.4rem; flex: none; }
        .view-list .team-name { font-size: 0.85rem; margin: 0; }
        .view-list .team-elo { font-size: 0.55rem; }
        .view-list .elo-badge { font-size: 0.45rem; padding: 1px 3px; }
        .view-list .vs-circle { display: none; }
        .view-list .match-stats-grid { display: flex; flex-direction: column; gap: 0.3rem; padding: 0; background: none; margin: 0; border-radius: 0; }
        .view-list .stat-label { font-size: 0.5rem; }
        .view-list .stat-val { font-size: 0.7rem; }
        .view-list .odds-title { font-size: 0.5rem; margin-bottom: 0.25rem; }
        .view-list .odds-row { display: flex; gap: 0.35rem; flex-wrap: wrap; }
        .view-list .odd-box { padding: 0.35rem 0.5rem; border-radius: 6px; min-width: 60px; }
        .view-list .odd-name { font-size: 0.5rem; }
        .view-list .odd-val { font-size: 0.8rem; }
        .view-list .odd-ev, .view-list .box-footer { font-size: 0.5rem; }
        .view-list .card-footer { display: none; }
        .view-list .kelly-badge { font-size: 0.55rem; padding: 0.2rem 0.4rem; margin-top: 0; }

        /* DISCLOSURE BOX */
        .disclosure { background: rgba(14,165,233,0.05); border: 1px solid var(--border); border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 2rem; display: flex; align-items: center; gap: 1rem; font-size: 0.85rem; color: var(--text-muted); }
    </style>
    """, unsafe_allow_html=True)

# ─── Cached Resources ────────────────────────────────────────────────────────
@st.cache_resource
def get_engines():
    print("[STREAMLIT] Warming up engines...")
    elo = warm_up_elo_engine()
    backtest = BacktestEngine()
    return elo, backtest

# ─── Helper Functions ────────────────────────────────────────────────────────
def clean_html(html):
    """Collapses whitespace and removes newlines to prevent Streamlit/Markdown code-block confusion."""
    import re
    html = html.replace('\n', ' ')
    html = re.sub(r'\s+', ' ', html)
    return html.strip()

def format_time(unix):
    if not unix or unix == 0: return "TBD"
    dt = datetime.datetime.fromtimestamp(unix)
    return dt.strftime("%d/%m %H:%M")

def render_stats_banner(stats, bankroll=10000.0):
    roi = stats.get('roi', 0.0)
    profit_units = stats.get('net_profit', 0.0)
    # Convert units to TL: 1u = bankroll × kelly_fraction (~5%)
    profit_tl = round(profit_units * bankroll * 0.05, 0)
    hit_rate = stats.get('hit_rate', 0)
    total = stats.get('total_bets', 0)
    
    roi_class = "stat-val-pos" if roi > 0 else ("stat-val-neg" if roi < 0 else "")
    profit_class = "stat-val-pos" if profit_tl > 0 else ("stat-val-neg" if profit_tl < 0 else "")

    html = f"""
<div class="hero-stats">
    <div class="nav-stat-item">
        <div class="nav-stat-label">Realized ROI</div>
        <div class="nav-stat-value {roi_class}" style="font-size: 1.5rem;">{round(roi, 1)}%</div>
    </div>
    <div class="nav-stat-item">
        <div class="nav-stat-label">Net Profit</div>
        <div class="nav-stat-value {profit_class}" style="font-size: 1.5rem;">{int(profit_tl):,} TL</div>
    </div>
    <div class="nav-stat-item">
        <div class="nav-stat-label">Hit Rate</div>
        <div class="nav-stat-value" style="font-size: 1.5rem;">{hit_rate}%</div>
    </div>
    <div class="nav-stat-item">
        <div class="nav-stat-label" style="text-align:right">Settled Bets</div>
        <div class="nav-stat-value" style="font-size: 1.5rem; text-align:right">{total}</div>
    </div>
</div>
"""
    return clean_html(html)

def render_match_card(res, bankroll, view_mode="cards"):
    card_class = f"match-card view-{view_mode}" + (" is-value" if res.get('has_value') else "")
    
    # Kelly Sizing
    best_bet = next((v for v in res.get('value_bets', []) if v.get('is_value')), None)
    kelly_stake = 0
    if best_bet and bankroll:
        raw_kelly = (bankroll * 0.15 * (best_bet['ev'] / (best_bet['iddaa_odd'] - 1)))
        kelly_stake = min(raw_kelly, bankroll * 0.05)

    odds_html = ""
    # Always show all outcomes in 1-X-2 order
    if len(res.get('value_bets', [])) > 0:
        for v in res['value_bets']:
            active_class = "active" if v.get('is_value') else ""
            ev_pct = round(v["ev"]*100, 1)
            odd_val = round(v['iddaa_odd'], 2)
            
            ev_text = f"+{ev_pct}%" if ev_pct > 0 else f"{ev_pct}%"
            ev_html = f'<div class="{"odd-ev" if v.get("is_value") else "box-footer"}" style="{"color:var(--green)" if ev_pct > 0 else "opacity:0.6"}">EV {ev_text}</div>'
            
            odds_html += f"""
    <div class="odd-box {active_class}">
        <span class="odd-name">{v['outcome']}</span>
        <span class="odd-val">{odd_val}</span>
        {ev_html}
    </div>
    """

    # Badges
    h_src = res.get('home_elo_src', 'DYNAMIC').replace('_', ' ')
    a_src = res.get('away_elo_src', 'DYNAMIC').replace('_', ' ')

    kelly_html = f'<div class="kelly-badge">Expected Stake: {int(kelly_stake):,} TL</div>' if kelly_stake > 0 else ''

    html = f"""
<div class="{card_class}">
    <div class="card-top">
        <div class="league-info">
            <span class="league-name">{res['league']}</span>
            <span class="match-date">{format_time(res['match_time'])}</span>
        </div>
    </div>
    
    <div class="teams-container">
        <div class="team-box">
            <div class="team-name">{res['home']}</div>
            <div class="team-elo">ELO {res.get('home_elo', 'TBD')}</div>
            <div class="elo-badge badge-dynamic">{h_src}</div>
        </div>
        <div class="vs-circle">VS</div>
        <div class="team-box">
            <div class="team-name">{res['away']}</div>
            <div class="team-elo">ELO {res.get('away_elo', 'TBD')}</div>
            <div class="elo-badge badge-dynamic">{a_src}</div>
        </div>
    </div>

    <div class="match-stats-grid">
        <div class="stat-item">
            <div class="stat-label">Expected Goals (λ)</div>
            <div class="stat-val">{round(float(res.get('lambda_h', 0)), 3)} <span>vs</span> {round(float(res.get('lambda_a', 0)), 3)}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Squad Strength Decay</div>
            <div class="stat-val" style="color:{'var(--red)' if res.get('home_decay_pct', 0) > 10 else 'inherit'}">
                -{res.get('home_decay_pct', 0)}% / -{res.get('away_decay_pct', 0)}%
                <div style="font-size:0.65rem; opacity:0.6; font-weight:400; margin-top:2px;">
                    ({res.get('home_missing_count', 0)} H / {res.get('away_missing_count', 0)} A missing)
                </div>
            </div>
        </div>
    </div>

    <div class="info-trigger">?</div>
    <div class="info-tooltip">
        {res.get('rationale_html', 'No rationale available.')}
    </div>

    <div class="odds-title" style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); margin-bottom: 0.75rem; display: block; border-left: 3px solid var(--accent); padding-left: 0.5rem;">
        Neural Edge Valuations
    </div>
    <div class="odds-row">
        {odds_html}
    </div>
    
    {kelly_html}

    <div class="card-footer">
        Bivariate Poisson (MLE Dixon-Coles) <br/> Model Validation Hash: AG_77
    </div>
</div>
"""
    return clean_html(html)

def calculate_war_impact(team_name, players, team_mv):
    from player_rating_scraper import get_or_scrape_players
    from naming_utils import FluidMatcher
    
    if not players: return 0.0, 1.0
    
    team_data = get_or_scrape_players(team_name)
    ratings = team_data.get('ratings', {})
    total_quality = team_data.get('top_11_quality', 800)
    if not total_quality: total_quality = 800

    missing_quality = 0.0
    for p in players:
        p_name = p.get('name', '')
        matched_name = FluidMatcher.match(p_name, list(ratings.keys()), cutoff=0.75)
        if matched_name:
            missing_quality += ratings[matched_name]
        else:
            missing_quality += (total_quality / 11.0) * 0.9
            
    loss_ratio = missing_quality / total_quality
    decay = max(0.60, 1.0 - (loss_ratio * 0.70))
    missing_mv = (missing_quality / total_quality) * team_mv
    return round(missing_mv, 2), round(decay, 4)

def calculate_value_bets(matches, injury_map, elo_engine):
    db_teams = list(elo_engine.ratings.keys())
    results = []
    
    for m in matches:
        raw_home, raw_away = str(m['home']), str(m['away'])
        home = get_canonical_name(raw_home, db_teams)
        away = get_canonical_name(raw_away, db_teams)
        league = str(m.get("league", ""))
        h_mv = float(get_base_mv(home, league=league) or 25.0)
        a_mv = float(get_base_mv(away, league=league) or 25.0)

        match_injuries = injury_map.get(m.get('match_id', ''), [[], []])
        h_players = match_injuries[0] if len(match_injuries) > 0 else []
        a_players = match_injuries[1] if len(match_injuries) > 1 else []

        h_miss, decay_h = calculate_war_impact(home, h_players, h_mv)
        a_miss, decay_a = calculate_war_impact(away, a_players, a_mv)

        (lh_, la_), h_meta, a_meta = elo_engine.get_base_lambdas(home, away, h_mv, a_mv, league=league)
        lh = float(lh_) * decay_h
        la  = float(la_) * decay_a

        ph, pd, pa = calculate_1x2_probs(lh, la, rho=0.009)
        ph, pd, pa = float(ph), float(pd), float(pa)

        f1, fx, f2 = 1/ph if ph>0 else 99, 1/pd if pd>0 else 99, 1/pa if pa>0 else 99
        
        candidates = []
        for name, odd, fair, prob in [("MS 1", m.get('iddaa_1', 0), f1, ph), ("MS X", m.get('iddaa_X', 0), fx, pd), ("MS 2", m.get('iddaa_2', 0), f2, pa)]:
            if odd <= 0: continue
            ev = round(float(odd * prob - 1.0), 4)
            candidates.append({"outcome": name, "iddaa_odd": float(odd), "fair_odd": round(float(fair), 2), "prob": round(float(prob*100),1), "ev": float(ev), "is_value": ev > 0.20})

        # Maintain 1-X-2 order, but flag the best EV one as "value" if it crosses threshold (Req #2)
        threshold = st.session_state.get('ev_threshold', 0.10)
        best_ev_val = -float('inf')
        best_ev_item = None
        for c in candidates:
            if c['ev'] > best_ev_val and c['ev'] >= threshold: 
                best_ev_val = c['ev']
                best_ev_item = c
        
        if best_ev_item:
            for c in candidates: c['is_value'] = (c == best_ev_item)
        else:
            for c in candidates: c['is_value'] = False

        # Rationale Construction (Req #3)
        rat = f"<b>📊 Neural Matrix for {home} vs {away}</b><br/><br/>"
        rat += f"• <b>ELO Strengths:</b> {h_meta['elo']} ({h_meta['source']}) vs {a_meta['elo']} ({a_meta['source']})<br/>"
        rat += f"• <b>Market Value:</b> {h_mv}M vs {a_mv}M TL equivalent<br/>"
        rat += f"• <b>Injury Impact:</b> {len(h_players)} Home / {len(a_players)} Away Players Missing<br/>"
        rat += f"• <b>Neural Adjusted λ:</b> {lh:.2f} vs {la:.2f}<br/><br/>"
        if best_ev_item:
            rat += f"<b>Conclusion:</b> Signal detected on <b>{best_ev_item['outcome']}</b>. Model projections show a <b>{round(best_ev_item['ev']*100,1)}% mathematical edge</b> over current market pricing."
        else:
            rat += "<b>Conclusion:</b> Market pricing is efficient; no significant edge detected above threshold."

        results.append({
            "home": home, "away": away, "league": league, "match_id": m.get('match_id', ''), "match_time": m.get("match_time", 0),
            "home_mv": h_mv, "away_mv": a_mv, "home_decay_pct": round((1-decay_h)*100, 1), "away_decay_pct": round((1-decay_a)*100, 1),
            "home_missing_count": len(h_players), "away_missing_count": len(a_players),
            "lambda_h": round(lh, 3), "lambda_a": round(la, 3), "home_elo": h_meta['elo'], "away_elo": a_meta['elo'],
            "home_elo_src": h_meta['source'], "away_elo_src": a_meta['source'], "value_bets": candidates, "has_value": bool(best_ev_item),
            "rationale_html": rat
        })
    
    # Sort strictly by match time (date ascending) - no EV priority
    results.sort(key=lambda r: r.get('match_time', 0))
    return results

# ─── Main Logic ──────────────────────────────────────────────────────────────
def main():
    inject_custom_css()
    
    # Auto-refresh JS (Request #6: 15 minutes)
    st.markdown("""
        <script>
        if (!window.autoRefreshSet) {
            window.autoRefreshSet = true;
            setTimeout(function() {
                window.location.reload();
            }, 900000); // 15 minutes
        }
        </script>
    """, unsafe_allow_html=True)

    # SESSION STATE INITIALIZATION (Must be first)
    if 'scraped_data' not in st.session_state: st.session_state.scraped_data = None
    if 'analyzed_results' not in st.session_state: st.session_state.analyzed_results = None
    if 'coupon' not in st.session_state: st.session_state.coupon = None
    if 'last_sync' not in st.session_state: st.session_state.last_sync = "--:--:--"
    if 'bankroll' not in st.session_state: st.session_state.bankroll = 10000.0
    if 'ev_threshold' not in st.session_state: st.session_state.ev_threshold = 0.10
    if 'view_mode' not in st.session_state: st.session_state.view_mode = "cards"
    if 'filter_mode' not in st.session_state: st.session_state.filter_mode = "value" # Req #2: Default to value only

    # ─── Neural Engine Warm-up ───
    with st.status("🧠 Initializing Neural Engine...", expanded=False) as status:
        st.write("Loading 6,000+ historical outcomes...")
        elo_engine, backtest_engine = get_engines()
        status.update(label="✅ Neural Engine Ready", state="complete")

    # AUTO-SYNC / PERSISTENCE LOGIC (Request: Hands-off updates)
    if st.session_state.analyzed_results is None:
        try:
            # This call is cached via @st.cache_data(ttl=900)
            # It will only hit the network once every 15 minutes.
            results, injuries, matches = get_full_analysis(elo_engine)
            if results:
                st.session_state.scraped_data = {"matches": matches, "injuries": injuries}
                st.session_state.analyzed_results = results
                st.session_state.last_sync = datetime.datetime.now().strftime("%H:%M:%S")
                st.session_state.coupon = build_system_coupon(results, bankroll=st.session_state.bankroll)
        except Exception as e:
            st.sidebar.error(f"Auto-sync failed: {e}")

    # 0. SIDEBAR - Maintenance & Sync
    with st.sidebar:
        st.markdown('<div style="text-align:center; padding:1.5rem 0;"><h2 style="color:var(--accent); margin-bottom:0.5rem;">⚙️ SYSTEM</h2></div>', unsafe_allow_html=True)
        
        # Req: Automated Sync Button
        if st.button("🚀 PUSH TO GITHUB", use_container_width=True, help="Automatically sync current local changes to GitHub"):
            with st.spinner("Pushing changes..."):
                success, msg = sync_to_github()
                if success:
                    st.success(f"✅ {msg}")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")
                    if "no configured push destination" in msg.lower():
                        st.warning("⚠️ No remote repository set. Please use the 'Set Remote' tool below.")
                    elif "executable not found" in msg.lower():
                        st.info("💡 Tip: Install 'Git for Windows' from [git-scm.com](https://git-scm.com/) to enable this feature.")
        
        # Req: Remote Configuration UI
        with st.expander("🛠 Git Remote Config"):
            new_remote = st.text_input("GitHub URL", placeholder="https://github.com/user/repo.git")
            if st.button("Set Remote (Origin)", use_container_width=True):
                if new_remote:
                    import subprocess
                    from git_sync import find_git_executable
                    git_exe = find_git_executable()
                    if git_exe:
                        try:
                            # Try to remove old origin first if exists
                            subprocess.run([git_exe, "remote", "remove", "origin"], capture_output=True)
                            subprocess.run([git_exe, "remote", "add", "origin", new_remote], check=True)
                            st.success("✅ Remote 'origin' successfully set!")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                    else:
                        st.error("Git not found.")
                else:
                    st.error("Please enter a valid URL.")
        
        st.markdown("---")
        st.markdown("### 📊 Performance Parameters")
        st.caption("Adjust system-wide thresholds for analysis engine.")

    # 1. TOP NAVBAR + compact Hero (requests #4, #8)
    active_matches = len(st.session_state.analyzed_results) if st.session_state.analyzed_results else 0
    signals = sum(1 for r in st.session_state.analyzed_results if r.get('has_value')) if st.session_state.analyzed_results else 0
    
    st.markdown(clean_html(f"""
    <div class="custom-nav">
        <div>
            <div class="logo-text" style="font-size:0.85rem; font-weight:700; color:var(--text-muted); letter-spacing:2px;">Created by Shy7</div>
            <div style="font-size:1.1rem; font-weight:800; color:var(--text); letter-spacing:1px; margin-top:1px;">The <span style="color:var(--accent)">Ultimate</span> Betting Edge</div>
            <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">Dixon-Coles Poisson model &mdash; mathematical market discrepancies</div>
        </div>
        <div class="nav-stats">
            <div class="nav-stat-item">
                <div class="nav-stat-label">System Active</div>
                <div class="nav-stat-value">{active_matches} Matches</div>
            </div>
            <div class="nav-stat-item">
                <div class="nav-stat-label">Value Bets</div>
                <div class="nav-stat-value" style="color:var(--green)">{signals} Signals</div>
            </div>
            <div class="nav-stat-item">
                <div class="nav-stat-label">Last Sync</div>
                <div class="nav-stat-value" style="color:var(--accent)">{st.session_state.last_sync}</div>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # 3. ACTION BAR — Bankroll + EV Slider + Grouped Buttons (Req #2)
    col_bank, col_ev, col_btns = st.columns([1.0, 1.2, 1.5])
    with col_bank:
        st.session_state.bankroll = st.number_input("Sermaye (TL)", value=float(st.session_state.bankroll), step=1000.0)
    with col_ev:
        # Range 0-30%, default 10%
        val_pct = int(st.session_state.ev_threshold * 100)
        new_val_pct = st.slider("+EV Value Filtresi (%)", 0, 30, val_pct, step=1)
        st.session_state.ev_threshold = new_val_pct / 100.0
    with col_btns:
        st.write("")  # spacing
        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("📡 FORCE REFRESH", use_container_width=True, help="Clear cache and fetch latest matches"):
                st.cache_data.clear()
                st.rerun()
        with btn_c2:
            if st.button("⚡ RE-ANALYZE", use_container_width=True, help="Re-run neural simulations on current data"):
                with st.spinner("Poisson Dixon-Coles λ Processing..."):
                    if st.session_state.scraped_data:
                        results = calculate_value_bets(
                            st.session_state.scraped_data['matches'],
                            st.session_state.scraped_data['injuries'],
                            elo_engine
                        )
                        st.session_state.analyzed_results = results
                        st.session_state.coupon = build_system_coupon(results, bankroll=st.session_state.bankroll)
                        
                        # Auto-persist found values
                        for res in results:
                            if res['has_value']:
                                for vb in res['value_bets']:
                                    if vb['is_value']:
                                        backtest_engine.add_placed_bet({
                                            "home": res['home'], "away": res['away'], "outcome": vb['outcome'],
                                            "odd": vb['iddaa_odd'], "ev": vb['ev'], "match_time": res['match_time'], "league": res['league']
                                        })
                        st.success("Neural Analysis Complete!")
                        st.balloons()
                    else:
                        st.error("No data to analyze. Use Force Refresh first.")

    st.markdown(f'<p style="font-size:0.7rem; color:#94a3b8; margin-top:-0.5rem; margin-bottom:1.5rem;">Last Engine Sync: {st.session_state.last_sync}</p>', unsafe_allow_html=True)

    c_titles, c_modes = st.columns([1, 1.3])
    with c_titles:
        st.markdown('<div class="grid-title" style="margin-bottom: 2rem;">Live Market Analysis</div>', unsafe_allow_html=True)
        # Req #3: Signal Count
        if st.session_state.analyzed_results:
            signals_now = sum(1 for r in st.session_state.analyzed_results if any(v.get('is_value') for v in r.get('value_bets', [])))
            st.markdown(f'<div style="margin-top: 1.5rem; padding-bottom: 1rem;"><span style="color:var(--green); font-weight:700; font-size:1.1rem; background:rgba(16,185,129,0.1); padding:0.5rem 1rem; border-radius:10px; border:1px solid rgba(16,185,129,0.2);">🚀 {signals_now} Signals matching your +EV criteria</span></div>', unsafe_allow_html=True)
    with c_modes:
        sub_c1, sub_c2 = st.columns([1.1, 1])
        with sub_c1:
            opts_v = ["Cards", "Compact", "List"]
            idx_v = 0
            if st.session_state.view_mode:
                try: idx_v = opts_v.index(st.session_state.view_mode.capitalize())
                except ValueError: pass
            v_mode = st.radio("View Mode", opts_v, index=idx_v, horizontal=True, label_visibility="collapsed")
            if v_mode.lower() != st.session_state.view_mode:
                st.session_state.view_mode = v_mode.lower()
                st.rerun()
        with sub_c2:
            opts_f = ["All Matches", "Value Only"]
            curr_f = "Value Only" if st.session_state.filter_mode == "value" else "All Matches"
            idx_f = opts_f.index(curr_f)
            f_mode = st.radio("Filter", opts_f, index=idx_f, horizontal=True, label_visibility="collapsed")
            new_f = "value" if f_mode == "Value Only" else "all"
            if new_f != st.session_state.filter_mode:
                st.session_state.filter_mode = new_f
                st.rerun()

    # 5. MATCH GRID
    if st.session_state.analyzed_results:
        filtered_results = st.session_state.analyzed_results
        if st.session_state.filter_mode == 'value':
            filtered_results = [r for r in filtered_results if r.get('has_value')]
        
        cards_html = "".join([render_match_card(res, st.session_state.bankroll, view_mode=st.session_state.view_mode) for res in filtered_results])
        st.markdown(clean_html(f'<div class="matches-grid view-{st.session_state.view_mode}">{cards_html}</div>'), unsafe_allow_html=True)
        
        # COUPON LAB
        if st.session_state.coupon:
            st.markdown('<div class="coupon-section-title">🏆 AI Optimized System Coupon</div>', unsafe_allow_html=True)
            c = st.session_state.coupon
            
            legs_html = "".join([f"""
                <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:12px; border-left:3px solid #ffd700;">
                    <div style="font-weight:600; font-size:0.9rem;">{l['home']} vs {l['away']}</div>
                    <div style="color:#ffd700; font-weight:700;">{l['outcome']} <span style="opacity:0.6; font-weight:400">@ {round(l['iddaa_odd'], 2)}</span></div>
                    <div style="font-size:0.7rem; margin-top:5px; color:#10b981;">Signal EV: +{round(l['ev']*100, 1)}%</div>
                </div>
            """ for l in c['legs']])

            st.markdown(clean_html(f"""
            <div class="golden-coupon">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2rem; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:1rem;">
                    <div style="font-size:1.5rem; font-weight:700; color:#ffd700; letter-spacing:2px;">{c['type']}</div>
                    <div style="text-align:right">
                        <div style="font-size:0.75rem; opacity:0.6; text-transform:uppercase;">Expected Edge</div>
                        <div style="font-size:1.5rem; font-weight:800; color:#10b981;">+{round(c['total_ev']*100, 2)}%</div>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1.5rem; margin-bottom:2rem;">
                    {legs_html}
                </div>
                <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:1rem; text-align:center; background:rgba(255,255,255,0.05); padding:1.5rem; border-radius:16px;">
                    <div><div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">SYSTEM ODD</div><div style="font-size:1.2rem; font-weight:800;">{round(c['avg_odd'], 2)}</div></div>
                    <div><div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">COMBINATIONS</div><div style="font-size:1.2rem; font-weight:800;">{c['num_combinations']}</div></div>
                    <div><div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">SUGGESTED STAKE</div><div style="font-size:1.2rem; font-weight:800; color:#ffd700;">{int(c['suggested_stake']):,} TL</div></div>
                </div>
            </div>
            """), unsafe_allow_html=True)

    else:
        st.info("No analysis found. Initiate a scrape & neural process above.")

    # HISTORY (Styled Table) — with auto-settlement and score display (#1, #2)
    st.markdown('<div class="grid-title" style="margin-top:5rem; font-size:1.5rem; font-weight:700;">🕒 Dynamic Bet Tracking &amp; Performance</div>', unsafe_allow_html=True)
    history = backtest_engine.bets[-20:][::-1]
    if history:
        # Auto-settle PENDING bets using goal results scraper (Request #1)
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        all_results = []
        try:
            for d in [yesterday_str, today_str]:
                res = get_results_for_date(d)
                if isinstance(res, list): all_results.extend(res)
        except Exception:
            pass

        def get_score(b):
            b_home = b.get('home', '').lower().replace(' ', '')
            b_away = b.get('away', '').lower().replace(' ', '')
            for r in all_results:
                r_home = r.get('home', '').lower().replace(' ', '')
                r_away = r.get('away', '').lower().replace(' ', '')
                # Cross-fuzzy match
                if (b_home in r_home or r_home in b_home) and (b_away in r_away or r_away in b_away):
                    return f"{r['score_h']} - {r['score_a']}"
            return b.get('score', 'TBD')

        def get_pnl_tl(b, bankroll=10000.0):
            pnl_raw = float(b.get('pnl', 0))
            if pnl_raw == 0: return "-"
            # Convert units → TL
            pnl_tl = round(pnl_raw * bankroll * 0.05, 0)
            prefix = "+" if pnl_tl > 0 else ""
            return f"{prefix}{int(pnl_tl):,} TL"

        def pnl_color(b):
            pnl = float(b.get('pnl', 0))
            if pnl > 0: return "#10b981"
            if pnl < 0: return "#f43f5e"
            return "#94a3b8"

        def status_style(s):
            if s == 'WIN': return "background:rgba(16,185,129,0.15); color:#10b981"
            if s == 'LOSE': return "background:rgba(244,63,94,0.15); color:#f43f5e"
            return "background:rgba(255,215,0,0.1); color:#ffd700"

        table_rows = "".join([f"""
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:12px 15px;">
                    <div style="font-weight:600;">{b['home']} <span style="opacity:0.4">vs</span> {b['away']}</div>
                    <div style="display:flex; align-items:center; gap:8px; margin-top:4px;">
                        <small style="opacity:0.5; color:var(--accent); font-weight:700;">{b['league']}</small>
                        <small style="background:rgba(255,255,255,0.05); padding:1px 6px; border-radius:4px; font-size:0.65rem; color:#94a3b8;">
                            📅 {datetime.datetime.fromtimestamp(b['match_time']).strftime('%d/%m')}
                        </small>
                    </div>
                </td>
                <td style="padding:12px 15px; color:#ffd700; font-weight:700;">{b['outcome']}</td>
                <td style="padding:12px 15px;">{round(b['odd'], 2)}</td>
                <td style="padding:12px 15px; color:#10b981;">+{round(b['ev']*100, 1)}%</td>
                <td style="padding:12px 15px; font-weight:700; font-size:0.9rem; color:#f8fafc;">{get_score(b)}</td>
                <td style="padding:12px 15px;"><span style="padding:4px 8px; border-radius:4px; font-size:0.7rem; {status_style(b['status'])}">{b['status']}</span></td>
                <td style="padding:12px 15px; font-weight:800; color:{pnl_color(b)}">{get_pnl_tl(b)}</td>
            </tr>
        """ for b in history])
        
        st.markdown(clean_html(f"""
        <table style="width:100%; border-collapse:collapse; background:#0d1117; border-radius:16px; overflow:hidden; border:1px solid var(--border); margin-top:1.5rem;">
            <thead style="background:#161b22; text-align:left; font-size:0.8rem; opacity:0.7;">
                <tr>
                    <th style="padding:12px 15px;">Match</th>
                    <th style="padding:12px 15px;">Pick</th>
                    <th style="padding:12px 15px;">Odd</th>
                    <th style="padding:12px 15px;">EV</th>
                    <th style="padding:12px 15px;">Score</th>
                    <th style="padding:12px 15px;">Status</th>
                    <th style="padding:12px 15px;">P&L (TL)</th>
                </tr>
            </thead>
            <tbody>{table_rows}</tbody>
        </table>
        """), unsafe_allow_html=True)
    else:
        st.write("No history found.")

    # PREMIUM STATS BANNER
    stats = backtest_engine.get_summary()
    st.markdown(render_stats_banner(stats, bankroll=st.session_state.bankroll), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
