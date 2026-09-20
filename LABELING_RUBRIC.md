# Labeling rubric — read this before you label anything

## The rule that protects the whole project

**Label all 50 records before you look at a single model prediction.**

Once you have seen the model's answer you cannot unsee it. Your labels
drift toward agreeing with it, your accuracy number becomes an echo, and
the project quietly stops measuring anything. If this happens, the number
in your portfolio is fiction and you cannot defend it in an interview.

Open `out/run_log.jsonl` only after `gold/labels.csv` is finished.

The sheet already has the narrative text in column B, so you can label
entirely inside one spreadsheet. Open `gold/labels.csv` in Google Sheets,
widen column B, turn on text wrapping, and work down the rows.

The 50 records are **stratified**, not random — 40% of them involve a
crash, fire, or injury, against 7% in the full corpus. That is on purpose
(see `make_gold_sheet.py`), and it means you will see more dramatic
records than are typical. Label what the narrative says; do not adjust
for the fact that severe cases feel over-represented.

## Second rule: decide the hard cases in writing

When you hit an ambiguous record, do not just pick one and move on. Write
the tie-breaker at the bottom of this file, then keep going. At the end,
re-check your earlier rows against every rule you added. Budget 20 minutes
for that pass — it is the difference between 50 labels and 50 guesses.

---

## claim_type

| value | use when |
|---|---|
| `collision` | impact with another vehicle or object |
| `mechanical` | component failure: brakes, transmission, electrical, engine |
| `fire` | fire or smoke, regardless of cause |
| `theft` | vehicle or contents taken |
| `weather` | hail, flood, wind, ice as the primary cause |
| `injury` | person hurt and that is the *substance* of the report |
| `other` | none of the above fits without stretching |

If two apply, pick the one that **drives the cost of the claim**. A crash
caused by brake failure is `collision` — the collision is what gets paid out.

## severity

| value | use when |
|---|---|
| `high` | injury, fire, rollover, total loss, or a safety-critical failure |
| `medium` | damage requiring repair, no injury reported |
| `low` | cosmetic or minor, no injury, vehicle still operable |

Severity is about **potential claim cost and urgency**, not how upset the
writer sounds. An all-caps furious narrative about a rattling trim panel
is still `low`.

## injury_reported

`true` **only** if the narrative states a person was hurt. Not "could have
been." Not "nearly." Stated only.

## safety_critical

`true` if the described failure could cause loss of control, fire, or
injury *if it happened again*. A brake failure at 5mph in a parking lot is
still `true` — the same failure at highway speed kills someone.

This is the field where you should lean toward `true` when torn. Missing a
real safety case is much worse than one false alarm, which is why the
evaluation reports **recall** here instead of accuracy.

## routing

| value | use when |
|---|---|
| `urgent_escalation` | `injury_reported` or `safety_critical` is true |
| `auto_process` | `low` severity **and** nothing important missing |
| `adjuster_review` | everything else — the honest default |

Routing is mostly determined by the fields above. If you find yourself
routing against them, that is a sign your severity call was wrong — go back
and fix the severity rather than the routing.

---

## Tie-breakers I added while labeling

Write them here as you go. Date each one.

- EXAMPLE ONLY, not a real rule — 2026-09-20 — narratives describing a recall notice with no
  incident are `other` / `low`, not `mechanical`, since no loss occurred.
-
-
