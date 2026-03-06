#!/usr/bin/env python3
"""
Coco Caribbean Calls - Batch Outbound Dialer
March 6, 2026
Offer: Website $599 + SEO $250/mo
"""
import os
import sys
import json
import time
import re
import requests
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
VAPI_API_KEY    = "0aaae7fe-be63-472a-a46d-5d9224e0fa89"
ASSISTANT_ID    = "ec36dfb3-9f0b-4f8e-9abb-53314b174831"   # Coco
PHONE_NUMBER_ID = "23eacc2d-e19d-4410-98dd-aef4ab564b63"   # Cron-specified
LEADS_FILE      = "/root/.openclaw/workspace/real-estate/caribbean-leads-2026-03-05.json"
RESULTS_FILE    = "/root/.openclaw/workspace/assets/coco-call-results-march6.json"
MAX_CALLS       = 50
SKIP_PREFIX     = "+1758"   # Saint Lucia
CALL_INTERVAL   = 3         # seconds between calls (rate-limit buffer)

SYSTEM_PROMPT = """You are Coco, a friendly and persuasive Caribbean tourism digital marketing specialist. 
You are calling small Caribbean tourism businesses (tour operators, guesthouses, activity providers, dive shops, etc.) to offer them affordable digital marketing solutions.

Your offer:
- Professional Website: $599 one-time (custom, mobile-optimised, SEO-ready)
- Monthly SEO Package: $250/month (Google rankings, more bookings, review management)

Your goals:
1. Greet the owner/manager warmly
2. Briefly explain you found their business online and noticed they could use a stronger digital presence
3. Highlight their specific pain points (mention 1-2 from their profile if relevant)
4. Present the offer clearly
5. Handle objections confidently
6. Try to book a follow-up call or get their email for a proposal

Keep it conversational, warm, and under 3-4 minutes. You represent a legitimate agency helping Caribbean tourism businesses grow.
If they're not interested, thank them and end politely."""

def normalize_phone(raw):
    """Strip spaces/dashes to clean E.164."""
    return re.sub(r"[\s\-\(\)]", "", raw)

def load_leads():
    with open(LEADS_FILE) as f:
        return json.load(f)

def filter_leads(leads):
    """Return first MAX_CALLS leads that have a phone and aren't +1758."""
    valid = []
    skipped_no_phone = 0
    skipped_saint_lucia = 0
    for lead in leads:
        raw_phone = lead.get("phone", "").strip()
        if not raw_phone:
            skipped_no_phone += 1
            continue
        phone = normalize_phone(raw_phone)
        if phone.startswith(SKIP_PREFIX):
            skipped_saint_lucia += 1
            continue
        lead["_phone_e164"] = phone
        valid.append(lead)
        if len(valid) >= MAX_CALLS:
            break
    return valid, skipped_no_phone, skipped_saint_lucia

def place_call(lead):
    """Fire a Vapi outbound call. Returns dict with call_id and status."""
    phone = lead["_phone_e164"]
    biz_name = lead.get("name", "")
    island = lead.get("island", "")
    biz_type = lead.get("business_type", "")
    signals = lead.get("digital_gap_signals", [])

    # Personalised first message
    first_msg = (
        f"Hi there! My name is Coco and I'm reaching out to {biz_name} on behalf of a Caribbean digital marketing agency. "
        f"Is the owner or manager available for a quick 2-minute chat? "
        f"I noticed your business could really benefit from a stronger online presence!"
    )

    payload = {
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {"number": phone},
        "assistantOverrides": {
            "firstMessage": first_msg,
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
                "tools": [{"type": "endCall"}]
            }
        }
    }

    try:
        resp = requests.post(
            "https://api.vapi.ai/call",
            headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
            json=payload,
            timeout=30
        )
        if resp.ok:
            data = resp.json()
            return {
                "call_id": data.get("id"),
                "status": "queued",
                "api_status": resp.status_code,
                "created_at": data.get("createdAt"),
            }
        else:
            return {
                "call_id": None,
                "status": "api_error",
                "api_status": resp.status_code,
                "error": resp.text[:300],
            }
    except Exception as e:
        return {
            "call_id": None,
            "status": "exception",
            "error": str(e),
        }

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading leads...")
    leads = load_leads()
    valid_leads, skip_no_phone, skip_sl = filter_leads(leads)

    print(f"  Total leads loaded  : {len(leads)}")
    print(f"  Skipped (no phone)  : {skip_no_phone}")
    print(f"  Skipped (Saint Lucia +1758): {skip_sl}")
    print(f"  Leads to call       : {len(valid_leads)}")
    print()

    results = []
    success = 0
    errors = 0

    for i, lead in enumerate(valid_leads, 1):
        biz = lead.get("name", "Unknown")
        phone = lead["_phone_e164"]
        print(f"[{i:02d}/{len(valid_leads)}] {biz} ({phone})", end=" ... ")

        result = place_call(lead)

        entry = {
            "index": i,
            "business_name": biz,
            "island": lead.get("island"),
            "country": lead.get("country"),
            "phone_raw": lead.get("phone"),
            "phone_e164": phone,
            "business_type": lead.get("business_type"),
            "digital_gap_signals": lead.get("digital_gap_signals", []),
            "call_result": result,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        results.append(entry)

        if result["status"] == "queued":
            success += 1
            print(f"✓ queued (id: {result['call_id'][:8]}...)")
        else:
            errors += 1
            print(f"✗ {result['status']}: {result.get('error','?')[:80]}")

        if i < len(valid_leads):
            time.sleep(CALL_INTERVAL)

    # ─── Save results ─────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    summary = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "assistant_id": ASSISTANT_ID,
        "phone_number_id": PHONE_NUMBER_ID,
        "offer": "Website $599 + SEO $250/mo",
        "total_leads_in_file": len(leads),
        "skipped_no_phone": skip_no_phone,
        "skipped_saint_lucia": skip_sl,
        "calls_attempted": len(valid_leads),
        "calls_queued": success,
        "calls_errored": errors,
        "results": results
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print()
    print("=" * 60)
    print(f"  DONE  |  Queued: {success}  |  Errors: {errors}")
    print(f"  Results saved to: {RESULTS_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
