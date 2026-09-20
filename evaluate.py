"""
Score predictions against hand labels.

Metrics are implemented by hand rather than pulled from sklearn. That is
deliberate: you should be able to explain exactly what macro-F1 is doing
when someone asks you in an interview, and 40 lines of arithmetic is
cheaper than a dependency you can't defend.

Reported:
  accuracy per field       -- the headline number, and the most misleading
  majority baseline        -- what you'd score by always guessing the most
                              common class. If you can't beat this, you have
                              nothing. ALWAYS report it next to accuracy.
  macro-F1 on claim_type   -- averages F1 across classes so a rare class
                              counts as much as a common one. On skewed data
                              this is the honest number.
  severity confusion       -- where it's wrong matters: low->medium is a
                              nuisance, low->high is a broken routing rule.
  recall on safety_critical-- asymmetric cost. Missing a true safety case is
                              far worse than a false alarm, so recall is the
                              number to optimize here, not accuracy.
  span grounding rate      -- % of evidence_span values actually present in
                              the source. This is a direct, measurable
                              hallucination rate.
"""

import csv
import json
import pathlib
from collections import Counter, defaultdict

from schema import SCORED_FIELDS, TriageResult, is_grounded

OUT = pathlib.Path("out")
BOOL = {"true": True, "false": False, "1": True, "0": False,
        "yes": True, "no": False}


def load_gold(path="gold/labels.csv"):
    gold = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            rid = row["id"].strip()
            if not rid or not row.get("claim_type", "").strip():
                continue                      # unlabeled row, skip
            rec = {}
            for k in SCORED_FIELDS:
                v = row[k].strip().lower()
                rec[k] = BOOL.get(v, v) if k in ("injury_reported",
                                                 "safety_critical") else v
            gold[rid] = rec
    return gold


def load_preds(path="out/run_log.jsonl"):
    preds, narratives = {}, {}
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            if row.get("ok"):
                preds[row["id"]] = row["result"]
    with open("data/sample.jsonl") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                narratives[str(r["id"])] = r.get("narrative", "")
    return preds, narratives


