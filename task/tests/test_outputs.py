import json, math, os
import numpy as np
import pytest

ARTIFACT=os.environ.get("NOTIFICATION_ARTIFACT","/app/notification_report.json")
TRUTH=os.environ.get("NOTIFICATION_TRUTH","/tests/truth/notification_truth.npz")
SCHEDULES=("cadence","ripple","surge")
ENG_TOL=120.0
OPT_TOL=.42

def number(x,where):
    if isinstance(x,bool): pytest.fail(f"{where}: boolean is not a number")
    try: y=float(x)
    except (TypeError,ValueError): pytest.fail(f"{where}: expected a number")
    assert math.isfinite(y),f"{where}: must be finite"; return y

@pytest.fixture(scope="module")
def submitted():
    if not os.path.isfile(ARTIFACT): pytest.fail(f"{ARTIFACT} was not produced")
    with open(ARTIFACT) as f: return json.load(f)

@pytest.fixture(scope="module")
def truth():
    z=np.load(TRUTH); return {str(s):(float(e),float(o)) for s,e,o in zip(z["schedule"],z["engagement"],z["optout"])}

def val(doc,key,s):
    assert isinstance(doc.get(key),dict),f"{key} must be an object"; assert s in doc[key],f"{key} missing {s}"; return number(doc[key][s],f"{key}.{s}")

def test_schema(submitted):
    assert submitted.get("best_schedule") in SCHEDULES
    for s in SCHEDULES: val(submitted,"engagement_effect_per_1000",s); val(submitted,"optout_effect_percentage_points",s)

@pytest.mark.parametrize("schedule",SCHEDULES)
def test_engagement(submitted,truth,schedule):
    assert abs(val(submitted,"engagement_effect_per_1000",schedule)-truth[schedule][0]) <= ENG_TOL

@pytest.mark.parametrize("schedule",SCHEDULES)
def test_optout(submitted,truth,schedule):
    assert abs(val(submitted,"optout_effect_percentage_points",schedule)-truth[schedule][1]) <= OPT_TOL

def test_best(submitted,truth):
    want=max(SCHEDULES,key=lambda s:truth[s][0]); assert submitted["best_schedule"]==want
