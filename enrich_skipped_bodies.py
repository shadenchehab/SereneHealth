#!/usr/bin/env python3
"""Re-upload rich Content bodies for articles that had Extraction skipped."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

BASE = "https://api.devrev.ai"
TOKEN = Path("/tmp/cabrillo_devrev_pat").read_text().strip()

# Full answers fetched from cabrillocu.com (WebFetch) for extraction-skipped articles
BODIES: Dict[str, str] = {
    "ART-6": """# In-app Support Hub

**Source:** https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Digital-Banking/Where-can-I-find-help-or-FAQs-in-Digital-Banking

## Where can I find help or FAQs in Digital Banking?

If you need assistance or have a question, Digital Banking includes a built-in Support Hub. You can access it by selecting the support icon (question mark or speech bubble) in Digital Banking or in the mobile app.

Inside the Support Hub, you’ll find:
- Virtual Service Center contact information, including service and loan hours
- Quick links to helpful resources and webpages
- Popular FAQs, plus **View All FAQs** to browse or search Cabrillo’s full Digital Banking FAQ library

Selecting a question takes you directly to the answer.
""",
    "ART-7": """# Contact Us

**Source:** https://www.cabrillocu.com/About-Us/General/Contact-Us

## Virtual Branch
For General Questions call **858.547.7400** or **800.222.7455**

### Member Support Hours
- Monday - Thursday: 7:30 AM - 5:00 PM PT
- Friday: 7:30 AM – 6:00 PM PT

## Cards
- Card Activation: 866.762.0558
- PIN Change: 866.762.0558
- Lost or Stolen Card: 888.241.2510

## Live Chat
Chat hours: Monday - Friday: 9:00 AM - 4:30 PM PT

## Additional Information
- Fax Number: 858.547.0804
- Routing Number: **322274488**

## Mailing Address
Cabrillo Credit Union  
PO Box 261169  
San Diego, CA 92196-1169

## Supervisory Committee Address
Supervisory Committee  
PO Box 261224  
San Diego, CA 92196

For account-specific questions, call or send a secure Digital Banking / eBranch message. Do not include account numbers or Social Security numbers in general email.
""",
    "ART-8": """# FAQ index (General)

**Source:** https://www.cabrillocu.com/Resources/FAQs/General/

Cabrillo maintains a FAQ library under `/Resources/FAQs/`.

Browse by category (examples):
- General FAQ (branches, customer service, hours/phone)
- Resources — Digital Banking
- Resources — Card Controls
- Resources — Payments & Transfers
- Savings Accounts / Share Certificates
- Credit Cards (Compare, Signature, Share Secured)
- Loans

Members can also open the **Support Hub** inside Digital Banking (question mark / speech bubble) and choose **View All FAQs** to search across products and services.
""",
    "ART-9": """# Old Member Resources FAQs

**Source:** https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/eBranch/I-m-unable-to-view-my-eStatements

Some older FAQs still live under `/Resources-old/Member-Resources/FAQs/` and use legacy **eBranch** wording.

Examples of legacy topics:
- eStatements viewing path in older eBranch
- Mobile Deposit enrollment via eServices
- Skip-A-Payment banner troubleshooting

For current steps, prefer the upgraded **Digital Banking** Support Hub and Documents & Statements flows. If a member is following an old eBranch path and it does not match what they see, clarify they may be on the new Digital Banking experience (launched February 2026).
""",
    "ART-13": """# Where can I find Digital Banking help and support?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Digital-Banking/Where-can-I-find-help-or-FAQs-in-Digital-Banking

If you need assistance or have a question, Digital Banking includes a built-in Support Hub. Access it by selecting the support icon (question mark or speech bubble) in Digital Banking or in the mobile app.

Inside the Support Hub you can:
- View Virtual Service Center contact information, including service and loan hours
- Use quick links to helpful webpages and resources
- Browse Popular FAQs, then select **View All FAQs** for the full Digital Banking FAQ library
- Search FAQs across products and services

Selecting a question takes you directly to the answer.
""",
    "ART-20": """# How do card controls work? / Where do I access Card Controls?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Card-Controls/Where-do-I-access-Card-Controls

Log in to Cabrillo’s Digital Banking on the mobile app or desktop. Select the account that has an associated card, then choose **Card Controls**.

From Card Controls you can:
- Lock or unlock your card
- Report it lost or stolen
- Request a replacement
- Set travel notices and alerts
- Manage your PIN
- Adjust advanced controls such as merchant categories, transaction types, regional restrictions, and international use

