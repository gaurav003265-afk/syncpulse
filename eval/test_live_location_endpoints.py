"""
Live endpoint verification script for location and reminders.
"""
import urllib.request
import json

base_url = "http://127.0.0.1:8000"

# 1. Update location for HH-0001
req_data = json.dumps({
    "latitude": 16.5123,
    "longitude": 80.6543,
    "accuracy_m": 3.5,
    "source": "GPS_CAPTURE"
}).encode("utf-8")

req = urllib.request.Request(
    f"{base_url}/api/households/HH-0001/location",
    data=req_data,
    headers={"Content-Type": "application/json"},
    method="PUT"
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print("1. Location update response:", res)

# 2. Get visits with worker coordinates
url = f"{base_url}/api/visits?worker_lat=16.5062&worker_lon=80.6480&limit=5"
with urllib.request.urlopen(url) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    visits = res["visits"]
    print(f"2. Retrieved {len(visits)} visits. Filter: {res['filter_tab']} | Worker loc: {res['worker_location']}")
    if visits:
        top = visits[0]
        print(f"   Top visit: {top['household_id']} | Tier: {top['priority_tier']} | Distance: {top['distance_display']} | Reason: {top['priority_reason']}")

# 3. Get reminders & follow-up gaps
url = f"{base_url}/api/reminders?as_of_date=2026-10-20"
with urllib.request.urlopen(url) as resp:
    rem = json.loads(resp.read().decode("utf-8"))
    reminders = rem["reminders"]
    gaps = rem["follow_up_gaps"]
    print(f"3. Monthly reminders: {len(reminders)} | Follow-up gaps: {len(gaps)} | Channel: {rem['notification_channel']}")
    if reminders:
        r0 = reminders[0]
        print(f"   Sample reminder: {r0['reminder_id']} ({r0['status']}) - {r0['service_name']} for {r0['beneficiary_name']}")
    if gaps:
        g0 = gaps[0]
        print(f"   Sample follow-up gap: {g0['follow_up_id']} ({g0['status']}) - {g0['task_description']}")

print("\nALL LIVE ENDPOINT CHECKS VERIFIED SUCCESSFULLY.")
