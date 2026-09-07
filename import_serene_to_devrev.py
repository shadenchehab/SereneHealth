#!/usr/bin/env python3
"""Import Cabrillo CU site inventory into DevRev Parts + KB collections.

Creates:
  - Capabilities under PROD-1 (or PROD-01 display id alias)
  - Features under each capability
  - Published article collections (directories): Support, Q&A, Articles, News
  - External, published KB articles linked to those collections

Usage:
  DEVREV_PAT=... python3 import_cabrillo_to_devrev.py
  python3 import_cabrillo_to_devrev.py --token-file /tmp/cabrillo_devrev_pat
  python3 import_cabrillo_to_devrev.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE = "https://api.devrev.ai"
OWNER = "DEVU-1"
PRODUCT = "PROD-1"
RATE = 0.25

# Capability -> feature titles (from cabrillo site product inventory)
PRODUCT_TREE: Dict[str, List[Tuple[str, str]]] = {
    "Membership": [
        ("Become a Member", "$5 Regular Share Savings. Live/work in San Diego County; Border Patrol, federal agencies, Sharp HealthCare, City of Carlsbad, FORBPO, relatives of members."),
        ("Open an Account", "New members apply online; existing members open additional accounts in Digital Banking."),
    ],
    "Checking": [
        ("Advantage Checking", "Free checking: no monthly fee, no minimum, VISA debit, Zelle, Bill Pay, eStatements, 30k+ CO-OP ATMs."),
        ("Big Easy Checking", "Checking product listed on deposit rates (0.01% APY)."),
        ("Basic Checking", "Non-dividend checking for members with NSF history; $25 minimum open."),
        ("VISA Debit Card", "Contactless EMV debit with tap-to-pay, wallets, Zero Liability."),
    ],
    "Savings": [
        ("Regular Savings", "$5 share establishes membership. NCUA insured to $250,000."),
        ("Holiday Club", "Seasonal savings via automatic transfers from checking."),
        ("Money Market", "$2,500 min. Tiered APY. Up to 6 checks/month."),
        ("Share Certificates (CDs)", "$2,000 min. Terms 3–60 months. Competitive APYs."),
        ("Market Rate IRA", "Liquid IRA savings, compounds monthly, open with $1."),
        ("Investment Rate IRA (Share Certificate)", "Fixed-rate IRA certificate, $2,000 min, terms 3 months–5 years."),
    ],
    "Credit Cards": [
        ("Compare VISA Credit Cards", "Traditional, Signature, and Share Secured — all $0 annual fee."),
        ("VISA Traditional", "Low-rate everyday card. Variable APR 10.15–16.15%. No cash back."),
        ("VISA Signature", "1% cash back. Variable APR 15.15–16.15%. Min $5,000 credit line."),
        ("VISA Share Secured", "Credit-builder backed by savings. Min $200 line. APR = Prime + savings APY."),
    ],
    "Loans": [
        ("Personal Loan", "Unsecured as low as 8.74% APR. Debt consolidation, fixed rate, no prepay penalty."),
        ("Overdraft Line of Credit", "Revolving overdraft attached to checking. Listed ~9.65% APR."),
        ("Share Secured Loan", "Share Rate + 3.00%. Terms up to 84 months."),
        ("Auto Loan", "New/used/refinance. As low as 4.54% APR. Refinance cash-back promos may apply."),
        ("Motorcycle, Boat, RV, ATV", "Fixed-rate recreational loans; boats/RVs up to 120 months."),
    ],
    "Home": [
        ("Home Loans / Mortgages", "Conventional, jumbo, fixed, ARM, refinance, cash-out, first-time buyer programs."),
        ("HELOC", "No setup/annual fees. 10-year draw, 15-year repayment. Variable rates."),
    ],
    "Digital Banking": [
        ("What's New | Digital Banking", "Platform upgrade (Feb 2026): dashboard, transfers, card controls, 2FA, My Credit Score."),
        ("Transfers & Payments", "Internal/external transfers, Bill Pay, Zelle, member-to-member, loan payments."),
        ("Card Controls", "Lock/unlock, PIN, travel notices, merchant/transaction/region controls, alerts."),
    ],
    "Rates": [
        ("Deposit Rates", "Savings, checking, money market, share certificates."),
        ("Loan Rates", "Auto, motorcycle, boats/RVs, personal, overdraft, share secured."),
        ("Home Equity / Mortgage Rates", "Fixed/ARM mortgage table plus HELOC terms."),
    ],
    "Locations": [
        ("Branches & ATMs", "Cabrillo branches plus shared branches/ATMs (CO-OP)."),
    ],
    "About": [
        ("The Cabrillo Story", "Founded 1955 for Border Patrol. Mission: enrich lives of member-owners."),
        ("Inland Credit Union (division)", "Inland FCU merger — Legal Day One Jun 1, 2026; full integration expected 2027."),
    ],
}

# KB rows: (collection, title, url, notes)
KB_ROWS: List[Tuple[str, str, str, str]] = [
    # Support
    ("Support", "FAQ Support Hub — Digital Banking", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Main public how-to + video hub. Categories: Getting Started, Card Controls/Alerts/Security, Payments & Transfers, Accounts & Services."),
    ("Support", "Getting Started with Digital Banking", "https://www.cabrillocu.com/Digital-Banking/Get-Started", "Upgrade enrollment, what carries over (Bill Pay), re-enroll alerts / MyCreditScore / PFM tools."),
    ("Support", "Digital Banking Transition (NCCU Onboarding)", "https://www.cabrillocu.com/Digital-Banking/NCCU-Onboarding", "Transition/onboarding page for the upgraded platform."),
    ("Support", "In-app Support Hub", "https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Digital-Banking/Where-can-I-find-help-or-FAQs-in-Digital-Banking", "Question-mark / speech-bubble inside logged-in Digital Banking and the mobile app."),
    ("Support", "Contact Us", "https://www.cabrillocu.com/About-Us/General/Contact-Us", "Virtual Branch 858.547.7400 / 800.222.7455. Routing 322274488. Chat/text hours."),
    ("Support", "FAQ index (General)", "https://www.cabrillocu.com/Resources/FAQs/General/", "CMS FAQ tree at /Resources/FAQs/{Category}/{Subcategory}/{slug}."),
    ("Support", "Old Member Resources FAQs", "https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/eBranch/I-m-unable-to-view-my-eStatements", "Legacy /Resources-old/Member-Resources/FAQs/ still indexed (eBranch, Mobile Deposit, Loans)."),
    # Q&A
    ("Q&A", "How to log in to the new Digital Banking experience?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Mobile vs desktop login, identity verify, new password, disclosures, re-enroll alerts/tools."),
    ("Q&A", "How do I customize my Digital Banking dashboard?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Pencil/eye icons, reorder tiles, Recent Transactions filter."),
    ("Q&A", "How does enhanced security and two-factor authentication work?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "2FA, authenticator app, push authentication. Basic → Intermediate → Advanced."),
    ("Q&A", "Where can I find Digital Banking help and support?", "https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Digital-Banking/Where-can-I-find-help-or-FAQs-in-Digital-Banking", "Support Hub icon, View All FAQs, search."),
    ("Q&A", "Where can I view my recent transactions?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Dashboard tile, per-account history, search."),
    ("Q&A", "How do I reset my username or password?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Profile → Security; verification code required."),
    ("Q&A", "How do I send a secure message?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Message Center via three-dot menu. Attachments supported."),
    ("Q&A", "What are secure forms and how do I use them?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Examples: international wire, loan due-date change. Secure Form History."),
    ("Q&A", "How do I navigate the Digital Banking dashboard on desktop?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Tiles, nav bar, extended menu (Bill Pay, forms, travel, alerts, statements)."),
    ("Q&A", "What are advanced subscription alerts?", "https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Card-Controls/What-are-Subscription-Alerts-(Advanced-Card-Alerts", "Card, account, Bill Pay, and security alerts."),
    ("Q&A", "How do card controls work?", "https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Card-Controls/Where-do-I-access-Card-Controls", "Lock/unlock, replacement, lost/stolen, travel, PIN, merchant/transaction/region."),
    ("Q&A", "Can I turn my card on or off?", "https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Card-Controls/Can-I-turn-my-card-on-or-off", "Standalone FAQ; same Card Controls path."),
    ("Q&A", "How do I set up travel notifications?", "https://www.cabrillocu.com/Digital-Banking/Card-Controls", "Travel Notices on card account; domestic vs international."),
    ("Q&A", "How do I make a loan payment?", "https://www.cabrillocu.com/Digital-Banking/Payments-and-Transfers", "From dashboard or loan account; Cabrillo or external funding; now or scheduled."),
    ("Q&A", "How do I make a credit card payment?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Min / statement / current / custom; one-time or recurring."),
    ("Q&A", "How do I edit or delete scheduled transfers?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Make a Transfer → Scheduled Transfers."),
    ("Q&A", "Can I review my scheduled loan payments?", "https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Payments-Transfers/Can-I-review-my-scheduled-loan-payments", "Standalone FAQ under Resources-Payments-Transfers."),
    ("Q&A", "How do I make a one-time or scheduled transfer?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Internal transfers; frequency and date options."),
    ("Q&A", "How do I add an external account?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Instant Account Verification or manual entry."),
    ("Q&A", "How do I pay my loan with a debit card?", "https://www.cabrillocu.com/Digital-Banking/Payments-and-Transfers", "Make a Transfer → Pay a Cabrillo Loan with a Debit Card."),
    ("Q&A", "How do member-to-member transfers work?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Create/share M2M code; send to another Cabrillo member."),
    ("Q&A", "How do I send with Zelle®?", "https://www.cabrillocu.com/Digital-Banking/Payments-and-Transfers", "Enroll with email/phone; send, request, split, activity."),
    ("Q&A", "How do I set up / schedule Bill Pay?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Pay My Bills; eBills, AutoPay, payee manage."),
    ("Q&A", "How do overdraft services work?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Overdraft Transfer + Debit Card Coverage opt-in."),
    ("Q&A", "How do I set up direct deposit?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Connect employer/payroll provider from Digital Banking."),
    ("Q&A", "How do I enroll in eStatements / view documents?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Documents & Statements; paperless settings."),
    ("Q&A", "How to enroll and use My Credit Score?", "https://www.cabrillocu.com/Digital-Banking/FAQs-Digital-Banking-Support", "Soft pull. Score, report, alerts, simulator, debt analysis."),
    ("Q&A", "Can I deposit checks with the mobile app?", "https://www.cabrillocu.com/Digital-Banking/Online-Mobile-Digital-Banking", "Mobile Deposit after Digital Banking enrollment."),
    ("Q&A", "Can I transfer money to another financial institution?", "https://www.cabrillocu.com/Digital-Banking/Online-Mobile-Digital-Banking", "Yes — one-time or recurring external transfers."),
    ("Q&A", "Can I apply for a loan through Online Banking?", "https://www.cabrillocu.com/Digital-Banking/Online-Mobile-Digital-Banking", "Loans, credit cards, and other products from inside Digital Banking."),
    ("Q&A", "Advantage Checking related FAQs", "https://www.cabrillocu.com/Checking", "Fees, debit/wallets, ATMs, Zelle, digital features, open online, order checks."),
    ("Q&A", "Savings related FAQs", "https://www.cabrillocu.com/Savings", "Open requirements, account types, NCUA, fees, vs money market/certificates."),
    ("Q&A", "What is the difference between CDs and Share Certificates?", "https://www.cabrillocu.com/Resources/FAQs/Savings-Accounts/Savings-Share-Certificates/What-is-the-difference-between-CDs-and-Share-Certi", "Banks vs credit unions; both insured."),
    ("Q&A", "Money Market related FAQs", "https://www.cabrillocu.com/Savings/Money-Market", "Min $2,500, vs savings, 6-check limit, no monthly fee."),
    ("Q&A", "Share Certificate related FAQs", "https://www.cabrillocu.com/savings/certificates-san-diego", "$2,000 min, terms, rates, maturity/10-day grace, NCUA."),
    ("Q&A", "IRA related FAQs", "https://www.cabrillocu.com/Savings/IRA-Retirement-Account", "IRA savings vs certificate, withdrawals, Roth vs Traditional."),
    ("Q&A", "Personal loan related FAQs", "https://www.cabrillocu.com/loans/personal-loan", "Documents, no prepay penalty, amount, rate, debt consolidation, apply online."),
    ("Q&A", "Motorcycle/Boat/RV related FAQs", "https://www.cabrillocu.com/loans/motorcycle-boat-rv", "How they work, docs, rates, terms, vs auto loan."),
    ("Q&A", "Home loan related FAQs", "https://www.cabrillocu.com/loans/home-loans", "Types, down payment, pre-qualify, docs, close timeline, fixed vs ARM."),
    ("Q&A", "HELOC related FAQs", "https://www.cabrillocu.com/loans/home-loans/home-equity-line-of-credit", "What a HELOC is, draw/repay, no fees, uses, vs home equity loan."),
    ("Q&A", "What credit cards do you offer?", "https://www.cabrillocu.com/Resources/FAQs/Credit-Cards/Credit-Cards-Compare-Credit-Cards/What-credit-cards-do-you-offer", "Traditional, Signature, Share Secured."),
    ("Q&A", "What do I need to sign up for a credit card?", "https://www.cabrillocu.com/Resources/FAQs/Credit-Cards/Credit-Cards-Signature/What-do-I-need-to-sign-up-for-a-credit-card", "Must be a member; personal/financial info; credit review."),
    ("Q&A", "What is Card Controls and can I use it with Share Secured?", "https://www.cabrillocu.com/Resources/FAQs/Credit-Cards/Credit-Cards-Share-Secured/What-is-Card-Controls-and-can-I-use-it-with-this-c", "Yes — lock, limits, alerts, travel via app/online banking."),
    ("Q&A", "Can you please provide the Address For each Branch Location?", "https://www.cabrillocu.com/Resources/FAQs/General/General-FAQ/Can-you-please-provide-the-Address-For-each-Branch", "Points to Branch & ATM Locator."),
    ("Q&A", "Customer service", "https://www.cabrillocu.com/Resources/FAQs/General/General-FAQ/Customer-service", "Virtual Service Center 858.547.7400."),
    ("Q&A", "Member Service / Card Support Hours / Phone Number", "https://www.cabrillocu.com/Resources/FAQs/General/General-FAQ/Member-Service-Card-Support-Hours-Phone-Number", "Same VSC number during business hours."),
    ("Q&A", "I'm unable to view my eStatements", "https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/eBranch/I-m-unable-to-view-my-eStatements", "Legacy eBranch path. Prefer new Digital Banking Documents & Statements."),
    ("Q&A", "How do I enroll in Mobile Deposit?", "https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/Mobile-Deposit/How-do-I-enroll-in-Mobile-Deposit", "Eligibility via Member Support 800.222.7455."),
    ("Q&A", "I do not see a Skip-A-Payment banner. How do I request to Skip my payment?", "https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/Loans/I-do-not-see-a-Skip-A-Payment-banner-How-do-I-requ", "Legacy loans FAQ. Call 800.222.7455."),
    # Articles
    ("Articles", "Stop. Check. Protect. How to Avoid Account Takeover Scams", "https://www.cabrillocu.com/articles", "Financial Education — phone/text/email/fake-site impersonation (Aug 2026)."),
    ("Articles", "Summer Travel Scams: How to Protect Yourself", "https://www.cabrillocu.com/articles", "Financial Education — fake rentals, travel deals, insurance scams (Jun 2026)."),
    ("Articles", "Refinance Your Auto Loan and Receive 1% Cash Back*", "https://www.cabrillocu.com/articles/Promotions-Offers/June-2026/Get-1-Cash-Back-When-You-Refinance-Your-Auto-Loan", "Up to $400. Funded by Aug 7, 2026. Existing Cabrillo loans excluded."),
    ("Articles", "Go Paperless with eStatements", "https://www.cabrillocu.com/articles/Products-Services/April-2026/Go-Paperless-with-eStatements-Earth-Day", "Earth Day enrollment/how-to for eStatements in Digital Banking."),
    ("Articles", "Adventure Into a Branch!", "https://www.cabrillocu.com/articles", "Promotions — bring-your-child-to-a-branch savings intro."),
    ("Articles", "Romance Scams: Financial Fraud", "https://www.cabrillocu.com/articles", "Financial Education (Apr 2026)."),
    ("Articles", "Imposter Scams: How to Spot Someone Pretending to Be Your Bank", "https://www.cabrillocu.com/articles", "Financial Education (Apr 2026)."),
    ("Articles", "Never Share Your Verification Code: The One-Time Passcode Scam", "https://www.cabrillocu.com/articles", "Financial Education."),
    ("Articles", "Fraud Tips: Protect Your Money and Identity", "https://www.cabrillocu.com/articles", "Financial Education (Mar 2026)."),
    ("Articles", "HELOC Fraud is on the Rise", "https://www.cabrillocu.com/articles", "Financial Education."),
    ("Articles", "Your guide to logging in and getting started with Digital Banking", "https://www.cabrillocu.com/articles/Products-Services/February-2026/Login-Digital-Banking-Upgrade", "Enrollment after Feb 2026 upgrade. Re-enroll alerts, MyCreditScore, PFM."),
    ("Articles", "NCCU Login / Digital Banking Upgrade", "https://www.cabrillocu.com/articles/Products-Services/February-2026/NCCU-Login-Digital-Banking-Upgrade", "Related upgrade/login article."),
    ("Articles", "18/24-Month Share Certificates promo", "https://www.cabrillocu.com/articles/Promotions-Offers/January-2025/24-Month-Share-Certificate", "Older promo (Jan 2025)."),
    ("Articles", "Consolidate Your Debt with New Low Rates!", "https://www.cabrillocu.com/articles/Promotions-Offers/September-2024/Take-Control-of-Your-Debt-with-a-Personal-Loan", "Personal loan 8.74% APR promo (Sep 2024)."),
    ("Articles", "San Diego Credit Union Open An Account", "https://www.cabrillocu.com/articles/Credit-Union/February-2024/San-Diego-Credit-Union-Open-An-Account", "How to join / apply. Membership eligibility."),
    ("Articles", "San Diego Credit Union Contact", "https://www.cabrillocu.com/articles/Credit-Union/March-2024/San-Diego-Credit-Union-Contact", "Contact numbers, hours, routing."),
    ("Articles", "San Diego Credit Union Auto Loan Rates", "https://www.cabrillocu.com/articles/Products-Services/February/San-Diego-Credit-Union-Auto-Loan-Rates", "Older rates article. Live rates on /Rates/Loan-Rates."),
    ("Articles", "San Diego ATV Loan", "https://www.cabrillocu.com/articles/Products-Services/June-2024/San-Diego-ATV-Loan", "ATV financing explainer; points to recreational loan apply."),
    # News
    ("News", "Sponsors the 23rd Annual Sharp HospiceCare Benefit Dinner and Regatta", "https://www.cabrillocu.com/news-press", "Aug 25, 2026. Community Outreach. Honorary Admiral Sponsor."),
    ("News", "Celebrating the Credit Union Difference on I Love My Credit Union Day", "https://www.cabrillocu.com/news-press", "Jul 31, 2026. Community Outreach."),
    ("News", "FORBPO 47th Annual Conference & Golf Tournament", "https://www.cabrillocu.com/news-press", "Jul 27, 2026. Community Outreach."),
    ("News", "Annual Brown Field Station Cornhole Tournament", "https://www.cabrillocu.com/news-press", "Jul 24, 2026. Border Patrol / community."),
    ("News", "14th Annual Summer Showdown", "https://www.cabrillocu.com/news-press", "Jul 20, 2026. Border Patrol softball, Chula Vista."),
    ("News", "2026 Annual Report Meeting", "https://www.cabrillocu.com/news-press", "Jul 1, 2026."),
    ("News", "A New Chapter for Sharp Tri-City Medical Center", "https://www.cabrillocu.com/news-press", "Jul 1, 2026. Partner milestone."),
    ("News", "7th Annual SHARP Appreciation Luncheon", "https://www.cabrillocu.com/news-press", "Jun 11, 2026. Community Outreach."),
    ("News", "Inland Federal Credit Union Members Approve Merger", "https://www.cabrillocu.com/news-press/Press/June-2026/Inland-Federal-Credit-Union-Members-Approve-Merger", "Jun 2, 2026. Inland becomes a division Jun 1, 2026; full ops integration 2027."),
    ("News", "Padres Staff Game", "https://www.cabrillocu.com/news-press", "May 30, 2026. Community Outreach."),
    ("News", "7th Annual Border Patrol Appreciation Month", "https://www.cabrillocu.com/news-press", "May 1, 2026. NBPC Local 1613 / MWR."),
    ("News", "Celebrating a New Chapter: Carmel Mountain Branch", "https://www.cabrillocu.com/news-press", "Apr 15, 2026. New Carmel Mountain branch."),
]


def load_token(token_file: Optional[str]) -> str:
    token = (os.environ.get("DEVREV_PAT") or os.environ.get("DEVREV_API_TOKEN") or "").strip()
    if not token and token_file:
        token = Path(token_file).read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("Set DEVREV_PAT or pass --token-file")
    return token


def api(token: str, method: str, path: str, body: Optional[dict] = None) -> Tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"message": raw}
        return e.code, parsed


def sleep() -> None:
    time.sleep(RATE)


def ensure_product(token: str) -> str:
    for pid in (PRODUCT, "PROD-01"):
        code, data = api(token, "GET", f"/parts.get?id={pid}")
        if code == 200 and data.get("part"):
            part = data["part"]
            print(f"Product: {part.get('display_id')} — {part.get('name')}")
            return part.get("display_id") or PRODUCT
    raise SystemExit("PROD-1 not found. Create product 'Cabrillo Credit Union' first.")


def list_parts_by_type(token: str, types: List[str]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    cursor = None
    while True:
        body: Dict[str, Any] = {"type": types, "limit": 100}
        if cursor:
            body["cursor"] = cursor
        code, data = api(token, "POST", "/parts.list", body)
        if code >= 400:
            break
        for p in data.get("parts") or []:
            name = (p.get("name") or "").strip()
            if name:
                out[name] = p
        cursor = data.get("next_cursor")
        if not cursor:
            break
        sleep()
    return out


def create_capability(token: str, name: str, parent: str, dry_run: bool) -> Optional[str]:
    if dry_run:
        print(f"  [dry] capability {name}")
        return f"DRY-{name}"
    code, data = api(
        token,
        "POST",
        "/parts.create",
        {
            "type": "capability",
            "name": name,
            "description": f"Cabrillo Credit Union — {name}",
            "parent_part": [parent],
            "owned_by": [OWNER],
        },
    )
    if code in (200, 201):
        part = data["part"]
        print(f"  + capability {part.get('display_id')} {name}")
        return part.get("display_id")
    print(f"  ! capability {name}: {code} {data}")
    return None


def create_feature(token: str, name: str, description: str, parent_cap: str, dry_run: bool) -> Optional[str]:
    if dry_run:
        print(f"    [dry] feature {name}")
        return f"DRY-{name}"
    code, data = api(
        token,
        "POST",
        "/parts.create",
        {
            "type": "feature",
            "name": name,
            "description": description[:1900],
            "parent_part": [parent_cap],
            "owned_by": [OWNER],
        },
    )
    if code in (200, 201):
        part = data["part"]
        print(f"    + feature {part.get('display_id')} {name}")
        return part.get("display_id")
    print(f"    ! feature {name}: {code} {data}")
    return None


def list_directories(token: str) -> Dict[str, dict]:
    code, data = api(token, "POST", "/directories.list", {"limit": 100})
    out: Dict[str, dict] = {}
    if code < 400:
        for d in data.get("directories") or []:
            title = (d.get("title") or "").strip()
            if title:
                out[title] = d
    return out


def ensure_collection(token: str, title: str, dry_run: bool) -> Optional[str]:
    existing = list_directories(token).get(title)
    if existing:
        did = existing.get("display_id") or existing.get("id")
        if not existing.get("published") and not dry_run:
            api(token, "POST", "/directories.update", {"id": did, "published": True})
            print(f"  ~ collection {title} published ({did})")
        else:
            print(f"  = collection {title} ({did})")
        return existing.get("id") or did
    if dry_run:
        print(f"  [dry] collection {title}")
        return f"DRY-DIR-{title}"
    code, data = api(token, "POST", "/directories.create", {"title": title, "published": True})
    if code in (200, 201):
        d = data["directory"]
        print(f"  + collection {d.get('display_id')} {title} published={d.get('published')}")
        return d.get("id")
    print(f"  ! collection {title}: {code} {data}")
    return None


def list_articles_by_title(token: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    cursor = None
    while True:
        body: Dict[str, Any] = {"limit": 100}
        if cursor:
            body["cursor"] = cursor
        code, data = api(token, "POST", "/articles.list", body)
        if code >= 400:
            break
        for a in data.get("articles") or []:
            title = (a.get("title") or "").strip()
            if title:
                out[title] = a
        cursor = data.get("next_cursor")
        if not cursor:
            break
        sleep()
    return out


def article_markdown(title: str, url: str, notes: str, collection: str) -> str:
    return (
        f"# {title}\n\n"
        f"**Collection:** {collection}\n\n"
        f"**Source:** {url}\n\n"
        f"{notes}\n\n"
        f"This article was imported from Cabrillo Credit Union public website content "
        f"for the cabrillo-demo DevRev knowledge base.\n"
    )


def create_article(
    token: str,
    title: str,
    url: str,
    notes: str,
    collection_id: str,
    part_id: str,
    dry_run: bool,
) -> Optional[str]:
    if dry_run:
        print(f"  [dry] article {title[:60]}")
        return "DRY-ART"
    desc = notes[:1800] if notes else title
    # Unique resource URL per article (API requires resource.url in this org)
    # Keep original URL; append fragment when duplicates share a listing page.
    resource_url = url
    body = {
        "title": title[:240],
        "owned_by": [OWNER],
        "applies_to_parts": [part_id],
        "status": "published",
        "access_level": "external",
        "description": desc,
        "resource": {"url": resource_url},
        "parent": collection_id,
    }
    code, data = api(token, "POST", "/articles.create", body)
    if code >= 400 and "already" in str(data).lower():
        # retry with fragment
        body["resource"] = {"url": f"{url}#{re.sub(r'[^a-z0-9]+', '-', title.lower())[:60]}"}
        code, data = api(token, "POST", "/articles.create", body)
    if code in (200, 201):
        art = data["article"]
        print(f"  + {art.get('display_id')} [{art.get('status')}] {title[:70]}")
        return art.get("display_id")
    # Duplicate title may fail differently — try unique URL fragment
    if code >= 400:
        body["resource"] = {"url": f"{url}#{abs(hash(title)) % 10_000_000}"}
        code, data = api(token, "POST", "/articles.create", body)
        if code in (200, 201):
            art = data["article"]
            print(f"  + {art.get('display_id')} [{art.get('status')}] {title[:70]}")
            return art.get("display_id")
    print(f"  ! article {title[:50]}: {code} {data}")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", default="/tmp/cabrillo_devrev_pat")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--parts-only", action="store_true")
    parser.add_argument("--articles-only", action="store_true")
    parser.add_argument("--limit-articles", type=int, default=0)
    args = parser.parse_args()

    token = load_token(args.token_file)
    code, me = api(token, "GET", "/dev-users.self")
    if code >= 400:
        raise SystemExit(f"Auth failed: {code} {me}")
    print(f"Auth OK as {me.get('dev_user', {}).get('email')}")

    product = ensure_product(token)
    summary: Dict[str, Any] = {"product": product, "capabilities": {}, "collections": {}, "articles": []}

    if not args.articles_only:
        print("\n=== Parts: capabilities + features ===")
        caps = list_parts_by_type(token, ["capability"])
        feats = list_parts_by_type(token, ["feature"])
        for cap_name, features in PRODUCT_TREE.items():
            existing = caps.get(cap_name)
            if existing and not existing.get("name", "").startswith("Default"):
                cap_id = existing.get("display_id")
                print(f"  = capability {cap_id} {cap_name}")
            else:
                cap_id = create_capability(token, cap_name, product, args.dry_run)
                sleep()
            if not cap_id:
                continue
            summary["capabilities"][cap_name] = {"id": cap_id, "features": []}
            for feat_name, feat_desc in features:
                if feat_name in feats and not str(feats[feat_name].get("name", "")).startswith("Default"):
                    fid = feats[feat_name].get("display_id")
                    print(f"    = feature {fid} {feat_name}")
                else:
                    fid = create_feature(token, feat_name, feat_desc, cap_id, args.dry_run)
                    sleep()
                if fid:
                    summary["capabilities"][cap_name]["features"].append({"id": fid, "name": feat_name})

    if args.parts_only:
        Path("cabrillo_import_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("Wrote cabrillo_import_summary.json")
        return 0

    print("\n=== Collections (directories) ===")
    collection_ids: Dict[str, str] = {}
    for title in ("Support", "Q&A", "Articles", "News"):
        cid = ensure_collection(token, title, args.dry_run)
        sleep()
        if cid:
            collection_ids[title] = cid
            summary["collections"][title] = cid

    print("\n=== Articles (external + published) ===")
    existing_arts = {} if args.dry_run else list_articles_by_title(token)
    # Skip prior probe articles
    skip_titles = {"News Item Three", "News Item With Parent", "T1", "T2", "T3", "T4", "T5", "T6", "T7"}
    rows = KB_ROWS
    if args.limit_articles:
        rows = rows[: args.limit_articles]
    created = 0
    skipped = 0
    for collection, title, url, notes in rows:
        if title in skip_titles:
            continue
        if title in existing_arts:
            art = existing_arts[title]
            print(f"  = {art.get('display_id')} {title[:70]}")
            skipped += 1
            summary["articles"].append({"title": title, "id": art.get("display_id"), "collection": collection, "status": "existing"})
            continue
        cid = collection_ids.get(collection)
        if not cid and not args.dry_run:
            print(f"  ! missing collection {collection}")
            continue
        aid = create_article(token, title, url, notes, cid or "", product, args.dry_run)
        sleep()
        if aid:
            created += 1
            summary["articles"].append({"title": title, "id": aid, "collection": collection, "status": "created"})

    summary["counts"] = {
        "capabilities": len(summary.get("capabilities") or {}),
        "features": sum(len(v.get("features") or []) for v in (summary.get("capabilities") or {}).values()),
        "collections": len(summary.get("collections") or {}),
        "articles_created": created,
        "articles_skipped": skipped,
    }
    Path("cabrillo_import_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n=== Done ===")
    print(json.dumps(summary["counts"], indent=2))
    print("Wrote cabrillo_import_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
