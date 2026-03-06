#!/usr/bin/env python3
"""
Coco Caribbean Tourism Batch Caller — March 6, 2026
Agent: Coco (ec36dfb3-9f0b-4f8e-9abb-53314b174831)
Phone Number ID: 23eacc2d-e19d-4410-98dd-aef4ab564b63
Offer: Website $599 + SEO $250/mo
"""
import os, json, re, sys, time, requests
from datetime import datetime, timezone

VAPI_API_KEY     = "0aaae7fe-be63-472a-a46d-5d9224e0fa89"
ASSISTANT_ID     = "ec36dfb3-9f0b-4f8e-9abb-53314b174831"
PHONE_NUMBER_ID  = "23eacc2d-e19d-4410-98dd-aef4ab564b63"
LEADS_FILE       = "/root/.openclaw/workspace/real-estate/caribbean-leads-2026-03-05.json"
RESULTS_FILE     = "/root/.openclaw/workspace/assets/coco-call-results-march6.json"
OFFER            = "Website $599 + SEO $250/mo"
MAX_CALLS        = 50
CALL_DELAY_SEC   = 2      # polite gap between API calls
POLL_WAIT_SEC    = 600    # wait 10 min before polling final status
POLL_MAX_RETRIES = 3

HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json"
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def clean_phone(raw):
    """Normalise to E.164: +<digits>"""
    if not raw:
        return None
    stripped = re.sub(r'[\s\-\(\)\.\/]', '', raw)
    if stripped.startswith('+'):
        digits = re.sub(r'[^\d]', '', stripped[1:])
        return '+' + digits if len(digits) >= 7 else None
    digits = re.sub(r'[^\d]', '', stripped)
    return '+' + digits if len(digits) >= 7 else None

def is_saint_lucia(raw):
    if not raw:
        return False
    e164 = clean_phone(raw)
    return bool(e164 and e164.startswith('+1758'))

def fire_call(lead):
    phone = clean_phone(lead.get('phone', ''))
    payload = {
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {
            "number": phone,
            "name": lead.get('name', '')
        },
        "assistantOverrides": {
            "variableValues": {
                "businessName": lead.get('name', ''),
                "island":       lead.get('island', ''),
                "country":      lead.get('country', ''),
                "businessType": lead.get('business_type', ''),
                "offer":        OFFER
            }
        }
    }
    try:
        r = requests.post("https://api.vapi.ai/call", headers=HEADERS, json=payload, timeout=30)
        if r.ok:
            data = r.json()
            return {
                "status":  "initiated",
                "call_id": data.get("id"),
                "vapi_status": data.get("status", "queued")
            }
        else:
            return {"status": "api_error", "code": r.status_code, "error": r.text[:300]}
    except Exception as e:
        return {"status": "exception", "error": str(e)}

def poll_call(call_id):
    for attempt in range(POLL_MAX_RETRIES):
        try:
            r = requests.get(f"https://api.vapi.ai/call/{call_id}", headers=HEADERS, timeout=15)
            if r.ok:
                return r.json()
        except:
            pass
        time.sleep(5)
    return {"status": "poll_failed", "call_id": call_id}

def save(data):
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ── Load & filter leads ───────────────────────────────────────────────────────

with open(LEADS_FILE) as f:
    all_leads = json.load(f)

valid_leads, skipped = [], []
for lead in all_leads:
    phone = lead.get('phone', '')
    if not phone:
        skipped.append({"name": lead.get('name'), "reason": "no_phone"})
        continue
    if is_saint_lucia(phone):
        skipped.append({"name": lead.get('name'), "reason": "saint_lucia_skip", "phone": phone})
        continue
    valid_leads.append(lead)
    if len(valid_leads) >= MAX_CALLS:
        break

print(f"[INFO] {len(valid_leads)} leads selected | {len(skipped)} skipped")

# ── Build results skeleton ────────────────────────────────────────────────────

