"""
LeadOps Platform Integration Script
Orchestrates all services: scraper -> grok -> outreach -> core_agent

Usage:
    python leadops_integration.py --niche "plumber" --location "Melbourne" --plan b
"""

import os
import asyncio
import argparse
import json
import httpx
from typing import Optional

# ── Service URLs (set via env or .env file) ──────────────────────────────────
SCRAPER_URL   = os.getenv("SCRAPER_URL",   "https://scraper.notion.locker")
OUTREACH_URL  = os.getenv("OUTREACH_URL",  "https://outreach.notion.locker")
AGENT_URL     = os.getenv("AGENT_URL",     "https://agent.notion.locker")
GROK_BASE_URL = os.getenv("XAI_BASE_URL",  "https://api.x.ai/v1")
XAI_API_KEY   = os.getenv("XAI_API_KEY",   "")
GROK_MODEL    = os.getenv("XAI_MODEL",     "grok-2-latest")


# ── 1. Lead Scraper ──────────────────────────────────────────────────────────
async def scrape_leads(niche: str, location: str, max_results: int = 50) -> list:
    """Scrape leads from manus-web-scraper service."""
    print(f"[LEAD ENGINE] Scraping '{niche}' in '{location}'...")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{SCRAPER_URL}/scrape",
            json={"query": niche, "location": location, "max_results": max_results}
        )
        resp.raise_for_status()
        data = resp.json()
        leads = data.get("leads", [])
        print(f"[LEAD ENGINE] Got {len(leads)} leads.")
        return leads


def dedupe_leads(leads: list) -> list:
    """Remove duplicates by website/domain."""
    seen = set()
    unique = []
    for lead in leads:
        key = lead.get("website") or lead.get("email") or lead.get("name")
        if key and key not in seen:
            seen.add(key)
            unique.append(lead)
    print(f"[LEAD ENGINE] After dedup: {len(unique)} unique leads.")
    return unique


def score_leads(leads: list) -> list:
    """Score leads A/B/C based on data completeness."""
    for lead in leads:
        score = 0
        if lead.get("email"):   score += 3
        if lead.get("website"): score += 2
        if lead.get("phone"):   score += 1
        lead["tier"] = "A" if score >= 5 else ("B" if score >= 3 else "C")
    a = sum(1 for l in leads if l["tier"] == "A")
    b = sum(1 for l in leads if l["tier"] == "B")
    c = sum(1 for l in leads if l["tier"] == "C")
    print(f"[LEAD ENGINE] Scored: A={a}, B={b}, C={c}")
    return leads


# ── 2. Grok Copy Generation ───────────────────────────────────────────────────
async def generate_copy(niche: str, location: str, segment: str = "A-tier") -> dict:
    """Generate cold email copy via xAI Grok."""
    print(f"[COPY & GROK] Generating copy for {niche} in {location} ({segment})...")
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": "You are a B2B cold email copywriter. Write concise, value-focused emails under 120 words. Return JSON with keys: subject1, body1, subject2, body2."},
            {"role": "user",   "content": f"Write 2 cold email variants for {niche} businesses in {location}. Focus on their biggest pain points. Segment: {segment}."}
        ],
        "temperature": 0.8,
        "max_tokens": 600,
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{GROK_BASE_URL}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        copy = json.loads(content)
        print(f"[COPY & GROK] Generated: '{copy.get('subject1', '')}' + '{copy.get('subject2', '')}")
        return copy


