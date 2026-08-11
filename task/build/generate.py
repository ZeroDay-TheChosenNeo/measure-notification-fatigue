"""Generate deterministic adaptive notification logs and isolated population truth."""
from pathlib import Path
import io
import json
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "environment" / "data"
TRUTH = ROOT / "tests" / "truth"
SEED = 86173
SCHEDULES = np.array(["cadence", "ripple", "surge"])


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def contexts(rng, n):
    tenure = np.minimum(rng.gamma(2.2, 180.0, n).astype(int), 1800)
    prior = rng.negative_binomial(3, 3 / (3 + 7.0), n)
    locale = rng.choice(np.array(["core", "growth", "frontier"]), n, p=[.48, .34, .18])
    reliability = np.clip(rng.beta(11, 2.3, n), .35, .995)
    score = sigmoid(-1.0 + .12 * prior + .0012 * tenure + .7 * (locale == "core") + .5 * (reliability - .75))
    latent_intent = rng.normal(0, 1, n)
    return tenure, prior, locale, reliability, score, latent_intent


def potential_parameters(tenure, prior, locale, reliability, schedule, latent_intent):
    z = np.log1p(prior) - 1.8
    base_sessions = np.exp(1.22 + .17*z + .00022*tenure + .10*(locale == "core") + .28*latent_intent)
    effect = np.select(
        [schedule == "cadence", schedule == "ripple", schedule == "surge"],
        [.65 + 1.70*(prior >= 5) + .30*(locale == "core"),
         1.22 + .16*(locale == "frontier"),
         .80 + .08*(reliability > .9)])
    fatigue = np.select([schedule == "cadence", schedule == "ripple", schedule == "surge"], [.008, .004, .035])
    base_optout = sigmoid(-4.55 + .18*z - .35*(reliability-.8) + .15*(locale == "frontier"))
    active_optout = np.clip(base_optout + fatigue + .0015*np.maximum(prior-8, 0), 0, .35)
    return base_sessions, effect, base_optout, active_optout


def fixed_npz(path, **arrays):
    blobs = {}
    for name, array in arrays.items():
        b = io.BytesIO(); np.lib.format.write_array(b, np.asanyarray(array), allow_pickle=False)
        blobs[name + ".npy"] = b.getvalue()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(blobs):
            info = zipfile.ZipInfo(name, (2024, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, blobs[name])


def main():
    DATA.mkdir(parents=True, exist_ok=True); TRUTH.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED); n = 90000
    tenure, prior, locale, reliability, score, latent = contexts(rng, n)
    logits = np.column_stack([
        1.15 - 2.35*score + .45*(locale == "frontier"),
        .05 + .10*(locale == "growth"),
        -1.00 + 2.30*score + .35*(locale == "core")])
    probs = np.exp(logits); probs /= probs.sum(1, keepdims=True)
    idx = np.array([rng.choice(3, p=p) for p in probs]); schedule = SCHEDULES[idx]
    p_assign = probs[np.arange(n), idx]
    p_probe = np.clip(.22 + .13*(locale == "frontier") + .09*(prior < 4) + .04*(schedule == "surge"), .18, .55)
    probe = rng.random(n) < p_probe
    ordinary_p = sigmoid(-2.4 + 4.0*score + 1.35*latent + .75*(schedule == "surge") - .35*(schedule == "cadence"))
    p_enabled = np.where(probe, .5, ordinary_p)
    enabled = rng.random(n) < p_enabled
    state_p = np.where(enabled, p_enabled, 1-p_enabled)
    planned = np.select([schedule == "cadence", schedule == "ripple", schedule == "surge"], [6, 11, 22]).astype(int)
    delivered = np.where(enabled, rng.binomial(planned, reliability), 0)
    base, effect, p_opt0, p_opt1 = potential_parameters(tenure, prior, locale, reliability, schedule, latent)
    sessions_n = rng.poisson(base + enabled*effect)
    optout = rng.random(n) < np.where(enabled, p_opt1, p_opt0)
    users = pd.DataFrame({
        "user_id": np.arange(700000, 700000+n), "tenure_days": tenure, "prior_sessions_30d": prior,
        "locale_tier": locale, "push_reliability": reliability.round(6), "schedule": schedule,
        "schedule_assignment_probability": p_assign.round(8), "randomized_probe": probe.astype(int),
        "probe_inclusion_probability": p_probe.round(8), "notifications_enabled": enabled.astype(int),
        "activation_probability": state_p.round(8), "adaptive_suppression_score": score.round(8),
        "planned_notifications": planned, "delivered_notifications": delivered, "horizon_complete": 1})
    users.to_csv(DATA/"users.csv.gz", index=False, compression={"method":"gzip", "mtime":0})

    owner = np.repeat(np.arange(n), sessions_n)
    m = len(owner); via_p = np.clip(.01 + enabled[owner]*np.select([schedule[owner] == "cadence", schedule[owner] == "ripple", schedule[owner] == "surge"], [.08, .31, .78]), .01, .86)
    via = rng.random(m) < via_p
    delay = np.where(via, np.clip(rng.lognormal(2.2 + .55*(schedule[owner] == "surge"), 1.0, m), .1, 700), 0)
    day = rng.integers(0, 30, m)
    report_p = np.clip(.91 - .00075*delay - .11*(locale[owner] == "frontier") + .04*(reliability[owner] > .9), .32, .97)
    kept = rng.random(m) < report_p
    events = pd.DataFrame({"event_id": np.arange(9000000, 9000000+kept.sum()), "user_id": users.user_id.to_numpy()[owner[kept]],
        "event_day": day[kept], "via_notification": via[kept].astype(int), "open_delay_hours": delay[kept].round(4),
        "event_reporting_probability": report_p[kept].round(8)})
    events.to_csv(DATA/"engagement_events.csv.gz", index=False, compression={"method":"gzip", "mtime":0})

    oo = np.flatnonzero(optout); oo_day = rng.integers(0, 30, len(oo))
    oo_p = np.clip(.88 - .22*(locale[oo] == "frontier") - .16*(oo_day > 22) + .06*(reliability[oo] > .9), .38, .96)
    ok = rng.random(len(oo)) < oo_p
    opts = pd.DataFrame({"optout_id": np.arange(12000000, 12000000+ok.sum()), "user_id": users.user_id.to_numpy()[oo[ok]],
        "optout_day": oo_day[ok], "optout_reporting_probability": oo_p[ok].round(8)})
    opts.to_csv(DATA/"optout_events.csv.gz", index=False, compression={"method":"gzip", "mtime":0})
    pd.DataFrame({"schedule":SCHEDULES, "description":["six evenly spaced reminders", "eleven behavior-timed reminders", "twenty-two high-frequency reminders"]}).to_csv(DATA/"schedules.csv", index=False)

    # Fresh population stream; integrate outcome probabilities rather than reusing or resampling the shipped log.
    trng = np.random.default_rng(SEED + 41); nt = 4_000_000
    tt, pp, ll, rr, _, ii = contexts(trng, nt)
    engage=[]; opt=[]
    for s in SCHEDULES:
        ss = np.repeat(s, nt); _, eff, p0, p1 = potential_parameters(tt, pp, ll, rr, ss, ii)
        engage.append(1000*eff.mean()); opt.append(100*(p1-p0).mean())
    fixed_npz(TRUTH/"notification_truth.npz", schedule=SCHEDULES, engagement=np.array(engage), optout=np.array(opt))


if __name__ == "__main__": main()
