# AI Inbox Triage Demo

Sorts a business inbox into URGENT / NOT SURE / routine using safety rules first and an AI classifier second; the AI can never downgrade a rule-flagged urgent email. Includes sample data, an HTML demo, and policy tests.

**Tech stack:** Python, LLM classification with rule-based guardrails

> **How this was built:** built fast with AI coding tools (vibe coding), then reviewed, tested, and documented by me. Demo data only: all names, numbers, and businesses are fictional.

Built by DeAli Dillard ([Aporia Nous](https://github.com/Aporia-Nous)). Contact: demo@aporianous.com. MIT licensed.

---

# Inbox Triage (HVAC demo)

A small, working demo of an email sorter for a busy trade business. It reads every email and puts it in one of three piles:

- **Urgent**: needs a person right now. Examples: a commercial unit down, no heat when it's freezing, a customer about to cancel. Your phone buzzes.
- **Not sure**: it can't tell how serious the email is. Your phone still buzzes, marked "please look."
- **Normal**: clearly routine stuff like promos, newsletters, scheduling, and old invoice questions. It gets a label, and no ping.

Every email gets a **one-line reason** in plain English and a **confidence score**, so you can see why it decided what it did.

**It only sorts. It never replies to, sends, forwards, or deletes any email.**

## The "tell me when you don't know" rule

This is the most important part. If the signs in an email are weak, mixed, or missing, it goes to **Not sure**, never quietly to Normal. A "Normal" result needs clear routine signs and good confidence. If an AI check is turned on, the AI and the rules both have to agree before anything is called Normal. The AI can raise an email to Urgent, but it can never lower one the rules marked Urgent.

You'd rather be bothered 20 times for nothing than miss one real emergency, and that's how this is built.

## What's in this folder

| File | What it is |
|---|---|
| `sample_emails.json` | 25 made-up emails (fake names, `@example.com` addresses, 555 numbers) |
| `triage.py` | The sorter: plain rules first, then an optional AI double-check |
| `results.json` | The sorter's output: pile, confidence, reason, the Gmail label it would apply, and the Slack message it would send |
| `build_demo.py` | Turns the results into `demo.html` |
| `demo.html` | The demo page. Open it in any browser. It's one file with no internet needed |
| `test_policy.py` | Checks the safety rules (including the AI merge, using fake AI answers) |

## How to run it

You need Python 3, and nothing else to install.

```
python3 triage.py --no-llm     # sort the sample emails with the rules only
python3 build_demo.py          # build demo.html
python3 test_policy.py         # check the safety rules
```

Then open `demo.html` in a browser.

To turn on the AI double-check, set an API key (for example `OPENAI_API_KEY`) and run `python3 triage.py` without `--no-llm`. If no key is set, or the key doesn't work, it says so and uses the rules only.

**What this demo run used:** rules only. The AI double-check was not used for the pictures and video.

**Honest note:** the rules were tuned on these 25 sample emails. On a real inbox, the first week or two is spent tuning them on your actual mail, so it learns what your office manager would flag.

## How it would connect to your real accounts

The demo makes **no** real Gmail or Slack calls. In a real setup:

**Google Workspace (Gmail)**
- A small script watches the inbox. This is either Google Apps Script, which lives inside your Google account, or a small program using the Gmail API with read-and-label permission only.
- Every minute or two, it looks at new emails, sorts them, and applies a label such as `Triage/URGENT` or `Triage/Not sure - please look`.
- It's given permission to **read and label only**. It has no permission to send email.

**Slack**
- You create an "incoming webhook" in Slack. That's a private web address that posts messages into one channel, for example `#email-alerts`.
- Urgent and Not sure emails post a short message there with the subject, who it's from, and the reason. With Slack notifications on for that channel, your phone buzzes.

**Setup for a non-technical owner:** step-by-step written instructions with screenshots. It takes about 30 minutes on a call together.

---

*Demo with sample emails. Sorts only, never replies.*