Select **Save** to apply any changes.
""",
    "ART-21": """# Can I turn my card on or off?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Card-Controls/Can-I-turn-my-card-on-or-off

Log in to Cabrillo’s Digital Banking on the mobile app or desktop. Select the account that has an associated card, then choose **Card Controls**.

From here, you can lock or unlock your card, report it lost or stolen, request a replacement, set travel notices and alerts, manage your PIN, and adjust advanced controls such as merchant categories, transaction types, regional restrictions, and international use.
""",
    "ART-26": """# Can I review my scheduled loan payments?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Resources/Resources-Payments-Transfers/Can-I-review-my-scheduled-loan-payments

Yes. Navigate to **Scheduled Transfers** or the loan account in Digital Banking to view upcoming payments. From there, you can review details, edit payment amounts or dates, or cancel scheduled payments as needed.
""",
    "ART-42": """# What is the difference between CDs and Share Certificates?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Savings-Accounts/Savings-Share-Certificates/What-is-the-difference-between-CDs-and-Share-Certi

CDs and Share Certificates are both deposit accounts with fixed rates for a set term. The main difference is that **CDs are offered by banks**, while **Share Certificates are offered by credit unions**. Both are federally insured and designed to help you grow your money safely.
""",
    "ART-50": """# What credit cards do you offer?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Credit-Cards/Credit-Cards-Compare-Credit-Cards/What-credit-cards-do-you-offer

We offer:
- VISA® Traditional Credit Card
- VISA® Signature Credit Card
- VISA® Share Secured Credit Card

Each card is designed for different needs, from everyday spending to earning rewards or building credit. All listed Cabrillo VISA credit cards have **no annual fee**.
""",
    "ART-51": """# What do I need to sign up for a credit card?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Credit-Cards/Credit-Cards-Signature/What-do-I-need-to-sign-up-for-a-credit-card

To apply for a Cabrillo credit card, you must be a **Cabrillo member**. During the application, you’ll provide basic personal and financial information such as your name, address, Social Security Number, income, and employment details. Your credit history and other factors are reviewed to determine eligibility.
""",
    "ART-52": """# What is Card Controls and can I use it with a Share Secured card?

**Source:** https://www.cabrillocu.com/Resources/FAQs/Credit-Cards/Credit-Cards-Share-Secured/What-is-Card-Controls-and-can-I-use-it-with-this-c

Yes. Card Controls let you turn your card on or off instantly, set purchase limits, receive alerts, and add travel notifications, all through the Cabrillo mobile app or Online Banking / Digital Banking.
""",
    "ART-53": """# Can you please provide the Address For each Branch Location?

**Source:** https://www.cabrillocu.com/Resources/FAQs/General/General-FAQ/Can-you-please-provide-the-Address-For-each-Branch

You can find the address for each branch location on our website using the **Branch & ATM Locator**:  
https://www.cabrillocu.com/ATMs-and-Locations/Cabrillo-Branches-and-ATMs
""",
    "ART-54": """# Customer service

**Source:** https://www.cabrillocu.com/Resources/FAQs/General/General-FAQ/Customer-service

For customer service assistance, contact our Virtual Service Center at **858.547.7400** during business hours.

Also available: **800.222.7455**  
Hours (Pacific Time): Monday–Thursday 7:30 AM–5:00 PM; Friday 7:30 AM–6:00 PM.
""",
    "ART-55": """# Member Service / Card Support Hours / Phone Number

**Source:** https://www.cabrillocu.com/Resources/FAQs/General/General-FAQ/Member-Service-Card-Support-Hours-Phone-Number

Member service and card support are available through the Virtual Service Center at **858.547.7400** during regular business hours.

Additional card numbers (from Contact Us):
- Card Activation / PIN Change: 866.762.0558
- Lost or Stolen Card: 888.241.2510
""",
    "ART-56": """# I'm unable to view my eStatements (legacy eBranch path)

**Source:** https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/eBranch/I-m-unable-to-view-my-eStatements

Legacy eBranch steps:
1. Login to eBranch
2. Click Services → eStatements
3. Select your primary savings account
4. Select the + sign to view eStatements

**Current Digital Banking note:** In the upgraded Digital Banking experience, use **Documents & Statements** from the menu and Paperless Settings / eStatements enrollment there. If the member only sees the new UI, guide them to Documents & Statements instead of the old eBranch Services path.
""",
    "ART-57": """# How do I enroll in Mobile Deposit?