results = {
    "campaign":        "Caribbean Tourism - Coco Outbound Calls",
    "date":            "2026-03-06",
    "fired_at":        datetime.now(timezone.utc).isoformat(),
    "offer":           OFFER,
    "agent_id":        ASSISTANT_ID,
    "phone_number_id": PHONE_NUMBER_ID,
    "total_leads":     len(valid_leads),
    "skipped":         skipped,
    "calls":           []
}
save(results)

# ── Fire all calls ────────────────────────────────────────────────────────────

print(f"\n[PHASE 1] Firing {len(valid_leads)} calls ...")
call_records = []

for i, lead in enumerate(valid_leads, start=1):
    phone_e164 = clean_phone(lead.get('phone', ''))
    print(f"  [{i:02d}/{len(valid_leads)}] {lead['name'][:50]:<50}  {phone_e164}")

    fire_result = fire_call(lead)

    record = {
        "index":          i,
        "business_name":  lead.get('name'),
        "phone":          phone_e164,
        "island":         lead.get('island'),
        "business_type":  lead.get('business_type'),
        "digital_gaps":   lead.get('digital_gap_signals', []),
        "fired_at":       datetime.now(timezone.utc).isoformat(),
        "fire_result":    fire_result,
        "final_status":   None,
        "ended_reason":   None,
        "duration_s":     None,
        "cost_usd":       None,
        "summary":        None
    }
    call_records.append(record)
    results["calls"].append(record)
    save(results)

    if fire_result.get("status") != "initiated":
        print(f"    ⚠  FAILED: {fire_result}")

    time.sleep(CALL_DELAY_SEC)

# ── Wait, then poll results ───────────────────────────────────────────────────

print(f"\n[PHASE 2] Waiting {POLL_WAIT_SEC}s before polling call results ...")
time.sleep(POLL_WAIT_SEC)

print(f"[PHASE 2] Polling {len(call_records)} calls ...")
for record in call_records:
    call_id = record.get("fire_result", {}).get("call_id")
    if not call_id:
        continue
    data = poll_call(call_id)
    record["final_status"]  = data.get("status")
    record["ended_reason"]  = data.get("endedReason") or data.get("ended_reason")
    record["cost_usd"]      = data.get("cost")
    record["summary"]       = data.get("summary") or data.get("analysis", {}).get("summary")

    # Duration
    started_at = data.get("startedAt")
    ended_at   = data.get("endedAt")
    if started_at and ended_at:
        try:
            from datetime import datetime as dt
            s = dt.fromisoformat(started_at.replace('Z', '+00:00'))
            e = dt.fromisoformat(ended_at.replace('Z', '+00:00'))
            record["duration_s"] = round((e - s).total_seconds(), 1)
        except:
            pass

    save(results)

# ── Summary ───────────────────────────────────────────────────────────────────

initiated   = sum(1 for r in call_records if r["fire_result"].get("status") == "initiated")
fire_errors = sum(1 for r in call_records if r["fire_result"].get("status") != "initiated")
ended       = sum(1 for r in call_records if r.get("final_status") == "ended")
total_cost  = sum(r.get("cost_usd") or 0 for r in call_records)

results["summary"] = {
    "total_leads_selected": len(valid_leads),
    "total_skipped":        len(skipped),
    "calls_initiated":      initiated,
    "call_fire_errors":     fire_errors,
    "calls_ended":          ended,
    "estimated_cost_usd":   round(total_cost, 4),
    "results_file":         RESULTS_FILE,
    "completed_at":         datetime.now(timezone.utc).isoformat()
}
save(results)

print(f"""
╔══════════════════════════════════════════════╗
║        COCO CAMPAIGN COMPLETE — MARCH 6      ║
╚══════════════════════════════════════════════╝
  Leads selected:  {len(valid_leads)}
  Leads skipped:   {len(skipped)}
  Calls initiated: {initiated}
  Fire errors:     {fire_errors}
  Calls ended:     {ended}
  Est. cost:       ${total_cost:.4f}
  Results file:    {RESULTS_FILE}
""")
