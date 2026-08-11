"""Reference estimator using the randomized activation probe."""
import json
import os
import numpy as np
import pandas as pd

DATA = os.environ.get("NOTIFICATION_DATA", "/app/data")
OUT = os.environ.get("NOTIFICATION_OUT", "/app/notification_report.json")


def estimate(users, events, optouts, normalize=True):
    probe = users[users.randomized_probe == 1].copy()
    event_totals = events.assign(value=1/events.event_reporting_probability).groupby("user_id").value.sum()
    opt_totals = optouts.assign(value=1/optouts.optout_reporting_probability).groupby("user_id").value.sum()
    probe["sessions"] = probe.user_id.map(event_totals).fillna(0.0)
    probe["optout"] = probe.user_id.map(opt_totals).fillna(0.0)
    result_e={}; result_o={}
    for schedule in pd.read_csv(f"{DATA}/schedules.csv").schedule:
        d = probe[probe.schedule == schedule]
        vals=[]
        for state in (1, 0):
            a=d[d.notifications_enabled == state]
            w=1/(a.probe_inclusion_probability*a.schedule_assignment_probability*a.activation_probability)
            den=w.sum() if normalize else len(users)
            vals.append((float((w*a.sessions).sum()/den), float((w*a.optout).sum()/den)))
        result_e[schedule]=1000*(vals[0][0]-vals[1][0])
        result_o[schedule]=100*(vals[0][1]-vals[1][1])
    return result_e, result_o


def main():
    users=pd.read_csv(f"{DATA}/users.csv.gz"); events=pd.read_csv(f"{DATA}/engagement_events.csv.gz"); opts=pd.read_csv(f"{DATA}/optout_events.csv.gz")
    engagement,optout=estimate(users,events,opts)
    report={"engagement_effect_per_1000":engagement,"optout_effect_percentage_points":optout,"best_schedule":max(engagement,key=engagement.get)}
    with open(OUT,"w") as f: json.dump(report,f,indent=2); f.write("\n")


if __name__ == "__main__": main()

