# FNOL Triage

LLM extraction of structured claim fields from free-text first-notice-of-loss
narratives, with routing recommendations and a measured accuracy baseline.

## The problem

Claims intake starts with unstructured text — a person describing what
happened. Before anything can be routed, someone reads it and keys in claim
type, severity, whether anyone was hurt, and what information is still
missing. This extracts those fields automatically, cites the text supporting
each judgment, and flags low-confidence cases for human review.

It is designed as triage, not automation: the model decides **what a human
looks at first**, not what gets paid.

## Results

<!-- Fill from out/metrics.json after evaluation. Do not write numbers here
     by hand. -->

**Hand-labeled set (n=50, stratified)**

| metric | value | majority baseline |
|---|---|---|
| claim_type accuracy | — | — |
| claim_type macro-F1 | — | |
| severity accuracy | — | — |
| safety_critical recall | — | |
| two-level severity errors | — | |

**Full corpus (n=500)**

| metric | value |
|---|---|
| span grounding rate | — |
| extraction failure rate | — |
| agreement, crash flag -> collision | — |
| agreement, injuries>0 -> injury_reported | — |
| cost per 1,000 records | — |

Two evaluation sets, because they answer different questions. The 50
hand-labeled records measure the full schema carefully but are
deliberately over-weighted toward rare classes, so their accuracy is not
representative of the corpus. The 500-record weak-label agreement runs at
the true class mix but only covers three fields, against labels that are
themselves imperfect.

## Limitations

- Public complaint narratives are a proxy for real FNOL text, which differs
  in structure and would need domain-specific prompt tuning.
- One labeler. Two annotators would disagree on some records; the true
  ceiling on measurable accuracy is below 100%.
- 50 labeled records is a small evaluation set — treat differences of a few
  points as noise.
- The hand-labeled set is stratified toward rare classes (40% crash/fire/
  injury vs 7% in the corpus). This makes rare-class metrics measurable and
  makes overall accuracy on that set optimistic relative to the corpus.
- NHTSA structured fields are self-reported alongside the narrative and are
  not independent ground truth. Some are plainly inconsistent — record
  11748457 reports 3 injuries on an air-conditioning complaint. They are
  used as a coverage signal, never as a correctness standard.

## Run

    pip install pydantic anthropic pandas streamlit
    export ANTHROPIC_API_KEY=...
    python pull_data.py      # 500 narratives -> data/sample.jsonl
    python make_gold_sheet.py  # stratified labeling sheet
    python extract.py        # writes out/run_log.jsonl
    # hand-label gold/labels.csv now, before looking at run_log
    python evaluate.py       # writes out/metrics.json
    streamlit run app.py
