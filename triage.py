#!/usr/bin/env python3
"""
Inbox triage demo: sorts emails into URGENT / NOT SURE / NORMAL.
It never replies to, sends, or deletes any email. It only sorts.

Layer 1: plain rules (keywords and simple checks).
Layer 2 (optional): an AI model double-checks each email, if an API key is set.

Safety policy:
  - Weak, mixed, or missing signals  -> NOT SURE (never NORMAL).
  - NORMAL only when the rules (and the AI, if used) agree with good confidence.
  - The AI can raise an email's priority but can never lower a rules URGENT.
"""
import json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))

LABELS = {
    "URGENT":   "Triage/URGENT",
    "NOT SURE": "Triage/Not sure - please look",
    "NORMAL":   "Triage/Normal",
}
NORMAL_MIN_CONFIDENCE = 0.70

# ---- Layer 1: rules -------------------------------------------------------
# (pattern, weight, plain-English name)
URGENT_SIGNALS = [
    (r"\bno heat\b|\bnot heating\b|\bfurnace (stopped|died|quit)\b", 3, "no heat"),
    (r"\bno cooling\b|\bnot cooling\b|\bno a/?c\b", 3, "no cooling"),
    (r"\b(unit|system|rtu|furnace|boiler)\b[^.]{0,30}\b(is )?down\b|\bdown\b[^.]{0,10}\bunit\b", 2, "unit down"),
    (r"\bcommercial\b|\brestaurant\b|\bkitchen\b|\bstore\b|\bwarehouse\b", 2, "commercial account"),
    (r"\b(1\d|[0-2]?\d|3[0-2]) degrees\b", 2, "freezing weather"),
    (r"\b(7\d|8\d|9\d) (years old|year old)\b|\bis (7\d|8\d|9\d)\b|\belderly\b|\blives alone\b", 2, "vulnerable person"),
    (r"\basap\b|\bemergency\b|\bright away\b|\bthis morning\b", 1, "asks for fast help"),
    (r"\bcancel\b", 2, "wants to cancel"),
    (r"\brefund\b|\bchargeback\b|\bcredit card company\b", 2, "money dispute"),
    (r"\blawyer\b|\battorney\b|\bsue\b|\blegal\b", 3, "legal threat"),
    (r"\breview\b|\bbbb\b", 1, "threatens a bad review"),
    (r"\bthird time\b|\bstill not fixed\b|\bi am done\b|\bfed up\b", 2, "angry repeat customer"),
    (r"\bgas (smell|leak)\b|\bsmell(s)? (of |like )?gas\b|\bcarbon monoxide\b|\bco alarm\b", 4, "possible gas / CO"),
    (r"\bflood(ing)?\b|\bwater everywhere\b|\bleaking\b", 2, "water leak"),
]
VAGUE_SIGNALS = [
    (r"\bweird noise\b|\bstrange noise\b|\brattl", 2, "a noise, unclear how bad"),
    (r"\bsmell\b", 2, "a smell, could be nothing or could be a safety issue"),
    (r"\bcall when you can\b|\bplease (have someone )?call\b|\bcall me\b", 1, "asks for a call but doesn't say why"),
    (r"\bneed to talk\b|\bour account\b", 2, "wants to talk about the account, reason not given"),
    (r"\bdoing the thing\b|\bagain\b", 1, "refers to an earlier problem without details"),
    (r"^(fwd|fw):", 1, "forwarded thread"),
    (r"\bnot sure\b|\bshould i be worried\b|\bis this (normal|anything)\b", 2, "sender is unsure themselves"),
]
ROUTINE_SIGNALS = [
    (r"\bunsubscribe\b|\b\d+% off\b|\bsale\b|\bsave \d+%|\bpromo|\bcode [A-Z0-9]+\b", 2, "promotion"),
    (r"\bshipped\b|\btracking\b|\border #", 2, "shipping notice"),
    (r"\bin this issue\b|\bread online\b|\bnewsletter\b", 2, "newsletter"),
    (r"\breschedule\b|\bmove my\b|\bconfirming\b|\bstill coming\b", 2, "scheduling"),
    (r"\binvoice\b|\bstatement\b|\bbalance due\b|\bcharged automatically\b", 2, "billing paperwork"),
    (r"\bno rush\b|\bnot urgent\b|\bwhenever\b", 2, "sender says it isn't urgent"),
    (r"\bquote\b|\bwhat does it cost\b|\bdo you (guys )?do\b", 2, "sales question"),
    (r"\bthanks!|\bgreat job\b|\bjust wanted to say\b", 2, "thank-you note"),
    (r"\brsvp\b|\bmixer\b|\benroll\b|\bce hours\b|\bpre-approved\b|\bapply in\b", 2, "event / marketing"),
    (r"\bweekly .*summary\b|\bview the full report\b", 2, "automated report"),
    (r"\brunning (about )?\d+ min\b|\brunning late\b|\balready texted\b", 2, "internal crew update"),
    (r"\bhow do i\b|\bwhat size\b", 2, "simple how-to question"),
]

