#!/usr/bin/env python3
"""Create 2 demo tickets per Cabrillo capability and feature for analytics demos."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

import requests

BASE = "https://api.devrev.ai"
TOKEN = Path("/tmp/cabrillo_devrev_pat").read_text(encoding="utf-8").strip()
OWNER = "DEVU-1"

# (part_id, part_name, ticket1_title, ticket1_body, ticket2_title, ticket2_body)
TICKETS: List[Tuple[str, str, str, str, str, str]] = [
    # --- Membership ---
    (
        "CAPL-3",
        "Membership",
        "General membership question — not sure where to start",
        "Hi, I'm interested in joining Cabrillo but I'm not sure if I qualify or what the first step is. Can someone walk me through membership in general?",
        "Can family members share membership benefits?",
        "My spouse wants to bank with Cabrillo. Do they need their own membership, or can they be added under mine? Looking for general membership guidance.",
    ),
    (
        "FEAT-5",
        "Become a Member",
        "Do I qualify to become a member? I work in San Diego County",
        "I live in Orange County but work full-time in San Diego County. Can I join with the $5 Regular Share Savings? Also, does Sharp HealthCare employment count?",
        "Eligibility for relative of an existing member",
        "My sister is a Cabrillo member. Can I join based on that relationship, and what documents do you need to verify it?",
    ),
    (
        "FEAT-6",
        "Open an Account",
        "How do new members open their first account online?",
        "I just confirmed I'm eligible. What's the online application path to open my first checking and savings, and how long until I can use Digital Banking?",
        "Existing member — open an additional savings in Digital Banking",
        "I've been a member for 3 years. Where in Digital Banking do I open another savings account without visiting a branch?",
    ),
    # --- Checking ---
    (
        "CAPL-5",
        "Checking",
        "Which checking product is right for me?",
        "I'm comparing checking options and don't know the difference between your checking products. Can you help me choose at a high level?",
        "Checking account fees overview",
        "Before I switch my payroll direct deposit, can someone summarize monthly fees and minimums across your checking lineup?",
    ),
    (
        "FEAT-7",
        "Advantage Checking",
        "Confirm Advantage Checking has no monthly fee",
        "Is Advantage Checking still free with no monthly fee and no minimum balance? I need VISA debit, Zelle, and Bill Pay.",
        "Order checks for Advantage Checking",
        "How do I order more checks for my Advantage Checking account, and is there a fee?",
    ),
    (
        "FEAT-8",
        "Big Easy Checking",
        "Big Easy Checking APY and requirements",
        "I saw Big Easy Checking on the deposit rates page at 0.01% APY. What are the requirements to open and keep this account?",
        "Switch from Big Easy to Advantage Checking",
        "Can I convert my Big Easy Checking to Advantage Checking, or do I need to close and reopen?",
    ),
    (
        "FEAT-9",
        "Basic Checking",
        "Basic Checking after NSF history — can I open one?",
        "I had NSF issues at another bank. Is Basic Checking available for me, and what's the $25 minimum to open?",
        "Does Basic Checking earn dividends?",
        "Confirming Basic Checking is non-dividend. Are there any paths to move back to Advantage later?",
    ),
    (
        "FEAT-10",
        "VISA Debit Card",
        "Replace lost VISA debit card",
        "I lost my Cabrillo VISA debit card. How do I freeze it and order a replacement? Also confirm Zero Liability coverage.",
        "Add debit card to Apple Wallet",
        "My contactless debit works in-store but I can't add it to Apple Wallet. What should I try?",
    ),
    # --- Savings ---
    (
        "CAPL-6",
        "Savings",
        "Overview of savings products",
        "I'd like a simple overview of Cabrillo savings options (regular, holiday club, money market, certificates, IRAs) before I pick one.",
        "NCUA insurance on savings — how does it work?",
        "Are all Cabrillo savings accounts NCUA insured to $250,000? Any special rules for joint owners?",
    ),
    (
        "FEAT-11",
        "Regular Savings",
        "Keep the $5 share savings open after closing other accounts?",
        "If I close my checking, do I need to keep the $5 Regular Savings open to remain a member?",
        "Transfer from Regular Savings to checking in the app",
        "How do I move money from my Regular Savings to Advantage Checking in Digital Banking?",
    ),
    (
        "FEAT-12",
        "Holiday Club",
        "Set up Holiday Club automatic transfers",
        "I want a Holiday Club account funded automatically from checking. What's the setup process and when is the money available?",
        "Early withdrawal from Holiday Club",
        "Can I withdraw from Holiday Club before the holiday payout date, and are there penalties?",
    ),
    (
        "FEAT-13",
        "Money Market",
        "Money Market $2,500 minimum and check limits",
        "Confirming Money Market needs $2,500 minimum and allows up to 6 checks per month. What happens if I go under the minimum?",
        "Tiered APY on Money Market — where to see current tiers",
        "Where can I see the current tiered APY for Money Market before I transfer funds in?",
    ),
    (
        "FEAT-14",
        "Share Certificates (CDs)",
        "Share Certificate terms and $2,000 minimum",
        "I'd like a Share Certificate (CD). Confirm $2,000 minimum and available terms from 3 to 60 months. Early withdrawal penalty?",
        "CD vs Share Certificate naming",
        "Is a Share Certificate the same as a CD at Cabrillo? I want to ladder two certificates.",
    ),
    (
        "FEAT-15",
        "Market Rate IRA",
        "Open a Market Rate IRA with $1",
        "Can I open a Market Rate (liquid) IRA with $1, and does it compound monthly? Difference vs a certificate IRA?",
        "Contribute to Market Rate IRA this year",
        "How do I make a contribution to my Market Rate IRA before the tax deadline?",
    ),
    (
        "FEAT-16",
        "Investment Rate IRA (Share Certificate)",
        "Investment Rate IRA certificate terms",
        "Looking at the Investment Rate IRA (Share Certificate): confirm $2,000 minimum and terms from 3 months to 5 years.",
        "Rollover 401(k) into Investment Rate IRA certificate",
        "Can I roll an old 401(k) into an Investment Rate IRA certificate at Cabrillo? What's the process?",
    ),
    # --- Credit Cards ---
    (
        "CAPL-7",
        "Credit Cards",
        "Help choosing a Cabrillo VISA credit card",
        "I want a Cabrillo credit card but don't know Traditional vs Signature vs Share Secured. Can you help me compare at a high level?",
        "Credit card application status",
        "I applied for a Cabrillo VISA last week. How do I check application status?",
    ),
    (
        "FEAT-17",
        "Compare VISA Credit Cards",
        "Side-by-side compare of all three VISA cards",
        "Please compare Traditional, Signature, and Share Secured — annual fee, cash back, and who each is best for. I heard all have $0 annual fee.",
        "Which card for rebuilding credit?",
        "Between your three VISA options, which should I choose if I'm rebuilding credit after a bankruptcy discharge?",
    ),
    (
        "FEAT-18",
        "VISA Traditional",
        "VISA Traditional APR range",
        "What's the current variable APR range for VISA Traditional (I saw 10.15–16.15%)? Does it offer cash back?",
        "Lower my VISA Traditional rate",
        "I've had VISA Traditional for 2 years with on-time payments. Can I request a rate review?",
    ),
    (
        "FEAT-19",
        "VISA Signature",
        "VISA Signature cash back and $5,000 minimum line",
        "Confirm Signature is 1% cash back with min $5,000 credit line and APR around 15.15–16.15%. How is cash back redeemed?",
        "Upgrade from Traditional to Signature",
        "Can I upgrade my Traditional card to Signature without a hard pull?",
    ),
    (
        "FEAT-20",
        "VISA Share Secured",
        "VISA Share Secured — how savings backs the line",
        "For Share Secured, confirm min $200 line and APR = Prime + savings APY. How much do I need to deposit to get a $1,000 line?",
        "Release savings after Share Secured history",
        "After 12 months of good payment history on Share Secured, can I convert to an unsecured card and free my savings?",
    ),
    # --- Loans ---
    (
        "CAPL-8",
        "Loans",
        "General consumer loan options",
        "I need financing but I'm not sure if I want personal, auto, or share-secured. Can you outline Cabrillo consumer loan types?",
        "Skip-A-Payment eligibility question",
        "I don't see a Skip-A-Payment banner. How do I know if my loan qualifies, and who do I call?",
    ),
    (
        "FEAT-21",
        "Personal Loan",
        "Personal loan for debt consolidation — rate and terms",
        "Interested in an unsecured personal loan for consolidation. Is it still as low as 8.74% APR, fixed rate, no prepay penalty?",
        "Personal loan application in Digital Banking",
        "Can I apply for a personal loan inside Digital Banking, and what documents are required?",
    ),
    (
        "FEAT-22",
        "Overdraft Line of Credit",
        "Attach Overdraft Line of Credit to checking",
        "How do I add an Overdraft Line of Credit to my Advantage Checking? I saw ~9.65% APR listed — is that current?",
        "Overdraft LOC vs debit card overdraft coverage",
        "What's the difference between Overdraft Line of Credit and Debit Card Coverage opt-in?",
    ),
    (
        "FEAT-23",
        "Share Secured Loan",
        "Share Secured Loan — Share Rate + 3% and term",
        "Confirm Share Secured Loan pricing is Share Rate + 3.00% with terms up to 84 months. Can I borrow against my CD?",
        "Pay off Share Secured Loan early",
        "Is there a prepayment penalty on a Share Secured Loan, and does my share stay frozen until payoff?",
    ),
    (
        "FEAT-24",
        "Auto Loan",
        "Auto refinance rate and cash-back promo",
        "I'd like to refinance my auto loan. Is pricing still as low as 4.54% APR, and are refinance cash-back promos available?",
        "New vs used auto loan — documents needed",
        "Buying a used car this weekend. What do I need for a Cabrillo auto loan pre-approval?",
    ),
    (
        "FEAT-25",
        "Motorcycle, Boat, RV, ATV",
        "RV loan term up to 120 months",
        "Looking at financing a travel trailer. Confirm boats/RVs can go up to 120 months and that rates are fixed.",
        "Motorcycle loan quote",
        "Need a quote for a new motorcycle loan. Is this under the recreational loan program?",
    ),
    # --- Home ---
    (
        "CAPL-9",
        "Home",
        "Home financing options overview",
        "We're first-time buyers and also curious about HELOC later. Can you outline Cabrillo home financing options?",
        "Mortgage vs HELOC — which for home improvements?",
        "Need ~$40k for renovations. Should we look at a cash-out refinance or a HELOC?",
    ),
    (
        "FEAT-26",
        "Home Loans / Mortgages",
        "First-time buyer mortgage programs",
        "Do you offer first-time buyer programs, and can we get conventional vs ARM guidance for a San Diego condo?",
        "Refinance existing mortgage to Cabrillo",
        "We have a mortgage elsewhere. What's the process to refinance to a Cabrillo fixed-rate loan?",
    ),
    (
        "FEAT-27",
        "HELOC",
        "HELOC fees, draw period, and repayment",
        "Confirm HELOC has no setup/annual fees, 10-year draw, 15-year repayment, and variable rates. How do I apply?",
        "HELOC draw access in Digital Banking",
        "Once approved, how do I draw from my HELOC — transfer in Digital Banking or checks?",
    ),
    # --- Digital Banking ---
    (
        "CAPL-10",
        "Digital Banking",
        "Digital Banking help — general navigation",
        "I logged into the new Digital Banking but I'm overwhelmed. Where should I start for basic navigation and Support Hub?",
        "Mobile app vs website features",
        "Is everything available on both the mobile app and desktop Digital Banking, or are some features desktop-only?",
    ),
    (
        "FEAT-28",
        "What's New | Digital Banking",
        "Feb 2026 Digital Banking upgrade — what carries over?",
        "With the platform upgrade, do Bill Pay payees carry over? Do I need to re-enroll alerts and My Credit Score?",
        "Two-factor authentication setup after upgrade",
        "After moving to the new Digital Banking, how do I set up 2FA / authenticator app?",
    ),
    (
        "FEAT-29",
        "Transfers & Payments",
        "Zelle enrollment and send limit questions",
        "How do I enroll in Zelle in Digital Banking, and what are send limits for a new enrollment?",
        "Schedule a loan payment and edit scheduled transfers",
        "I need to schedule a loan payment from checking and also edit an existing scheduled transfer. Where in Transfers & Payments?",
    ),
    (
        "FEAT-30",
        "Card Controls",
        "Lock debit card and set travel notice",
        "I'm traveling to Mexico next week. How do I set a travel notice and temporarily lock/unlock my card in Card Controls?",
        "Merchant and region controls not saving",
        "I tried setting merchant category and region controls but they don't seem to stick. Steps to verify Card Controls settings?",
    ),
    # --- Rates ---
    (
        "CAPL-11",
        "Rates",
        "Where to find current Cabrillo rates",
        "Where on the website are current deposit, loan, and mortgage/HELOC rates published? I don't want outdated numbers.",
        "Rates changed — when do you update the tables?",
        "How often are rate tables updated, and do advertised 'as low as' rates require relationships or credit tiers?",
    ),
    (
        "FEAT-31",
        "Deposit Rates",
        "Current APY for share certificates and money market",
        "Please point me to the current deposit rates page for savings, money market, and share certificate APYs. I need accurate figures for a decision this week.",
        "Advantage Checking dividend rate",
        "Does Advantage Checking earn a dividend, and where is it listed on the deposit rates table?",
    ),
    (
        "FEAT-32",
        "Loan Rates",
        "Current auto and personal loan rate sheet",
        "I need the published loan rates for auto, personal, motorcycle/boat/RV, overdraft LOC, and share secured — not guesses.",
        "Does 'as low as' auto rate require autopay?",
        "Your loan rates say as low as 4.54% APR on autos. What conditions are required to get that rate?",
    ),
    (
        "FEAT-33",
        "Home Equity / Mortgage Rates",
        "Current mortgage and HELOC rate table",
        "Where can I see current fixed/ARM mortgage rates and HELOC terms? Looking to compare before talking to a lender.",
        "HELOC variable rate index",
        "What index does the HELOC use, and where is the current HELOC rate published?",
    ),
    # --- Locations ---
    (
        "CAPL-12",
        "Locations",
        "Find a Cabrillo location near me",
        "I need help finding Cabrillo branches or ATMs near Clairemont. Is there a locator for branches and shared ATMs?",
        "Shared branch vs Cabrillo branch services",
        "What's the difference between a Cabrillo branch and a CO-OP shared branch for deposits and withdrawals?",
    ),
    (
        "FEAT-34",
        "Branches & ATMs",
        "Branch hours and address list",
        "Can you provide addresses and lobby hours for Cabrillo branches? Also confirm CO-OP ATM access with Advantage Checking.",
        "ATM fee reimbursement / CO-OP network",
        "If I use a non-CO-OP ATM, are there fees, and how do I find surcharge-free CO-OP ATMs?",
    ),
    # --- About ---
    (
        "CAPL-13",
        "About",
        "About Cabrillo — mission and history question",
        "A coworker asked about Cabrillo's background. Can you share a short overview of the credit union's story and mission?",
        "Is Cabrillo a nonprofit credit union?",
        "Confirming Cabrillo is member-owned and not-for-profit. Any quick About facts I can share with my family?",
    ),
    (
        "FEAT-35",
        "The Cabrillo Story",
        "Founded 1955 for Border Patrol — more history?",
        "I read Cabrillo was founded in 1955 for Border Patrol. Can you share more of The Cabrillo Story / mission to enrich member-owners' lives?",
        "Request Cabrillo Story materials for new-member welcome",
        "We're onboarding my parents as members. Is there an official Cabrillo Story summary or page I can send them?",
    ),
    (
        "FEAT-36",
        "Inland Credit Union (division)",
        "Inland FCU merger — Legal Day One date",
        "What's the status of the Inland Credit Union merger? I heard Legal Day One is June 1, 2026 — what changes for members then?",
        "When is full Inland integration expected?",
        "Will Inland members keep their accounts through 2027 integration, and where can I read official merger updates?",
    ),
]


def headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def create_ticket(part_id: str, title: str, body: str) -> requests.Response:
    payload = {
        "type": "ticket",
        "title": title[:200],
        "body": body,
        "applies_to_part": part_id,
        "owned_by": [OWNER],
    }
    r = requests.post(f"{BASE}/works.create", json=payload, headers=headers(), timeout=45)
    if r.status_code < 400:
        return r
    # retry without owned_by / with body_type
    for alt in (
        {**payload, "body_type": "text"},
        {"type": "ticket", "title": title[:200], "body": body, "applies_to_part": part_id},
    ):
        r2 = requests.post(f"{BASE}/works.create", json=alt, headers=headers(), timeout=45)
        if r2.status_code < 400:
            return r2
    return r


def main() -> int:
    for k in list(os.environ):
        if "proxy" in k.lower():
            os.environ.pop(k, None)

    org = requests.get(f"{BASE}/dev-orgs.get", headers=headers(), timeout=30)
    org.raise_for_status()
    slug = (org.json().get("dev_org") or {}).get("dev_slug")
    print(f"Org: {slug}")
    print(f"Creating {len(TICKETS) * 2} tickets ({len(TICKETS)} parts × 2)...")

    created = []
    failed = []

    for part_id, part_name, t1, b1, t2, b2 in TICKETS:
        for title, body in ((t1, b1), (t2, b2)):
            full_body = (
                f"Member support request\n"
                f"Channel: email\n"
                f"Part: {part_id} — {part_name}\n\n"
                f"{body}"
            )
            print(f"  {part_id} | {title[:64]}")
            resp = create_ticket(part_id, title, full_body)
            if resp.status_code >= 400:
                print(f"    FAIL {resp.status_code}: {resp.text[:240]}")
                failed.append({"part": part_id, "title": title, "error": resp.text[:500]})
                continue
            work = resp.json().get("work") or {}
            did = work.get("display_id") or work.get("id")
            applies = (work.get("applies_to_part") or {}).get("display_id")
            print(f"    OK {did} → {applies}")
            created.append(
                {
                    "id": did,
                    "title": title,
                    "part_id": part_id,
                    "part_name": part_name,
                    "applies_to_part": applies,
                }
            )
            time.sleep(0.12)

    out = {
        "created_count": len(created),
        "failed_count": len(failed),
        "created": created,
        "failed": failed,
    }
    path = Path(__file__).resolve().parent / "demo_tickets_summary.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("=" * 50)
    print(f"Created: {len(created)}  Failed: {len(failed)}")
    print(f"Wrote {path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
