from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import csv, time, os, re, calendar

FIELDS = ["rank","id","title","url","domain","score","author","comments","timestamp","created_utc","type"]
METRICS = ["date","method","items","time_s","wait_s","active_time_s","requests","bandwidth_kb","avg_latency_ms","notes"]
pages = ["https://news.ycombinator.com/news", "https://news.ycombinator.com/news?p=2"]

# Selenium cannot see the network traffic itself, so after each page we ask the browser
PERF = """
const files = performance.getEntriesByType('navigation').concat(performance.getEntriesByType('resource'));
const page = performance.getEntriesByType('navigation')[0];
let bytes = 0;
for (const f of files) bytes += f.decodedBodySize;
return [files.length, bytes, page.responseStart - page.requestStart];
"""

t0 = time.time()
driver = webdriver.Chrome()
results, n_req, n_bytes, latencies, wait = [], 0, 0, [], 0
for i, page in enumerate(pages):
    if i > 0:
        time.sleep(30); wait += 30
    driver.get(page)
    while "not able to serve your requests" in driver.page_source:
        print("Rate-limited, waiting 60s..."); time.sleep(60); wait += 60
        driver.refresh()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.athing")))
    req, size, lat = driver.execute_script(PERF)
    n_req += req; n_bytes += size; latencies.append(lat)
    stories = driver.find_elements(By.CSS_SELECTOR, "tr.athing")
    subs = driver.find_elements(By.CSS_SELECTOR, "td.subtext")
    for story, sub in zip(stories, subs):
        link = story.find_element(By.CSS_SELECTOR, "span.titleline > a")
        rank = int(story.find_element(By.CSS_SELECTOR, "span.rank").text.strip("."))
        url = link.get_attribute("href")
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        score, author, comments = 0, "", 0

        m = re.search(r"(\d+)\s+points?", sub.text)
        if m: score = int(m.group(1))
        m = re.search(r"(\d+)\s+comments?", sub.text)
        if m: comments = int(m.group(1))
        users = sub.find_elements(By.CSS_SELECTOR, "a.hnuser, a[href^='user?id=']")
        if users: author = users[0].text

        age = sub.find_element(By.CSS_SELECTOR, "span.age").get_attribute("title")[:19]
        ts = calendar.timegm(time.strptime(age, "%Y-%m-%dT%H:%M:%S"))
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))
        story_type = "story" if users else "job"
        results.append([rank, int(story.get_attribute("id")), link.text, url, domain,
                        score, author, comments, ts, created, story_type])
driver.quit()
elapsed = round(time.time()-t0, 2)

with open("hn_selenium.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(FIELDS); w.writerows(results)

kb = round(n_bytes/1024, 2)
latency = round(sum(latencies)/len(latencies), 2)
new = not os.path.exists("metrics.csv")
with open("metrics.csv", "a", newline="") as f:
    w = csv.writer(f)
    if new: w.writerow(METRICS)
    w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), "Selenium", len(results), elapsed, wait, round(elapsed-wait, 2),
                n_req, kb, latency, f"pages={len(pages)}"])
print(f"Scraped: {len(results)} | Requests: {n_req} | {kb} KB | Latency: {latency} ms | Time: {elapsed}s")