# ── 3. Campaign Launch ────────────────────────────────────────────────────────
async def create_campaign(name: str, leads: list, copy: dict, dry_run: bool = True) -> dict:
    """Create outreach campaign via manus-sales-automation."""
    templates = [
        {"id": "v1", "subject": copy.get("subject1", ""), "body": copy.get("body1", ""), "delay_days": 0},
        {"id": "v2", "subject": copy.get("subject2", ""), "body": copy.get("body2", ""), "delay_days": 4},
    ]
    payload = {
        "name": name,
        "segment": "A-tier",
        "templates": templates,
        "schedule": {"daily_send_limit": 15},
        "throttle_limit": 15,
        "dry_run": dry_run
    }
    if dry_run:
        print(f"[AUTOPILOT] DRY RUN - Campaign '{name}' config ready ({len(leads)} leads).")
        print(f"[AUTOPILOT] Subjects: '{templates[0]['subject']}' | '{templates[1]['subject']}'")
        return {"status": "dry_run", "campaign": payload}

    print(f"[AUTOPILOT] Launching campaign '{name}'...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{OUTREACH_URL}/campaigns", json=payload)
        resp.raise_for_status()
        campaign = resp.json()
        print(f"[AUTOPILOT] Campaign created: {campaign.get('campaign_id')}")

        # Send batch
        batch_resp = await client.post(
            f"{OUTREACH_URL}/send_batch",
            json={"campaign_id": campaign["campaign_id"], "lead_list": leads[:20]}
        )
        print(f"[AUTOPILOT] Batch sent: {batch_resp.json()}")
        return campaign


# ── 4. Core Agent Optimisation ────────────────────────────────────────────────
async def optimise_with_agent(goal: str, context: dict) -> dict:
    """Run optimisation task via manus-agent-core ReAct loop."""
    print(f"[AUTOPILOT] Sending to core_agent: '{goal}'")
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{AGENT_URL}/run_task",
            json={"goal": goal, "context": context, "max_steps": 25}
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"[AUTOPILOT] Agent plan: {result.get('final_plan', '')[:200]}")
        return result


# ── 5. Main Orchestration Flow ────────────────────────────────────────────────
async def run_leadops(niche: str, location: str, plan: str, dry_run: bool = True):
    """Full LeadOps pipeline: scrape -> copy -> campaign -> (optimise)."""
    print(f"\n{'='*60}")
    print(f"LeadOps Platform | Plan {plan.upper()} | {niche} in {location}")
    print(f"{'='*60}\n")

    # Step 1: Scrape
    raw_leads  = await scrape_leads(niche, location)
    leads      = dedupe_leads(raw_leads)
    leads      = score_leads(leads)
    a_tier     = [l for l in leads if l["tier"] == "A"]

    # Step 2: Copy (Plan A+)
    copy = await generate_copy(niche, location)

    # Step 3: Campaign (Plan A+)
    campaign_name = f"{niche.title()}_{location.replace(' ','_')}_Q1"
    campaign = await create_campaign(campaign_name, a_tier, copy, dry_run=dry_run)

    # Step 4: Agent optimisation (Plan C only)
    if plan.lower() == "c" and not dry_run:
        await optimise_with_agent(
            goal=f"Design full LeadOps strategy for {niche} in {location}",
            context={"leads_count": len(leads), "a_tier": len(a_tier), "campaign": campaign_name}
        )

    print(f"\n[DONE] LeadOps run complete.")
    print(f"  Leads scraped : {len(leads)}")
    print(f"  A-tier leads  : {len(a_tier)}")
    print(f"  Campaign      : {campaign_name}")
    print(f"  Status        : {'DRY RUN - review and set --no-dry-run to launch' if dry_run else 'LIVE'}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LeadOps Platform CLI")
    parser.add_argument("--niche",     required=True, help="Business niche (e.g. plumber)")
    parser.add_argument("--location",  required=True, help="City or region (e.g. Melbourne)")
    parser.add_argument("--plan",      default="b",   help="SaaS plan: a, b, or c (default: b)")
    parser.add_argument("--no-dry-run",action="store_true", help="Actually send emails (default: dry run)")
    parser.add_argument("--max-leads", type=int, default=50, help="Max leads to scrape")
    args = parser.parse_args()

    asyncio.run(run_leadops(
        niche=args.niche,
        location=args.location,
        plan=args.plan,
        dry_run=not args.no_dry_run
    ))
