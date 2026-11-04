# Evidence-backed content roadmap

This roadmap turns engineering work into public explanations without making claims ahead of the
evidence. A topic is “ready” only when its supporting artifact is committed and reproducible.

| Topic | Engineering artifact | Status | Claim allowed now |
|---|---|---|---|
| Completion versus clean execution | Raw traces, proof manifest, trajectory audit | Ready | The scorer tagged 34 completed Sol/v1 executions as `wrong_tool` |
| How the evaluation system works | Architecture diagram, ADRs, scoring documentation | Ready | The harness scores outcomes, tool choice, arguments, sequence, grounding, and policy attempts |
| Why an evaluator can be wrong | `refund-elig-01` trace and declared allowed-tool set | Ready | One extra successful lookup caused a precision penalty under the current specification |
| Strict versus flexible trajectories | New rubric plus rescored artifacts | Not run | Describe the proposed experiment only; do not claim an improvement |
| Held-out evaluation | Independently authored cases and preregistered protocol | Not built | State this as the next validation step |
| Latency/cost trade-offs | Per-case timings and conservative cost estimates | Ready with caveats | Report descriptive measurements for these exact runs, not general performance |

## Recommended sequence

1. **Evaluator disagreement:** explain the 144 completion / 110 clean gap and show the concrete
   `refund-elig-01` trace.
2. **Architecture walkthrough:** show where policy checks, trace capture, and scoring sit in the
   LangGraph loop.
3. **Evaluation specification:** separate correctness requirements from efficiency preferences;
   label this a design proposal until a new rubric is implemented.
4. **Rescoring experiment:** implement the new rubric, preserve the original scores, and publish
   both result sets with a migration note.
5. **Held-out set:** preregister expectations before running models, then report the limitations
   and any scorer disagreements.

## Publication rule

Do not turn a planned test into a past-tense achievement. Link to the most specific evidence page,
state the sample size as 52 unique cases, and distinguish repeated executions from independent
tasks.

