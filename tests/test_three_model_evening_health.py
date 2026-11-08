from datetime import datetime
from zoneinfo import ZoneInfo

from research.three_model_evening_health import assess, classify

TZ=ZoneInfo("Asia/Taipei")


def run(id, hour, minute, event="schedule", conclusion="success"):
    t=datetime(2026,11,9,hour,minute,tzinfo=TZ)
    return {"id":id,"created_at":t.isoformat(),"status":"completed",
            "conclusion":conclusion,"head_branch":"main","event":event,
            "html_url":"https://github.com/placeholder"}


def test_monday_both_slots_have_run_evidence_but_not_cron_certification():
    now=datetime(2026,11,9,19,50,tzinfo=TZ)
    parent=[run(10,17,30),run(20,18,30)]
    children={"ledger":[run(11,17,31,event="workflow_dispatch")],
              "markout":[run(21,18,31,event="workflow_dispatch")]}
    result=assess(now,parent,children)
    assert result["status"]=="RUNS_COMPLETED_UNCORRELATED"
    assert result["cron_identity_certified"] is False
    assert result["gcs_content_verified"] is False
    assert result["slots"][1]["downstream"]["run_id"]==21


def test_manual_dispatch_cannot_replace_actual_schedule():
    now=datetime(2026,11,9,19,50,tzinfo=TZ)
    manual=[run(99,17,30,event="workflow_dispatch"),
            run(100,18,30,event="workflow_dispatch")]
    result=assess(now,manual,{"ledger":manual,"markout":manual})
    assert result["status"]=="ATTENTION"
    assert all(x["dispatcher"]["status"]=="MISSING_RUN" for x in result["slots"])


def test_missing_downstream_and_failure_flagged():
    now=datetime(2026,11,9,19,50,tzinfo=TZ)
    parent=[run(1,17,30),run(2,18,30,conclusion="failure")]
    result=assess(now,parent,{"ledger":[],"markout":[]})
    assert result["status"]=="ATTENTION"
    assert result["slots"][0]["downstream"]["status"]=="MISSING_RUN"
    assert result["slots"][1]["dispatcher"]["status"]=="RUN_NOT_SUCCESSFUL"


def test_before_evening_window_end_never_claims_failure():
    now=datetime(2026,11,9,18,40,tzinfo=TZ)
    result=assess(now,[],{"ledger":[],"markout":[]})
    assert result["status"]=="ATTENTION"  # 17:30 slot has expired
    assert result["slots"][1]["status"]=="AWAITING_WINDOW_END"


def test_weekend_and_disabled_do_not_fabricate_schedule():
    now=datetime(2026,11,8,20,0,tzinfo=TZ)
    assert assess(now,[],{},enabled=True)["status"]=="WEEKEND_NO_SCHEDULE_EXPECTED"
    assert assess(now,[],{},enabled=False)["status"]=="DISABLED_BY_CONFIGURATION"
    assert assess(now,[],{},enabled=True)["slots"]==[]


def test_no_future_or_wrong_branch_run_can_satisfy_expected_slot():
    start=datetime(2026,11,9,17,30,tzinfo=TZ)
    end=datetime(2026,11,9,18,25,tzinfo=TZ)
    rows=[run(1,17,25),run(2,18,26)]
    off=run(3,17,35)
    off["head_branch"]="research"
    rows.append(off)
    assert classify(rows,start,end,"schedule")["status"]=="MISSING_RUN"
