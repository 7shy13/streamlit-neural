import datetime
from goal_results_scraper import get_results_for_date

now_utc = datetime.datetime.utcnow()
for i in range(1, 10, 3):
    d = (now_utc - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
    res = get_results_for_date(d)
    print(f"Date: {d}, Results found: {len(res) if res else 0}")
