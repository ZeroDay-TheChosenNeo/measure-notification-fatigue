"""Print separation evidence for valid and tempting invalid analyses."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"solution"))
import solve

DATA=ROOT/"environment"/"data"
solve.DATA=str(DATA)
SCHEDULES=("cadence","ripple","surge")
U=pd.read_csv(DATA/"users.csv.gz")
E=pd.read_csv(DATA/"engagement_events.csv.gz")
O=pd.read_csv(DATA/"optout_events.csv.gz")
Z=np.load(ROOT/"tests"/"truth"/"notification_truth.npz")
TE=dict(zip(Z["schedule"],Z["engagement"])); TO=dict(zip(Z["schedule"],Z["optout"]))
event_ipw=E.assign(v=1/E.event_reporting_probability).groupby("user_id").v.sum()
opt_ipw=O.assign(v=1/O.optout_reporting_probability).groupby("user_id").v.sum()
raw_event=E.groupby("user_id").size(); raw_opt=O.groupby("user_id").size()

def route(rows, weights, corrected=True, subtract=True):
    d=rows.copy(); d["y"]=d.user_id.map(event_ipw if corrected else raw_event).fillna(0); d["o"]=d.user_id.map(opt_ipw if corrected else raw_opt).fillna(0)
    re={}; ro={}
    for s in SCHEDULES:
        q=d[d.schedule==s]; vals=[]
        for a in (1,0):
            x=q[q.notifications_enabled==a]; w=weights(x)
            vals.append(((w*x.y).sum()/w.sum(),(w*x.o).sum()/w.sum()))
        re[s]=1000*(vals[0][0]-(vals[1][0] if subtract else 0)); ro[s]=100*(vals[0][1]-(vals[1][1] if subtract else 0))
    return re,ro

valid_hajek=solve.estimate(U,E,O,True)
valid_ht=solve.estimate(U,E,O,False)
p=U[U.randomized_probe==1]

def poststratified():
    d=p.copy(); d["y"]=d.user_id.map(event_ipw).fillna(0); d["o"]=d.user_id.map(opt_ipw).fillna(0)
    mix=U.locale_tier.value_counts(normalize=True); re={}; ro={}
    for s in SCHEDULES:
        outcomes=[]
        for a in (1,0):
            means=[]
            for loc,share in mix.items():
                x=d[(d.schedule==s)&(d.notifications_enabled==a)&(d.locale_tier==loc)]
                w=1/(x.probe_inclusion_probability*x.schedule_assignment_probability*x.activation_probability)
                means.append((share*(w*x.y).sum()/w.sum(),share*(w*x.o).sum()/w.sum()))
            outcomes.append(tuple(map(sum,zip(*means))))
        re[s]=1000*(outcomes[0][0]-outcomes[1][0]); ro[s]=100*(outcomes[0][1]-outcomes[1][1])
    return re,ro
routes={
 "valid_hajek":valid_hajek,
 "valid_poststratified":poststratified(),
 "probe_unweighted":route(p,lambda x:np.ones(len(x))),
 "probe_no_schedule_weight":route(p,lambda x:1/(x.probe_inclusion_probability*x.activation_probability)),
 "probe_no_reporting_weight":route(p,lambda x:1/(x.probe_inclusion_probability*x.schedule_assignment_probability*x.activation_probability),False),
 "enabled_mean_not_contrast":route(p,lambda x:1/(x.probe_inclusion_probability*x.schedule_assignment_probability*x.activation_probability),True,False),
 "ordinary_all_rows":route(U,lambda x:np.ones(len(x))),
 "all_rows_design_weighted":route(U,lambda x:1/(x.schedule_assignment_probability*x.activation_probability)),
}

# A common dashboard ratio: recorded notification-originated sessions per delivery.
joined=E[E.via_notification==1].merge(U[["user_id","schedule"]],on="user_id")
ctr={s:1000*len(joined[joined.schedule==s])/max(1,U.loc[U.schedule==s,"delivered_notifications"].sum()) for s in SCHEDULES}
routes["delivered_message_ctr"]=(ctr,{s:100*len(O.merge(U.loc[(U.schedule==s)&(U.delivered_notifications>0),["user_id"]],on="user_id"))/max(1,(U.schedule==s).sum()) for s in SCHEDULES})

for name,(re,ro) in routes.items():
    ee=max(abs(re[s]-TE[s]) for s in SCHEDULES); oe=max(abs(ro[s]-TO[s]) for s in SCHEDULES)
    print(f"{name:28s} eng_max={ee:8.3f} opt_max={oe:6.3f} winner={max(re,key=re.get):7s} values="+", ".join(f"{s}:{re[s]:.1f}/{ro[s]:.2f}" for s in SCHEDULES))
print("truth",", ".join(f"{s}:{TE[s]:.1f}/{TO[s]:.2f}" for s in SCHEDULES))
