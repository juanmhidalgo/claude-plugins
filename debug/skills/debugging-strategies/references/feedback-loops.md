# Building a feedback loop

Adapted from [mattpocock/skills `diagnosing-bugs`](https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnosing-bugs/SKILL.md). Copyright (c) 2026 Matt Pocock, MIT License.

A feedback loop is one command that goes **red** on this exact bug and green once it is fixed. Step 1 of `/debug:debug` does not end until you have run one.

## Ways to build one, roughly in this order

1. **Failing test** at whatever level reaches the bug: unit, integration, end-to-end.
2. **curl / HTTP script** against a running dev server, asserting on status and body.
3. **CLI invocation** with a fixture input, `diff`-ed against a known-good output.
4. **Headless browser script** (Playwright) that drives the UI and asserts on the DOM, console, or network.
5. **Replay a captured trace**: save a real request, payload, or event log to disk and replay it through the code path alone.
6. **Throwaway harness**: start the smallest subset of the system (one service, fake dependencies) that reaches the bug with a single call.
7. **Property / fuzz loop**: for "sometimes wrong output", run 1000 random inputs and look for the failure.
8. **Bisect harness**: if the bug appeared between two known states (commit, dataset, version), script "set up state X, check" and hand it to `git bisect run`.
9. **Differential loop**: run the same input through the old and new version (or two configs) and diff the outputs.
10. **Human in the loop**, last resort: when a person must click, write a short script that prints each step, waits for them, and captures what they report, so the loop stays structured. The Bash tool cannot answer an interactive prompt, so the user runs that script themselves (`! ./repro.sh`) and the output lands in the conversation.

## Tighten it

Once you have *a* loop, treat it as a product:

- **Faster**: cache setup, skip unrelated initialisation, narrow the test selection.
- **Sharper**: assert on the specific symptom, not "didn't crash".
- **More deterministic**: pin time, seed randomness, isolate the filesystem, stub the network.

A 30-second flaky loop is barely better than none; a 2-second deterministic one is what makes the rest of the process mechanical.

## Flaky bugs

The goal is a **higher reproduction rate**, not a clean repro. Loop the trigger 100 times, run in parallel, add load, narrow timing windows, inject sleeps. A bug that shows up 50% of the time can be debugged; one at 1% cannot, so keep raising the rate.

## Performance bugs

Logs rarely help. Measure a baseline first (timing harness, profiler, query plan, `EXPLAIN ANALYZE`), make that measurement the loop, then bisect against it. Measure first, fix second.

## Secrets

Loops and captured artifacts often carry credentials. Read them from environment variables rather than writing them into the script, and redact any token, cookie, or auth header before showing output: write `<REDACTED>` in its place and quote only the lines that carry the signal.