**Source:** https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/Mobile-Deposit/How-do-I-enroll-in-Mobile-Deposit

Enrollment in Mobile Deposit is based on eligibility. Contact Member Support at **800.222.7455** for eligibility questions.

Legacy eBranch enrollment path:
1. Log in to eBranch
2. Select eServices → Mobile Deposit Enrollment
3. Agree to Terms and Conditions and submit
4. Log off and back on if using a smartphone or tablet before depositing a check

In upgraded Digital Banking / the mobile app, Mobile Deposit is available after Digital Banking enrollment (snap a photo of the check with the rear-facing camera).
""",
    "ART-58": """# I do not see a Skip-A-Payment banner. How do I request to Skip my payment?

**Source:** https://www.cabrillocu.com/Resources-old/Member-Resources/FAQs/Loans/I-do-not-see-a-Skip-A-Payment-banner-How-do-I-requ

There may be several reasons the banner is not displayed on your account. For example:
- The loan due date might not be reflecting a December due date yet
- The checking/savings account balance may be overdrawn

Please call **800.222.7455** if you have further questions regarding skip qualifications.
""",
}


def api(method: str, path: str, body: Optional[dict] = None) -> Tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except Exception as e:
        if hasattr(e, "read"):
            return getattr(e, "code", 500), json.loads(e.read().decode())
        raise


def text_node(text: str) -> dict:
    return {"type": "text", "text": text}


def paragraph(text: str = "") -> dict:
    if not text:
        return {"type": "paragraph"}
    return {"type": "paragraph", "content": [text_node(text)]}


def heading(level: int, text: str) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [text_node(text)]}


def bullet_list(items: List[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [paragraph(i)]} for i in items if i.strip()],
    }


def markdown_to_rt(md: str) -> dict:
    import re

    blocks: List[dict] = []
    bullets: List[str] = []

    def flush():
        nonlocal bullets
        if bullets:
            blocks.append(bullet_list(bullets))
            bullets = []

    for line in md.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if not s:
            flush()
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush()
            blocks.append(heading(len(m.group(1)), m.group(2)))
            continue
        if re.match(r"^[-*]\s+", s):
            bullets.append(re.sub(r"^[-*]\s+", "", s))
            continue
        flush()
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        blocks.append(paragraph(s))
    flush()
    return {"type": "doc", "content": blocks or [paragraph("")]}


def upload_rt(rt: dict) -> str:
    h = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    body = {"file_name": "Article", "file_type": "devrev/rt", "configuration_set": "article_media"}
    prep = requests.post(f"{BASE}/artifacts.prepare", json=body, headers=h, timeout=45)
    if prep.status_code >= 400:
        body.pop("configuration_set", None)
        prep = requests.post(f"{BASE}/artifacts.prepare", json=body, headers=h, timeout=45)
    prep.raise_for_status()
    data = prep.json()
    form = {i["key"]: i["value"] for i in data.get("form_data", [])}
    payload = json.dumps(rt, ensure_ascii=False).encode()
    up = requests.post(data["url"], data=form, files={"file": ("Article", payload, "devrev/rt")}, timeout=90)
    if up.status_code not in (200, 201, 204):
        raise RuntimeError(up.text[:400])
    return data["id"]


def main() -> None:
    for did, md in BODIES.items():
        code, art_wrap = api("GET", f"/articles.get?id={did}")
        art = art_wrap["article"]
        print(f"{did} {art.get('title')[:50]} md={len(md)}")
        rt = markdown_to_rt(md)
        aid = upload_rt(rt)
        # short description = first non-heading paragraph
        desc = next((ln.strip() for ln in md.splitlines() if ln.strip() and not ln.startswith("#") and not ln.startswith("**Source")), md[:200])
        code, data = api("POST", "/articles.update", {"id": art["id"], "content_artifact": aid, "description": desc[:1900]})
        if code >= 400:
            code, data = api("POST", "/articles.update", {"id": art["id"], "resource": {"content_artifact": aid}, "description": desc[:1900]})
        print(f"  -> {code} artifact={aid}")
        time.sleep(0.25)
    print("Done enriching skipped articles")


if __name__ == "__main__":
    # clear proxies for requests
    for k in list(os.environ):
        if "proxy" in k.lower():
            os.environ.pop(k, None)
    main()
