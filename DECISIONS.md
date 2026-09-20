# Decisions

Every non-obvious choice and why. Read this before the interview.

Format: `[date] | what happened | what we decided | why`

---

- `2026-09-20` | Needed loss narratives; real claims data is not public |
  Used NHTSA vehicle safety complaints rather than LLM-generated synthetic
  text | Generating narratives with an LLM and then extracting from them
  with an LLM is circular — the accuracy number would measure nothing.

- `2026-09-20` | Corpus is heavily imbalanced (5% crash, 2% injury, 1%
  fire) | Stratified the 50-record gold set to ~40% rare-class instead of
  sampling at random | A random 50 gives ~2 crashes and 0 fires, so every
  rare-class metric would rest on one or two records. Tradeoff: accuracy on
  the gold set is optimistic relative to the corpus, disclosed in README.

- `2026-09-20` | NHTSA records structured flags (crash/fire/injuries)
  beside each narrative | Used them as a second evaluation axis across all
  500, not as ground truth | They are self-reported alongside the narrative
  so they are correlated, and some are plainly wrong (record 11748457 logs
  3 injuries on an A/C complaint). Good for coverage at the true class mix,
  useless as a correctness standard.

- `2026-09-20` | Needed to detect hallucinated justifications | Required
  `evidence_span` to be a verbatim substring of the source | Makes
  hallucination programmatically checkable with `span in narrative`, which
  turns a vague worry into a reported number.

- `2026-09-20` | Could have imported `sklearn.metrics.f1_score` | Wrote
  macro-F1 by hand instead | ~40 lines, no dependency, and I can explain
  exactly what it computes when asked.

-