def _hits(text, signals):
    found = []
    for pat, w, name in signals:
        if re.search(pat, text, re.I | re.M):
            found.append((w, name))
    return found

def rules_triage(email):
    text = f"{email['subject']}\n{email['body']}"
    subj = email["subject"]
    u = _hits(text, URGENT_SIGNALS)
    v = _hits(text, VAGUE_SIGNALS) + [h for h in _hits(subj, VAGUE_SIGNALS[5:6]) if h not in _hits(text, VAGUE_SIGNALS)]
    r = _hits(text, ROUTINE_SIGNALS)
    us, vs, rs = sum(w for w, _ in u), sum(w for w, _ in v), sum(w for w, _ in r)
    names = lambda hs: ", ".join(n for _, n in hs)

    if us >= 4:
        conf = min(0.98, 0.60 + 0.05 * us)
        return dict(category="URGENT", confidence=round(conf, 2),
                    reason=f"Strong urgent signs: {names(u)}.", signals=dict(urgent=us, vague=vs, routine=rs))
    if us > 0:
        return dict(category="NOT SURE", confidence=0.45,
                    reason=f"Some urgent signs ({names(u)}) but not enough to be sure. A person should look.",
                    signals=dict(urgent=us, vague=vs, routine=rs))
    if vs > 0:
        conf = max(0.25, 0.55 - 0.05 * vs)
        return dict(category="NOT SURE", confidence=round(conf, 2),
                    reason=f"Can't tell how serious this is: {names(v)}.", signals=dict(urgent=us, vague=vs, routine=rs))
    if rs > 0:
        conf = min(0.95, 0.60 + 0.08 * rs)
        cat = "NORMAL" if conf >= NORMAL_MIN_CONFIDENCE else "NOT SURE"
        reason = (f"Routine: {names(r)}. No urgent signs." if cat == "NORMAL"
                  else f"Looks routine ({names(r)}) but the signs are weak. A person should look.")
        return dict(category=cat, confidence=round(conf, 2), reason=reason, signals=dict(urgent=us, vague=vs, routine=rs))
    return dict(category="NOT SURE", confidence=0.30,
                reason="No clear signs either way, so I'm not guessing. A person should look.",
                signals=dict(urgent=0, vague=0, routine=0))

# ---- Layer 2: optional AI check -------------------------------------------
PROMPT = """You sort emails for an 11-person HVAC company. You NEVER write replies.
Classify this one email as exactly one of:
- URGENT: needs a human within the hour (commercial unit down, no heat in cold weather,
  vulnerable person at risk, safety issue like gas/CO, angry customer about to cancel or threatening legal action).
- NOT SURE: you cannot tell how serious it is from the text (vague, missing details, could be nothing or could be bad).
- NORMAL: clearly routine (promos, newsletters, scheduling, billing paperwork, thank-yous, simple questions).
If you have ANY doubt between URGENT and NORMAL, answer NOT SURE. Do not guess.
Answer with JSON only: {"category": "...", "confidence": 0.0-1.0, "reason": "one short plain-English sentence"}

From: %s
Subject: %s

%s"""

