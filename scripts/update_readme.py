"""
Refreshes the "Latest open roles" table in README.md from the AI Work Expert job feed.

Only the block between <!-- JOBS:START --> and <!-- JOBS:END --> is rewritten.
Standard library only, so the GitHub Action needs no install step.

Usage: python3 scripts/update_readme.py
"""
import pathlib
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEED_URL = "https://www.aiworkexpert.com/feeds/jobs.xml"
README = pathlib.Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- JOBS:START -->", "<!-- JOBS:END -->"
LIMIT = 50


def text(job, tag):
    el = job.find(tag)
    return (el.text or "").strip() if el is not None else ""


def cell(s):
    # Pipes and newlines would break the markdown table.
    return " ".join(s.replace("|", "/").split())


def posted(job):
    try:
        return parsedate_to_datetime(text(job, "date"))
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


req = urllib.request.Request(FEED_URL, headers={"User-Agent": "awesome-ai-training-jobs-updater"})
with urllib.request.urlopen(req, timeout=60) as resp:
    root = ET.fromstring(resp.read())

jobs = sorted(root.findall("job"), key=posted, reverse=True)
if not jobs:
    # An empty feed is far more likely an outage than zero open roles; keep the last table.
    sys.exit("Feed returned no jobs; README left unchanged.")

counts = Counter(text(j, "company") for j in jobs)
summary = ", ".join(f"{name} ({n})" for name, n in counts.most_common())

rows = []
for j in jobs[:LIMIT]:
    when = posted(j)
    rows.append(
        f"| [{cell(text(j, 'title'))}]({text(j, 'url')}) | {cell(text(j, 'company'))} "
        f"| {cell(text(j, 'salary')) or 'Not stated'} | {when.strftime('%d %b %Y') if when.year > 1 else ''} |"
    )

block = "\n".join(
    [
        START,
        f"**{len(jobs)} open remote roles** across {len(counts)} platforms: {summary}.",
        f"The newest {min(LIMIT, len(jobs))} are below. Updated {datetime.now(timezone.utc):%d %b %Y}.",
        "",
        "| Role | Platform | Pay | Posted |",
        "|---|---|---|---|",
        *rows,
        END,
    ]
)

readme = README.read_text()
head, rest = readme.split(START, 1)
_, tail = rest.split(END, 1)
new = head + block + tail
if new != readme:
    README.write_text(new)
    print(f"README updated: {len(jobs)} jobs, {len(rows)} shown.")
else:
    print("No change.")
