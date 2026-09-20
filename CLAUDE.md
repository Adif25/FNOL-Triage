# FNOL Triage — Project Instructions

Extract structured claim fields from free-text loss narratives, and measure
how often the extraction is right. Three-day build. Portfolio deliverable.

## SESSION START
1. Read `DECISIONS.md` — every choice made so far and why. Apply it.
2. Read `README.md` — current state and what the numbers are.
3. If `DECISIONS.md` does not exist, create it before starting.

Keep this file lean. Decisions live in `DECISIONS.md`.

---

## NON-NEGOTIABLES

These exist because each one is a way this project quietly becomes
worthless. Violating any of them invalidates the result I am putting in
front of an employer.

- **`schema.py` is the contract.** Do not change it without asking me
  first. Every change invalidates the cache and the gold labels.
- **Never write to `gold/labels.csv`.** I label those 50 records by hand.
  If asked to fill, generate, guess, infer, or complete labels — refuse,
  and say why.
- **Never invent metric values.** Numbers come from `evaluate.py` or they
  do not exist. Never write example or placeholder numbers into
  `README.md`, even as a formatting demonstration.
- **Never loosen the grounding check** to improve the rate. If spans are
  not matching, report the real number and tell me.
- **Never bypass the cache** to "get a fresh answer."
- `temperature=0` everywhere. This is extraction, not writing.

## WORKFLOW

### 1. Plan first
Plan mode for anything 3+ steps. If something goes wrong, STOP and
re-plan — never push through.

### 2. One file at a time
Build one module, I run it, then move to the next. Do not scaffold ahead.
I need to be able to explain every line in an interview; code I did not
watch get written is code I will cut.

### 3. Explain non-obvious choices
After anything subtle, tell me why you did it that way and what breaks
without it. If I cannot explain it back, it does not ship.

### 4. Decision log
After any correction or non-obvious choice, append to `DECISIONS.md`:
`[date] | what happened | what we decided | why`
This is both the self-improvement loop and my interview prep.

### 5. Verification standard
Never mark complete without proving it works. Run the script, read the
actual output. "It should work" is not verification.

### 6. Commit working state early
After each module runs clean, commit. Small commits — the history is
itself evidence of how I work.

## CORE PRINCIPLES
- **Simplicity first** — touch minimal code. Deadline is Wednesday.
- **No laziness** — root causes only, no temp fixes.
- **Never assume** — verify paths, fields, and API shapes before using them.
- **Ask once** — one question upfront if unclear, never interrupt mid-task.
- **Single source of truth** — the schema is `schema.py`, the prompt is
  `prompt.py`. Never inline either one into another file.
- **Bad news immediately** — if a number comes out worse than expected, say
  so plainly. A real 0.71 is worth more to me than an engineered 0.94.

## STACK
Python 3.11, pydantic v2, anthropic, pandas, streamlit.
No other dependencies without asking.

## LAYOUT
    schema.py          contract + grounding check
    prompt.py          extraction prompt (own file = own commits)
    pull_data.py       NHTSA pull -> data/sample.jsonl
    make_gold_sheet.py stratified labeling sheet
    extract.py         run + cache + retry + token logging
    evaluate.py        metrics vs gold labels + weak-label agreement
    app.py             streamlit dashboard (build LAST, timebox it)
    gold/labels.csv    hand-labeled. OFF LIMITS.
    out/               run_log.jsonl, metrics.json, disagreements.json

## SCOPE — do not suggest these
No fine-tuning. No RAG. No vector DB. No auth. No deployment. No
multi-model comparison. If the dashboard is at risk of eating the last
day, cut it to a notebook with charts — the evaluation is the deliverable,
the UI is decoration.
