# Measure Notification Fatigue

A hard, programmatically verified causal-inference task built around an adaptively suppressed notification rollout. The submission must recover 30-day population engagement and opt-out effects for three schedules despite nonuniform schedule assignment, randomized-probe selection, ghost holdouts, delayed event reporting, and production suppression.

## Why the task is difficult

The production dashboard is self-confirming: high-intent users are more likely to survive adaptive suppression, and a delivered-message CTR reports `surge` as the winner. The target is instead an eligible-user population contrast between activation and the corresponding ghost holdout. Sparse opt-out records and delayed engagement telemetry add distinct observation mechanisms.

The instruction defines the estimand, the complete data dictionary, and the identifying assumptions without prescribing an estimator. Hidden truth comes from 4,000,000 fresh population contexts on an independent random stream. Outcome expectations are integrated rather than drawn, and the shipped rollout is never reused.

## Calibration evidence

Independent truth (engagement sessions per 1,000 / opt-out percentage points):

| Schedule | Engagement | Opt-out |
|---|---:|---:|
| cadence | 1894.4 | 1.02 |
| ripple | 1248.8 | 0.62 |
| surge | 821.1 | 3.72 |

The reference self-normalized estimator has worst errors 96.7 sessions and 0.284 percentage points. A distinct locale-poststratified design estimator has worst errors 115.9 and 0.284. Both are inside verifier tolerances of 120 and 0.42.

Seven plausible wrong analyses fail. Their worst engagement/opt-out errors are respectively: unweighted probe 401.3/0.363; omitted schedule weights 284.0/0.288; omitted reporting weights 274.2/0.897; active mean without the ghost contrast 4133.6/1.198; ordinary all-row contrast 973.8/0.098; all-row design weighting 154.7/0.152; and delivered-message CTR 1789.5/1.173. The nearest wrong route remains 34.7 sessions outside tolerance. Delivered-message CTR ranks `surge` first, opposite the true `cadence` winner; the true winner leads by 645.6 sessions per 1,000.

## Layout and validation

- `task/build/generate.py` deterministically rebuilds shipped data and hidden truth.
- `task/build/calibrate.py` reproduces the separation table.
- `task/solution/` contains the isolated oracle.
- `task/tests/` contains the artifact verifier and hidden truth.
- `scripts/run_task.sh` runs the two-phase oracle harness; tests enter only after the solver exits.
- GitHub Actions checks byte reproducibility and requires oracle reward `1` and no-op reward `0`.

Native check:

```sh
python3 task/build/generate.py
NOTIFICATION_DATA="$PWD/task/environment/data" NOTIFICATION_OUT="$PWD/notification_report.json" python3 task/solution/solve.py
NOTIFICATION_ARTIFACT="$PWD/notification_report.json" NOTIFICATION_TRUTH="$PWD/task/tests/truth/notification_truth.npz" pytest -q task/tests/test_outputs.py
python3 task/build/calibrate.py
```

Released under the MIT License.
