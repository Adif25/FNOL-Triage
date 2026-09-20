"""
Run triage extraction over a set of narratives.

Design notes (these are the parts worth being able to explain):

  Caching   -- every response is written to .cache/{id}.json before anything
               else happens. A crash at record 380 costs you nothing, and
               re-running to tweak the dashboard is free. Delete .cache/ when
               you change schema.py or prompt.py, or you will be evaluating
               stale outputs.

  Retry     -- one retry. A validation error is fed back into the prompt;
               most enum violations fix themselves this way. A transport
               error (rate limit, network) retries the original prompt
               unchanged -- the model never saw it. If a value fails
               validation twice, that's a signal your enum naming is
               ambiguous, not that you need more retries.

  Truncation-- recorded explicitly per record. Silent truncation corrupts
               results in a way that is nearly impossible to debug later.

  Logging   -- tokens and latency per record go to out/run_log.jsonl. You
               need those numbers for the writeup, and you cannot
               reconstruct them afterwards.
"""

import json
import os
import pathlib
import time

from pydantic import ValidationError

from prompt import SYSTEM, USER_TEMPLATE, RETRY_SUFFIX
from schema import TriageResult

# --- config -----------------------------------------------------------
MODEL = os.environ.get("TRIAGE_MODEL", "claude-haiku-4-5-20251001")
MAX_CHARS = 6000          # truncate narratives beyond this
CACHE = pathlib.Path(".cache")
OUT = pathlib.Path("out")
CACHE.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

# Set these from your provider's current pricing page before the final run.
# Left as None deliberately -- do not put a guessed number in your writeup.
USD_PER_MTOK_IN = None
USD_PER_MTOK_OUT = None
# ----------------------------------------------------------------------

_client = None


def client():
    """Lazy client. Swap this function to change providers -- nothing else
    in the file knows which vendor you are using."""
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def call_model(narrative: str, prior_error: str | None = None):
    """One model call. Returns (raw_tool_input, usage, latency_seconds)."""
    user = USER_TEMPLATE.format(narrative=narrative)
    if prior_error:
        user += RETRY_SUFFIX.format(error=prior_error)

    t0 = time.time()
    resp = client().messages.create(
        model=MODEL,
        max_tokens=1024,
        temperature=0,
        system=SYSTEM,
        tools=[{
            "name": "record_triage",
            "description": "Record the structured triage result.",
            "input_schema": TriageResult.model_json_schema(),
        }],
        tool_choice={"type": "tool", "name": "record_triage"},
        messages=[{"role": "user", "content": user}],
    )
    latency = time.time() - t0

    for block in resp.content:
        if block.type == "tool_use":
            return block.input, resp.usage, latency
    raise RuntimeError("model returned no tool_use block")


def extract_one(record_id: str, narrative: str) -> dict:
    """
    Extract one record. Always returns a dict with an 'ok' key -- failures
    are data, not exceptions, because the failure rate is a number you
    report.
    """
    cached = CACHE / f"{record_id}.json"
    if cached.exists():
        return json.loads(cached.read_text())

    truncated = len(narrative) > MAX_CHARS
    text = narrative[:MAX_CHARS]

    row = {"id": record_id, "truncated": truncated, "attempts": 0}
    err = None

    for attempt in (1, 2):
        row["attempts"] = attempt
        try:
            raw, usage, latency = call_model(text, prior_error=err)
            result = TriageResult.model_validate(raw)
            row.update({
                "ok": True,
                "result": result.model_dump(),
                "in_tokens": usage.input_tokens,
                "out_tokens": usage.output_tokens,
                "latency_s": round(latency, 3),
            })
            break
        except ValidationError as e:
            err = str(e)
            row["last_error"] = err[:500]
        except Exception as e:                     # transport, rate limit, etc.
            # Not the model's fault: log it, but retry the original prompt.
            row["last_error"] = f"{type(e).__name__}: {e}"[:500]
            time.sleep(2 * attempt)                # crude backoff
    else:
        row["ok"] = False

    cached.write_text(json.dumps(row, indent=2))
    return row


def load_records(path="data/sample.jsonl"):
    """Yield (id, narrative). Blank narratives are skipped and counted --
    never silently dropped."""
    skipped = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            narrative = (rec.get("narrative") or "").strip()
            if len(narrative) < 20:
                skipped += 1
                continue
            yield str(rec["id"]), narrative
    print(f"skipped {skipped} records with missing or trivial narratives")


def main():
    rows = []
    for i, (rid, narrative) in enumerate(load_records(), 1):
        rows.append(extract_one(rid, narrative))
        if i % 25 == 0:
            print(f"  {i} processed")

    with open(OUT / "run_log.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    ok = [r for r in rows if r.get("ok")]
    tin = sum(r.get("in_tokens", 0) for r in ok)
    tout = sum(r.get("out_tokens", 0) for r in ok)

    print(f"\n{len(ok)}/{len(rows)} extracted "
          f"({100 * (1 - len(ok) / max(len(rows), 1)):.1f}% failure rate)")
    print(f"retried: {sum(1 for r in rows if r['attempts'] > 1)}")
    print(f"truncated: {sum(1 for r in rows if r['truncated'])}")
    print(f"tokens: {tin} in / {tout} out")
    if USD_PER_MTOK_IN and USD_PER_MTOK_OUT:
        cost = tin / 1e6 * USD_PER_MTOK_IN + tout / 1e6 * USD_PER_MTOK_OUT
        print(f"cost: ${cost:.3f}  (${cost / max(len(ok), 1) * 1000:.2f} per 1k)")


if __name__ == "__main__":
    main()
