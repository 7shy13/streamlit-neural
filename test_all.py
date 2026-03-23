from backtest_engine import BacktestEngine
from streamlit_app import settle_all_pending_bets, render_stats_banner

be = BacktestEngine()
print("Starting stats:", be.get_summary())

# Run settlement
settle_all_pending_bets(be)

print("Ending stats:", be.get_summary())
html = render_stats_banner(be.get_summary())
print("Rendered Banner HTML length:", len(html))
