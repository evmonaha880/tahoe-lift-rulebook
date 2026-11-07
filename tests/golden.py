"""Golden tests for the parser. Every case is a real post wording found in the audit, with the events it MUST produce
and the event types it must NOT produce. usage: python3 -I tests/golden.py   (exit 1 if anything fails)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from parse_posts import parse_post
# (text, must=[(event_type, lift, cause_or_None_for_any)], must_not=[(event_type, lift_or_None_for_any)])
H, C, D, R, P, S, W, O = "hold_start", "closed_day", "delay", "reopen", "partial", "scheduled_opening", "warning", "other"
CASES = [
 ("Mtn Meadow and the Tram are now on wind hold. The Base to Base Gondola and High Camp Carpet are off the schedule for the rest of the day.",
  [(H, "Mountain Meadow", "wind"), (H, "Tram", "wind"), (C, "Base to Base Gondola", None), (C, "High Camp Carpet", None)], []),
 ("All lifts are currently on wind hold.", [(H, "ALL", "wind")], [(C, None)]),
 ("Alpine Update: The following lifts are open: Treeline Cirque Meadow Kangaroo All other scheduled lifts are on wind hold.",
  [(H, "ALL_OTHER", "wind"), (R, "Treeline Cirque", None)], []),
 ("Summit is off wind hold and open to the public #alpinelifts", [(R, "Summit", "wind")], [(H, None)]),
 ("The Tram is going on wind hold. Downloads only at this time.", [(H, "Tram", "wind"), (P, "Tram", None)], []),
 ("Gold Coast is on mechanical hold, Shirley and Red Dog are open, Belmont will be closed for the remainder of the day.",
  [(H, "Gold Coast", "mechanical"), (R, "Shirley Lake", None), (R, "Red Dog", None), (C, "Belmont", None)], []),
 ("Update: Off the schedule for the day: Base to Base Gondola Funitel Tram",
  [(C, "Base to Base Gondola", None), (C, "Funitel", None), (C, "Tram", None)], [(R, None)]),
 ("The following lifts are on delay, all other scheduled lifts at Palisades are open. Emigrant Gold Coast Granite Chief",
  [(D, "Emigrant", None), (D, "Gold Coast", None), (D, "Granite Chief", None)], [(S, None)]),
 ("Emigrant, Granite Chief, and Siberia will have a delayed opening due to high winds on the upper mountain.",
  [(D, "Emigrant", "wind"), (D, "Granite Chief", "wind"), (D, "Siberia", "wind")], []),
 ("Shirley Lake is closed for the day due to lightning.", [(C, "Shirley Lake", "weather")], []),
 ("Summit is on wind hold. #palisadesops", [(H, "Summit", "wind")], []),
 ("Red Dog is on a maintenance hold. #palisadesops", [(H, "Red Dog", "mechanical")], []),
 ("Alpine Meadows Road is now open. #palisadesops", [], [(R, None), (H, None), (C, None)]),
 ("Safety Alert: Ski & ride predictably and in control. Allow 10' of space between you and others.", [], [(H, None), (C, None), (R, None)]),
 ("KT-22 is on mechanical hold. The mothership needs a quick hose fix and should be back up and running in about an hour.",
  [(H, "KT-22", "mechanical")], [(R, None)]),
 ("Big Blue has been added to the schedule today and is now open! #palisadesops", [(S, "Big Blue", None), (R, "Big Blue", None)], []),
 ("Siberia and Gold Coast will be opening at 12:50.", [(D, "Siberia", None), (D, "Gold Coast", None)], [(S, None)]),
 ("Headwall now on Wind Hold. #palisadesops", [(H, "Headwall", "wind")], []),
 ("The High Camp Carpet will be closing at 2pm today for maintenance. #palisadesops", [(C, "High Camp Carpet", None)], [(P, None)]),
 ("Treeline Cirque to the mid-station is open #palisadesops", [(P, "Treeline Cirque", None)], []),
 ("Granite Chief is off Patrol Hold and open for skiing and riding! #squawlifts", [(R, "Granite Chief", "patrol")], [(H, None)]),
 ("Palisades: Mostly sunny, with a high near 29. NW winds of 15 to 25 mph, with gusts as high as 40 mph.", [], [(H, None), (C, None), (R, None), (D, None)]),
 ("Palisades Wind Closures: - Base to Base - Tram - Bailey’s", [(C, "Base to Base Gondola", "wind"), (C, "Tram", "wind"), (C, "Bailey's Beach", "wind")], []),
 ("Alpine Update: Wind Hold: Base to Base Summit Roundhouse Off Schedule: Scott #palisadesops",
  [(H, "Base to Base Gondola", "wind"), (H, "Summit", "wind"), (H, "Roundhouse", "wind"), (C, "Scott", None)], [(S, None)]),
 ("For Alpine, we expect Roundhouse, Summit, Subway at 9am. All other scheduled lifts are on delay due to icing. #palisadesops",
  [(D, "ALL_OTHER", "weather")], []),
 ("The Base to Base Gondola is now on a stage 2 wind alert. Please return to the base area you plan to depart from.", [(W, "Base to Base Gondola", "wind")], [(H, None)]),
 ("Sherwood is on delay and Treeline Cirque will be open to mid-station until Sherwood goes.", [(D, "Sherwood", None), (P, "Treeline Cirque", None)], []),
 ("Palisades Open at 9am: Base to Base Tram Funitel KT Red Dog Resort Wind Hold: Solitude Bailey's Delayed: Wa She Shu Gold Coast",
  [(S, "Tram", None), (H, "Solitude", "wind"), (H, "Bailey's Beach", "wind"), (D, "Wa She Shu", None), (D, "Gold Coast", None)], [(H, "Tram")]),
 ("The Base to Base Gondola is on wind hold. Kangaroo will have a Delayed Opening. #palisadesops", [(H, "Base to Base Gondola", "wind"), (D, "Kangaroo", None)], []),
 ("Hot Wheels and Meadow Chair are now off Wind Hold and open to the public. #alpinelifts", [(R, "Hot Wheels", "wind")], [(H, None)]),
]
b = {"id": "t", "created_at": "2024-01-13T17:01:00.000Z"}
fails = 0
for i, (text, must, must_not) in enumerate(CASES, 1):
    ev = parse_post({**b, "text": text}); have = {(e["event_type"], e["lift"], e["cause"]) for e in ev}
    bad = [m for m in must if not any(h[0] == m[0] and h[1] == m[1] and (m[2] is None or h[2] == m[2]) for h in have)]
    bad_not = [m for m in must_not if any(h[0] == m[0] and (m[1] is None or h[1] == m[1]) for h in have)]
    if bad or bad_not:
        fails += 1; print(f"FAIL #{i}: {text[:90]}\n   missing: {bad}  unexpected: {bad_not}\n   got: {sorted(have, key=str)[:8]}")
print(f"{len(CASES)-fails}/{len(CASES)} golden cases pass"); sys.exit(1 if fails else 0)