def macro_f1(pairs):
    """pairs: list of (true, pred). Returns (macro_f1, per_class dict)."""
    classes = sorted({t for t, _ in pairs} | {p for _, p in pairs})
    per = {}
    for c in classes:
        tp = sum(1 for t, p in pairs if t == c and p == c)
        fp = sum(1 for t, p in pairs if t != c and p == c)
        fn = sum(1 for t, p in pairs if t == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per[c] = {"precision": round(prec, 3), "recall": round(rec, 3),
                  "f1": round(f1, 3), "support": tp + fn}
    macro = sum(v["f1"] for v in per.values()) / len(per) if per else 0.0
    return round(macro, 3), per



def weak_label_agreement(preds, path="data/sample.jsonl"):
    """
    Agreement with the structured fields NHTSA recorded at intake, across
    ALL extracted records rather than the 50 you labeled.

    These are WEAK labels, not ground truth. The same consumer wrote both
    the narrative and the checkboxes, so they are correlated, and some are
    plainly wrong -- one record in this corpus reports 3 injuries on an
    air-conditioning complaint. Disagreement here is therefore evidence to
    go read the record, not proof the model is wrong.

    What this buys you: coverage. The hand-labeled sheet is 50 records and
    deliberately over-weighted toward rare classes. This runs over all 500
    at the corpus's true mix, so the two together tell you more than either
    alone.
    """
    rows = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[str(r["id"])] = r

    out, disagreements = {}, []
    checks = [
        ("crash -> collision", lambda w: w["crash"],
         lambda p: p["claim_type"] == "collision"),
        ("fire -> fire", lambda w: w["fire"],
         lambda p: p["claim_type"] == "fire"),
        ("injuries>0 -> injury_reported", lambda w: w["injuries"] > 0,
         lambda p: p["injury_reported"]),
    ]

    print("\nweak-label agreement (all extracted records)")
    for name, flag, pred_fn in checks:
        flagged = [(i, p) for i, p in preds.items()
                   if i in rows and flag(rows[i]["weak_labels"])]
        if not flagged:
            continue
        hits = [i for i, p in flagged if pred_fn(p)]
        rate = len(hits) / len(flagged)
        out[name] = {"n_flagged": len(flagged), "agreement": round(rate, 3)}
        print(f"  {name:<32} {rate:>6.2f}  (n={len(flagged)})")
        for i, p in flagged:
            if not pred_fn(p):
                disagreements.append({"id": i, "check": name,
                                      "predicted": p["claim_type"],
                                      "severity": p["severity"]})

    pathlib.Path("out/disagreements.json").write_text(
        json.dumps(disagreements, indent=2))
    print(f"  {len(disagreements)} disagreements -> out/disagreements.json")
    print("  READ A FEW. They are your error-analysis section.")
    return out


def main():
    gold = load_gold()
    preds, narratives = load_preds()
    ids = [i for i in gold if i in preds]
    print(f"scoring {len(ids)} labeled records "
          f"({len(gold) - len(ids)} labeled but not extracted)\n")

    metrics = {"n_scored": len(ids)}

    # --- accuracy + baseline per field --------------------------------
    print(f"{'field':<18}{'accuracy':>10}{'baseline':>10}{'lift':>8}")
    for field in SCORED_FIELDS:
        pairs = [(gold[i][field], preds[i][field]) for i in ids]
        acc = sum(t == p for t, p in pairs) / len(pairs)
        majority = Counter(t for t, _ in pairs).most_common(1)[0][1] / len(pairs)
        metrics[field] = {"accuracy": round(acc, 3),
                          "majority_baseline": round(majority, 3)}
        print(f"{field:<18}{acc:>10.3f}{majority:>10.3f}{acc - majority:>+8.3f}")

    # --- macro-F1 on claim_type ---------------------------------------
    pairs = [(gold[i]["claim_type"], preds[i]["claim_type"]) for i in ids]
    macro, per_class = macro_f1(pairs)
    metrics["claim_type"]["macro_f1"] = macro
    metrics["claim_type"]["per_class"] = per_class
    print(f"\nclaim_type macro-F1: {macro}")
    for c, v in sorted(per_class.items(), key=lambda kv: -kv[1]["support"]):
        print(f"  {c:<12} f1={v['f1']:<6} n={v['support']}")

    # --- severity confusion -------------------------------------------
    order = ["low", "medium", "high"]
    conf = defaultdict(int)
    for i in ids:
        conf[(gold[i]["severity"], preds[i]["severity"])] += 1
    print("\nseverity confusion (rows = true, cols = predicted)")
    print(f"{'':<8}" + "".join(f"{c:>8}" for c in order))
    for t in order:
        print(f"{t:<8}" + "".join(f"{conf[(t, p)]:>8}" for p in order))
    severe_miss = conf[("high", "low")] + conf[("low", "high")]
    metrics["severity"]["two_level_errors"] = severe_miss
    print(f"two-level errors (low<->high): {severe_miss}  <- the ones that matter")

    # --- recall on safety_critical ------------------------------------
    tp = sum(1 for i in ids if gold[i]["safety_critical"]
             and preds[i]["safety_critical"])
    fn = sum(1 for i in ids if gold[i]["safety_critical"]
             and not preds[i]["safety_critical"])
    rec = tp / (tp + fn) if tp + fn else None
    metrics["safety_critical"]["recall"] = round(rec, 3) if rec is not None else None
    print(f"\nsafety_critical recall: {rec}  (missed {fn} true cases)")

    # --- span grounding, over ALL extractions, not just labeled -------
    checks = []
    for rid, p in preds.items():
        if rid in narratives:
            g = is_grounded(TriageResult.model_validate(p),
                            narratives[rid])
            if g is not None:
                checks.append(g)
    rate = sum(checks) / len(checks) if checks else None
    declined = len(preds) - len(checks)
    metrics["span_grounding"] = {
        "rate": round(rate, 3) if rate is not None else None,
        "checked": len(checks),
        "declined_to_cite": declined,
    }
    print(f"\nspan grounding: {rate} over {len(checks)} spans "
          f"({declined} declined to cite)")

    metrics["weak_labels"] = weak_label_agreement(preds)

    OUT.mkdir(exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print("\nwrote out/metrics.json")


if __name__ == "__main__":
    main()
