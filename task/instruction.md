# Measure notification engagement and fatigue

The growth team logged a 30-day rollout of three notification schedules. Estimate, for each registered schedule, its population-average effect of enabling that schedule rather than assigning the same users to a ghost holdout. Report:

- the change in **meaningful engagement sessions per 1,000 eligible users** over 30 days; and
- the change in the **30-day opt-out rate in percentage points**.

The target population is the full eligible-user frame represented by `users.csv.gz`, not only users who received a notification or generated a recorded event. A schedule's effect compares `notifications_enabled = 1` with `notifications_enabled = 0` for that schedule. Set `best_schedule` to the registered schedule with the largest engagement effect.

Write `/app/notification_report.json` with this shape:

```json
{
  "engagement_effect_per_1000": {"cadence": 0.0, "ripple": 0.0, "surge": 0.0},
  "optout_effect_percentage_points": {"cadence": 0.0, "ripple": 0.0, "surge": 0.0},
  "best_schedule": "cadence"
}
```

## Files

`/app/data/users.csv.gz` contains one row per eligible user:

- `user_id`: stable user identifier.
- `tenure_days`: account age at rollout start.
- `prior_sessions_30d`: meaningful sessions in the preceding 30 days.
- `locale_tier`: registered locale group (`core`, `growth`, or `frontier`).
- `push_reliability`: pre-rollout probability that a push reaches the device.
- `schedule`: registered schedule assigned to the user.
- `schedule_assignment_probability`: probability of that schedule assignment under the rollout design.
- `randomized_probe`: 1 when the user entered the randomized activation probe.
- `probe_inclusion_probability`: probability of randomized-probe inclusion.
- `notifications_enabled`: 1 when the assigned schedule was activated; 0 denotes its ghost holdout.
- `activation_probability`: probability of the observed activation state within the applicable rollout path (thus it is `P(enabled=1)` for enabled rows and `P(enabled=0)` for ghost rows).
- `adaptive_suppression_score`: pre-rollout score used by ordinary delivery suppression.
- `planned_notifications`: number prescribed by the assigned schedule over 30 days.
- `delivered_notifications`: number actually delivered during the window.
- `horizon_complete`: 1 when the full 30-day outcome horizon elapsed. All shipped rows have a complete horizon.

`/app/data/engagement_events.csv.gz` contains recorded meaningful engagement sessions:

- `event_id`: stable event identifier.
- `user_id`: user identifier joining to `users.csv.gz`.
- `event_day`: integer day 0 through 29 on which the session occurred.
- `via_notification`: 1 when the session followed a notification open, otherwise 0.
- `open_delay_hours`: elapsed hours from delivery to the open for notification-originated sessions; 0 otherwise.
- `event_reporting_probability`: probability that this event is present in the log.

`/app/data/optout_events.csv.gz` contains recorded opt-outs (users without a recorded opt-out have no row):

- `optout_id`: stable opt-out event identifier.
- `user_id`: user identifier joining to `users.csv.gz`.
- `optout_day`: integer day 0 through 29 of opt-out.
- `optout_reporting_probability`: probability that this opt-out is present in the log.

`/app/data/schedules.csv` contains:

- `schedule`: registered schedule name.
- `description`: human-readable schedule description.

The recorded design probabilities are positive on their support. Conditional on the pre-rollout fields, schedule assignment and randomized-probe inclusion follow their recorded probabilities. Within the randomized probe, activation is independent of potential 30-day outcomes conditional on the pre-rollout fields and follows the recorded activation probability. Event and opt-out reporting are independent of the corresponding outcome conditional on their recorded fields and follow the recorded reporting probabilities. The randomized probe is representative of the eligible frame after accounting for its recorded inclusion probabilities.

