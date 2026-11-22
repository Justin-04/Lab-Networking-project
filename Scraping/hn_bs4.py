import requests, csv, time, os, re, calendar
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

FIELDS = ["rank","id","title","url","domain","score","author","comments","timestamp","created_utc","type"]
METRICS = ["date","method","items","time_s","wait_s","active_time_s","requests","bandwidth_kb","avg_latency_ms","notes"]
headers = {"User-Agent": "labnet2-student-scraper/1.0"}
pages = ["https://news.ycombinator.com/news", "https://news.ycombinator.com/news?p=2"]

t0 = time.time()
results, responses, wait = [], [], 0
for i, page in enumerate(pages):
    if i > 0:
        time.sleep(30); wait += 30
    r = requests.get(page, headers=headers, timeout=10); responses.append(r)
    while "not able to serve your requests" in r.text:
        print("Rate-limited, waiting 60s..."); time.sleep(60); wait += 60
        r = requests.get(page, headers=headers, timeout=10); responses.append(r)
    soup = BeautifulSoup(r.text, "html.parser")
    for story in soup.select("tr.athing"):
        sub = story.find_next_sibling("tr")
        link = story.select_one("span.titleline > a")
        rank = int(story.select_one("span.rank").text.strip("."))
        url = urljoin("https://news.ycombinator.com/", link["href"])
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        score, author, comments = 0, "", 0

        m = re.search(r"(\d+)\s+points?", sub.get_text(" "))
        if m: score = int(m.group(1))
        m = re.search(r"(\d+)\s+comments?", sub.get_text(" "))
        if m: comments = int(m.group(1))
        user = sub.select_one("a.hnuser, a[href^='user?id=']")
        if user: author = user.get_text()

        age = sub.select_one("span.age")["title"][:19]
        ts = calendar.timegm(time.strptime(age, "%Y-%m-%dT%H:%M:%S"))
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))
        story_type = "story" if user else "job"
        results.append([rank, int(story["id"]), link.get_text(), url, domain,
                        score, author, comments, ts, created, story_type])
elapsed = round(time.time()-t0, 2)

with open("hn_bs4.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(FIELDS); w.writerows(results)

kb = round(sum(len(x.content) for x in responses)/1024, 2)
latency = round(sum(x.elapsed.total_seconds() for x in responses)/len(responses)*1000, 2)
new = not os.path.exists("metrics.csv")
with open("metrics.csv", "a", newline="") as f:
    w = csv.writer(f)
    if new: w.writerow(METRICS)
    w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), "BS4", len(results), elapsed, wait, round(elapsed-wait, 2),
                len(responses), kb, latency, f"pages={len(pages)}"])
print(f"Scraped: {len(results)} | Requests: {len(responses)} | {kb} KB | Latency: {latency} ms | Time: {elapsed}s")
