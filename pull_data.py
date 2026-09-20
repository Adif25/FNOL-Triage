"""
Pull loss narratives from the NHTSA vehicle safety complaints API.

Why this source: each complaint carries a free-text `summary` written by
the consumer -- messy, unpunctuated, often all-caps, which is what real
first-notice-of-loss text looks like -- PLUS structured fields (crash,
fire, numberOfInjuries) recorded at intake.

Those structured fields are kept as `weak_labels`. They are NOT ground
truth: the same person wrote both the narrative and the checkboxes, so
they are correlated. But they are independent of YOUR judgment, they
cover all 500 records instead of 50, and they are exactly the kind of
partially-reliable historical label real claims data comes with. See
evaluate.py for how they are used and what they can and cannot support.

The API is queried per make/model/year, so breadth comes from querying a
spread of vehicles rather than one big call.
"""

import json
import random
import time
import urllib.parse
import urllib.request

API = "https://api.nhtsa.gov/complaints/complaintsByVehicle"

# A spread across manufacturers, body styles and model years, so the
# sample is not dominated by one vehicle's recall cluster.
FLEET = [
    ("honda", "accord", 2019), ("honda", "civic", 2021),
    ("toyota", "camry", 2020), ("toyota", "rav4", 2022),
    ("ford", "f-150", 2021), ("ford", "explorer", 2020),
    ("chevrolet", "silverado", 2021), ("chevrolet", "equinox", 2019),
    ("nissan", "altima", 2020), ("nissan", "rogue", 2021),
    ("jeep", "grand cherokee", 2022), ("jeep", "wrangler", 2021),
    ("subaru", "outback", 2020), ("subaru", "forester", 2022),
    ("hyundai", "elantra", 2021), ("hyundai", "tucson", 2022),
    ("kia", "telluride", 2021), ("kia", "sorento", 2022),
    ("tesla", "model 3", 2021), ("tesla", "model y", 2022),
    ("bmw", "x5", 2020), ("volkswagen", "jetta", 2021),
    ("ram", "1500", 2021), ("gmc", "sierra", 2020),
    ("mazda", "cx-5", 2021), ("dodge", "charger", 2020),
]

TARGET = 500
MIN_CHARS = 120        # below this there is nothing to extract
MAX_PER_VEHICLE = 40   # stop one recall cluster from dominating


def fetch(make, model, year):
    q = urllib.parse.urlencode(
        {"make": make, "model": model, "modelYear": year})
    req = urllib.request.Request(
        f"{API}?{q}", headers={"User-Agent": "fnol-triage-portfolio/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["results"]


def main():
    seen, rows = set(), []

    for make, model, year in FLEET:
        try:
            results = fetch(make, model, year)
        except Exception as e:
            print(f"  skip {make} {model} {year}: {e}")
            continue

        kept = 0
        for c in results:
            if kept >= MAX_PER_VEHICLE:
                break
            odi = c.get("odiNumber")
            summary = (c.get("summary") or "").strip()
            if odi in seen or len(summary) < MIN_CHARS:
                continue
            seen.add(odi)
            kept += 1
            rows.append({
                "id": str(odi),
                "narrative": summary,
                # Context an adjuster would have. Not fed to the model --
                # the model sees only the narrative.
                "context": {
                    "make": make, "model": model, "year": year,
                    "components": c.get("components", ""),
                    "date_of_incident": c.get("dateOfIncident"),
                },
                # Structured intake fields. Weak labels, not ground truth.
                "weak_labels": {
                    "crash": bool(c.get("crash")),
                    "fire": bool(c.get("fire")),
                    "injuries": int(c.get("numberOfInjuries") or 0),
                    "deaths": int(c.get("numberOfDeaths") or 0),
                },
            })
        print(f"  {make} {model} {year}: kept {kept}")
        time.sleep(0.4)

    random.seed(20260920)     # reproducible sample
    random.shuffle(rows)
    rows = rows[:TARGET]

    with open("data/sample.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    wl = [r["weak_labels"] for r in rows]
    print(f"\nwrote {len(rows)} records to data/sample.jsonl")
    print(f"  crash flagged:   {sum(w['crash'] for w in wl)}")
    print(f"  fire flagged:    {sum(w['fire'] for w in wl)}")
    print(f"  injuries > 0:    {sum(w['injuries'] > 0 for w in wl)}")
    print(f"  median length:   "
          f"{sorted(len(r['narrative']) for r in rows)[len(rows) // 2]} chars")


if __name__ == "__main__":
    main()
