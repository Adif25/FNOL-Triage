"""
Build the hand-labeling sheet.

Why stratified and not random:

  In this sample only ~5% of records are flagged as crashes, ~2% report
  injuries, ~1% involve fire. A random 50 would contain roughly two
  crashes, one injury, and zero fires -- so every metric about the cases
  you actually care about would rest on one or two records, which is
  noise, not measurement.

  So the sheet oversamples rare, high-signal records and fills the rest
  at random. This is a deliberate, disclosable choice:

    - Rare-class metrics (safety_critical recall, high-severity accuracy)
      become measurable.
    - Overall accuracy on this sheet is NOT representative of the full
      500, because the mix is different by construction. Say so in the
      README. Report full-corpus rates from the weak-label agreement
      instead.

  Getting this distinction right -- and stating it -- is worth more than
  a higher number would be.
"""

import csv
import json
import random

N = 50
random.seed(20260920)

rows = [json.loads(l) for l in open("data/sample.jsonl")]
by_id = {r["id"]: r for r in rows}


def interesting(r):
    w = r["weak_labels"]
    return w["crash"] or w["fire"] or w["injuries"] > 0 or w["deaths"] > 0


rare = [r for r in rows if interesting(r)]
common = [r for r in rows if not interesting(r)]
random.shuffle(rare)
random.shuffle(common)

# Take up to 20 rare, fill to 50 with common -> roughly 40/60 split,
# versus ~8/92 if sampled at random.
picked = rare[:20] + common[: N - len(rare[:20])]
random.shuffle(picked)

with open("gold/labels.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "narrative", "claim_type", "severity",
                "injury_reported", "safety_critical", "routing", "notes"])
    for r in picked:
        text = " ".join(r["narrative"].split())
        w.writerow([r["id"], text, "", "", "", "", "", ""])

n_rare = sum(interesting(by_id[p["id"]]) for p in picked)
print(f"wrote gold/labels.csv with {len(picked)} rows, label columns blank")
print(f"  rare-class records: {n_rare}/{len(picked)} "
      f"({n_rare / len(picked):.0%}, vs {len(rare) / len(rows):.0%} in corpus)")
print("\nLabel these before you look at out/run_log.jsonl.")
