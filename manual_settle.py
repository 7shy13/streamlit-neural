from backtest_engine import BacktestEngine
from goal_results_scraper import get_results_for_date
import datetime

be = BacktestEngine()
now_utc = datetime.datetime.utcnow()
dates = [
    now_utc.strftime("%Y-%m-%d"),
    (now_utc - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
    (now_utc - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
]

all_results = []
for d in dates:
    res = get_results_for_date(d)
    if res:
        all_results.extend(res)

settled = be.settle_bets(all_results)
print(f"Settled {settled} matches.")