def find_llm():
    """Return (name, url, model, key) for the first configured provider, without printing the key."""
    providers = [
        ("OpenAI",   "OPENAI_API_KEY",   "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
        ("DeepSeek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/chat/completions",  "deepseek-chat"),
        ("xAI",      "XAI_API_KEY",      "https://api.x.ai/v1/chat/completions",       "grok-3-mini"),
    ]
    for name, env, url, model in providers:
        if os.environ.get(env):
            return name, url, model, os.environ[env]
    return None

def llm_triage(llm, email):
    name, url, model, key = llm
    body = json.dumps({
        "model": model, "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": PROMPT % (email["from"], email["subject"], email["body"])}],
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        out = json.load(resp)
    data = json.loads(out["choices"][0]["message"]["content"])
    cat = str(data.get("category", "")).upper().strip()
    if cat not in LABELS:
        cat = "NOT SURE"
    return dict(category=cat, confidence=float(data.get("confidence", 0.5)), reason=str(data.get("reason", "")).strip())

def combine(rules, ai):
    """Safety-first merge. NORMAL only if both agree with good confidence."""
    rc, ac = rules["category"], ai["category"]
    if rc == "URGENT":
        return "URGENT", max(rules["confidence"], ai["confidence"] if ac == "URGENT" else 0), \
               rules["reason"] + ("" if ac == "URGENT" else f" (AI check said {ac}; rules win on urgent.)")
    if ac == "URGENT" and ai["confidence"] >= 0.8:
        return "URGENT", ai["confidence"], f"AI check flagged it urgent: {ai['reason']}"
    if rc == "NORMAL" and ac == "NORMAL" and ai["confidence"] >= NORMAL_MIN_CONFIDENCE:
        return "NORMAL", round(min(rules["confidence"], ai["confidence"]), 2), rules["reason"]
    if rc == ac:  # both NOT SURE
        return "NOT SURE", round(min(rules["confidence"], ai["confidence"]), 2), rules["reason"]
    # disagreement or low confidence -> NOT SURE
    return "NOT SURE", 0.40, f"Rules said {rc}, AI check said {ac}. They disagree, so a person should look. {ai['reason']}"

# ---- Alerts (built, never sent) -------------------------------------------
def slack_payload(email, res):
    icon = ":rotating_light:" if res["category"] == "URGENT" else ":large_yellow_circle:"
    head = "URGENT email" if res["category"] == "URGENT" else "Not sure - please look"
    sender = email["from"].split("<")[0].strip()
    return {
        "text": f"{head}: {email['subject']} (from {sender})",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn",
             "text": f"{icon} *{head}*\n*{email['subject']}*\nFrom: {sender} · {email['received']}"}},
            {"type": "context", "elements": [{"type": "mrkdwn",
             "text": f"Why: {res['reason']}  ·  Confidence: {int(res['confidence']*100)}%"}]},
        ],
    }

def main():
    no_llm = "--no-llm" in sys.argv
    emails = json.load(open(os.path.join(HERE, "sample_emails.json")))
    llm = None if no_llm else find_llm()
    mode = f"rules + AI check ({llm[0]}, {llm[2]})" if llm else "rules only (no AI key found)"
    if no_llm:
        mode = "rules only (--no-llm)"
    print(f"Mode: {mode}", file=sys.stderr)
    results, ai_failures = [], 0
    for e in emails:
        rules = rules_triage(e)
        ai = None
        if llm:
            try:
                ai = llm_triage(llm, e)
            except urllib.error.HTTPError as ex:
                ai_failures += 1
                if ex.code in (401, 403):
                    print(f"  AI key was rejected ({ex.code}); switching to rules only for every email", file=sys.stderr)
                    mode = f"rules only (an AI key was found for {llm[0]} but it was rejected)"
                    llm = None
                else:
                    print(f"  AI check failed on #{e['id']} (HTTP {ex.code}); using rules only for it", file=sys.stderr)
            except Exception as ex:
                ai_failures += 1
                print(f"  AI check failed on #{e['id']} ({type(ex).__name__}); using rules only for it", file=sys.stderr)
        if ai:
            cat, conf, reason = combine(rules, ai)
        else:
            cat, conf, reason = rules["category"], rules["confidence"], rules["reason"]
        res = dict(category=cat, confidence=round(float(conf), 2), reason=reason)
        item = dict(email=e, **res, rules=rules, ai=ai,
                    gmail_label=LABELS[cat], reply_sent=False,
                    slack=slack_payload(e, res) if cat != "NORMAL" else None)
        results.append(item)
        print(f"  #{e['id']:>2} {cat:<8} {res['confidence']:.2f}  {e['subject'][:50]}", file=sys.stderr)
    counts = {k: sum(1 for r in results if r["category"] == k) for k in LABELS}
    out = dict(mode=mode, ai_failures=ai_failures, total=len(results), counts=counts,
               replies_sent=0, real_api_calls_to_gmail_or_slack=0, results=results)
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=2)
    print(f"{len(results)} emails: {counts['URGENT']} urgent, {counts['NOT SURE']} not sure, "
          f"{counts['NORMAL']} normal; 0 replies sent.", file=sys.stderr)

if __name__ == "__main__":
    main()
