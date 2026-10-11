"""Checks the safety rules, including the AI merge, using fake AI answers (no network)."""
import json
from triage import rules_triage, combine
emails = {e["id"]: e for e in json.load(open("sample_emails.json"))}
exp = {1: "URGENT", 2: "URGENT", 3: "URGENT", 4: "NOT SURE", 5: "NOT SURE", 6: "NOT SURE", 7: "NOT SURE"}
for i, cat in exp.items():
    assert rules_triage(emails[i])["category"] == cat, (i, rules_triage(emails[i]))
ai = lambda c, conf=0.9: dict(category=c, confidence=conf, reason="fake")
R = lambda c, conf=0.8: dict(category=c, confidence=conf, reason="r")
assert combine(R("URGENT"), ai("NORMAL"))[0] == "URGENT"        # AI can never downgrade urgent
assert combine(R("NORMAL"), ai("URGENT"))[0] == "URGENT"        # AI can raise priority
assert combine(R("NORMAL"), ai("URGENT", .6))[0] == "NOT SURE"  # ...but a shaky raise becomes NOT SURE
assert combine(R("NORMAL"), ai("NOT SURE"))[0] == "NOT SURE"    # disagreement -> NOT SURE
assert combine(R("NOT SURE"), ai("NORMAL"))[0] == "NOT SURE"    # never NORMAL unless both agree
assert combine(R("NORMAL"), ai("NORMAL", .5))[0] == "NOT SURE"  # low AI confidence -> NOT SURE
assert combine(R("NORMAL"), ai("NORMAL"))[0] == "NORMAL"
r = json.load(open("results.json"))
assert r["replies_sent"] == 0 and all(not x["reply_sent"] for x in r["results"])
print("all policy checks passed")
