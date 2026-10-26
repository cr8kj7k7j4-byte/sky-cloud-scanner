from research.backtest_opening_retest_reclaim_baseline_d import detect_reclaim_entry, fourth_tick_above

assert fourth_tick_above(10.00)==10.20
assert fourth_tick_above(49.90)==50.20

day={
 "session_open":10.0,
 "bars":{
  "09:00":{"open":10.0,"high":10.05,"low":9.99,"close":10.02},
  "09:01":{"open":10.02,"high":10.25,"low":10.01,"close":10.20},
  "09:02":{"open":10.18,"high":10.20,"low":9.98,"close":9.99},
  "09:03":{"open":10.0,"high":10.08,"low":9.99,"close":10.05},
 },
 "outcomes":{
  "09:04":{"entry_status":"ENTRY_4TICK_ZONE","entry":10.10,"raw_entry_open":10.10,
           "max_entry_4tick":10.20,"stop_aware_exit_30m":10.3,"stop_aware_exit_60m":10.5,
           "session_close":10.6,"high_60m":10.7,"low_60m":9.95,"high_to_close":10.8,
           "low_to_close":9.9,"open_stop_triggered":True}
 }
}
z=detect_reclaim_entry(day)
assert z["launch_time"]=="09:01"
assert z["retest_time"]=="09:02"
assert z["reclaim_time"]=="09:03"
assert z["entry_time"]=="09:04"
assert z["entry_status"]=="ENTRY_4TICK_ZONE"
print("PASS Opening Retest Reclaim Baseline D")
