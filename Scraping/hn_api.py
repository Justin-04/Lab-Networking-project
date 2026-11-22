import requests, csv, time, os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

FIELDS = ["rank","id","title","url","domain","score","author","comments","timestamp","created_utc","type"]
METRICS = ["date","method","items","time_s","wait_s","active_time_s","requests","bandwidth_kb","avg_latency_ms","notes"]
BASE = "https://hacker-news.firebaseio.com/v0"
WORKERS = 5

def get_item(item_id):
    return requests.get(f"{BASE}/item/{item_id}.json", timeout=10)

t0 = time.time()
r = requests.get(f"{BASE}/topstories.json", timeout=10)
ids = r.json()[:60]
with ThreadPoolExecutor(WORKERS) as ex:                     # multithreading: 5 requests at a time
    responses = list(ex.map(get_item, ids))
elapsed = round(time.time()-t0, 2)

results = []
for rank, resp in enumerate(responses, 1):
    s = resp.json()
    if not s or s.get("deleted") or s.get("dead"): continue
    url = s.get("url") or f"https://news.ycombinator.com/item?id={s['id']}"
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    ts = s.get("time", 0)
    created = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))
    results.append([rank, s["id"], s.get("title",""), url, domain, s.get("score",0), s.get("by",""),
                    s.get("descendants",0), s.get("time"), created, s.get("type","story")])

with open("hn_api.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(FIELDS); w.writerows(results)

all_resp = [r] + responses
kb = round(sum(len(x.content) for x in all_resp)/1024, 2)
latency = round(sum(x.elapsed.total_seconds() for x in all_resp)/len(all_resp)*1000, 2)
new = not os.path.exists("metrics.csv")
with open("metrics.csv", "a", newline="") as f:
    w = csv.writer(f)
    if new: w.writerow(METRICS)
    w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), "API", len(results), elapsed, 0, elapsed,
                len(all_resp), kb, latency, f"workers={WORKERS}"])
print(f"Scraped: {len(results)} | Requests: {len(all_resp)} | {kb} KB | Latency: {latency} ms | Time: {elapsed}s")
