#!/usr/bin/env python3
"""Deterministic synthetic NGO text/PII fixtures for T0 redaction benchmarking.

Seed 20260825. Re-running this script reproduces byte-identical output for
every fixture. Do not hand-edit files under text-fixtures/ -- edit this
generator instead and re-run it.

Usage: .venv-v2/bin/python benchmarks/t0/build_text_fixtures.py
"""
import csv
import datetime
import json
import os
import random

import pandas as pd

SEED = 20260825
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "text-fixtures")
MIXED = os.path.join(OUT, "mixed")
CLASSES = ["person", "phone", "email", "aadhaar", "pan", "account"]
GOLD = {}

# --------------------------------------------------------------- name pools
FIRST_M = ["Ramesh", "Suresh", "Arjun", "Imran", "Santosh", "Vikram", "Prakash",
           "Dnyaneshwar", "Sanjay", "Anil", "Rahul", "Faisal", "Manoj", "Ravi",
           "Ashok", "Deepak", "Manjunath", "Ateeq"]
FIRST_F = ["Sunita", "Kavita", "Pooja", "Meena", "Lata", "Rukhsana", "Sangita",
           "Anita", "Fatima", "Nirmala", "Priya", "Shabana", "Geeta", "Vidya",
           "Asha", "Roopa", "Lakshmi", "Deepa"]
LAST = ["Pawar", "Shaikh", "Kulkarni", "Jadhav", "Naidu", "Gaikwad", "Sayyed",
        "More", "Patil", "Bhosale", "Deshmukh", "Yadav", "Reddy", "Chauhan",
        "Iyer", "Rao", "Sharma", "Gowda", "Kumar"]
VILLAGES = ["Sarpanchwadi", "Dongargaon", "Khed Shivapur", "Nasrapur", "Kanhe",
            "Velhe", "Ambewadi", "Umbraj", "Kondhawale", "Belsar"]
TOWNS = ["Bhor", "Saswad", "Baramati", "Wai", "Phaltan", "Junnar", "Indapur"]
DOMAINS = ["ngomail.org", "sahayogtrust.in", "gmail.com", "rediffmail.com", "yahoo.co.in"]
CLUSTERS = ["Channapatna", "Kondapalli", "Etikoppaka", "Molela", "Bagru", "Cheriyal"]
BUYER_CITIES = ["Jaipur", "Delhi", "Mumbai", "Bengaluru", "Pune", "Hyderabad", "Kolkata"]
VENUES = ["Dastkar Nature Bazaar", "Crafts Council Expo Hall", "Chitra Santhe Grounds",
          "State Emporium Mela", "Kala Ghoda Arts Festival stall"]
WHATSAPP_CASUAL = [
    "good morning sabko",
    "kal exhibition ke liye stall setup karna hai, 8 baje pahunch jana",
    "haan bhai sab ready hai yahan se",
    "koi Bagru cluster se sample bhej sakta hai kya jaldi",
    "photo achi aayi hai, group mein daal raha hoon",
    "traffic bahut hai, thoda late ho jaunga",
    "order ka fabric abhi tak nahi mila courier se",
    "thank you sabko, aaj ka session accha raha",
    "location bhej raha hoon exhibition venue ka",
    "kisi ke paas extra packing box hai kya",
    "rate list update kar diya hai, dekh lena",
    "weather kharab hai, delivery kal tak ho payegi shayad",
    "sample approve ho gaya buyer se",
    "meeting 4 baje rakhte hain kal",
    "ok noted",
    "bahut badiya kaam hua is baar",
    "packing material khatam ho raha hai godown mein",
    "naya design bheja hai dekh lo",
]
HELPLINE_TEMPLATES = [
    "caller {name} from {town} said her ration card update is still pending, call back on {phone}",
    "caller {name} said the borewell near {town} has run dry, asked for the water tanker helpline",
    "{name} phoned about her daughter's scholarship form, gave contact {phone}, resident of {town}",
    "caller {name} from {town} wanted to know status of the widow pension application",
    "{name} called regarding the SHG loan repayment schedule, said reach him after 6pm on {phone}",
    "caller from {town}, {name}, reported the anganwadi has not opened this week",
    "{name} asked about the disability certificate camp date, resident of {town}",
    "caller {name} said the LPG subsidy did not credit this month, number {phone}",
    "{name} from {town} complained the tailoring batch instructor has not come for two weeks",
    "caller {name} wanted the address of the district legal aid office, said call {phone} to confirm",
]
COMPLAINT_TEMPLATES = [
    "fever and body ache for {d} days, seen earlier by Dr. {name}",
    "cough and cold, referred to {name} for home follow-up",
    "stomach pain, mother {name} says it worsens after meals",
    "skin rash on arms, prescribed by Dr. {name}, review in a week",
    "high BP, husband {name} to bring old prescription next visit",
    "routine antenatal check, accompanied by {name}",
]

# ------------------------------------------------------------------ helpers
def digits(rng, n):
    return "".join(rng.choice("0123456789") for _ in range(n))

def full_name(rng, sex=None):
    sex = sex or rng.choice(["M", "F"])
    first = rng.choice(FIRST_M if sex == "M" else FIRST_F)
    return f"{first} {rng.choice(LAST)}"

def phone10(rng):
    return rng.choice("6789") + digits(rng, 9)

def phone_plus91(rng):
    n = phone10(rng); return f"+91 {n[:5]} {n[5:]}"

def aadhaar(rng):
    n = rng.choice("23456789") + digits(rng, 11); return f"{n[0:4]} {n[4:8]} {n[8:12]}"

def pan(rng):
    letters3 = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(3))
    last = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{letters3}P{last}{rng.randint(1000, 9999)}{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"

def account_no(rng, n=None):
    return digits(rng, n or rng.choice([11, 12, 14]))

def ifsc_code(rng, bank):
    return f"{bank}0{digits(rng, 6)}"

def email_for(name, domain, rng, tag=""):
    slug = name.lower().replace(" ", ".").replace("'", "")
    suffix = str(rng.randint(1, 99)) if rng.random() < 0.35 else ""
    return f"{slug}{tag}{suffix}@{domain}"

def pincode(rng):
    return str(rng.randint(400001, 442605))

def write_text(relpath, text):
    path = os.path.join(OUT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def record_gold(relpath, count_text, plants, extra=None):
    entry, total = {}, 0
    for c in list(CLASSES) + (extra or []):
        counts = {}
        for v in dict.fromkeys(plants.get(c, [])):
            n = count_text.count(v)
            if n:
                counts[v] = n
                total += n
        if counts:
            entry[c] = counts
    entry["_total_mentions"] = total
    GOLD[relpath] = entry

def _advance(rng, date, time, lo=1, hi=45):
    total_min = time.hour * 60 + time.minute + rng.randint(lo, hi)
    add_days, rem = divmod(total_min, 24 * 60)
    return date + datetime.timedelta(days=add_days), datetime.time(rem // 60, rem % 60)

def _structured_report(rng):
    kind = rng.choice(["cluster", "order", "exhibition", "payment"])
    if kind == "cluster":
        c = rng.choice(CLUSTERS)
        return (f"{c} update: {rng.randint(6, 20)} artisans, {rng.randint(15, 60)} toys done, "
                f"{rng.randint(0, 6)} pending orders")
    if kind == "order":
        return f"order from {rng.choice(BUYER_CITIES)} buyer {rng.choice([5000,8000,10000,12000,15000,18000,22000,28000])} rs confirmed"
    if kind == "exhibition":
        d1 = rng.randint(10, 20)
        return f"exhibition dates confirmed: {d1}-{d1 + rng.randint(2, 4)} Sept at {rng.choice(VENUES)}"
    return f"payment of {rng.choice([3000,6000,9000,12000,15000])} rs received for {rng.choice(CLUSTERS)} order, thanks"

# ------------------------------------------------------------- file builders
def build_blog(rng):
    narrator, shg_leader, sarpanch = full_name(rng, "M"), full_name(rng, "F"), full_name(rng, "M")
    asha, driver, colleague = full_name(rng, "F"), full_name(rng, "M"), full_name(rng, "F")
    trainee, block_coord = full_name(rng, "F"), full_name(rng, "M")
    v1, v2 = rng.sample(VILLAGES, 2)
    ph_block, ph_driver, ph_office = phone_plus91(rng), phone10(rng), phone_plus91(rng)
    em_colleague = email_for(colleague, "sahayogtrust.in", rng)
    em_accounts = "accounts@sahayogtrust.in"
    trainee_aadhaar = aadhaar(rng)
    acct, ifsc = account_no(rng, 14), ifsc_code(rng, "HDFC")

    text = f"""Field Notes: A Week Between {v1} and {v2}

I'm {narrator}, field coordinator with Sahayog Trust, and this week took me from {v1} to {v2} for the quarterly livelihoods review. The state transport bus from Bhor was running more than an hour late, so I reached {v1} only a little after eleven, by when {shg_leader} had already gathered six other members of the self-help group under the neem tree outside the panchayat office. She was visibly annoyed about the delay but softened once I explained the bus had broken down near Nasrapur and every passenger had to wait for a replacement. {v1} has had a good quarter -- the group's tailoring unit delivered forty school uniforms to the zilla parishad school last month and is now in talks for a second order from a nearby junior college. {shg_leader} wants the Trust to co-sign a small loan so the group can buy a second-hand overlock machine, and I promised to take the request to the finance committee next week. Before I left {v1}, she also asked me to note down that the bank has still not updated her passbook after the last disbursement, which is a separate problem for the accounts team to chase.

From {v1} I walked over to the anganwadi, where {asha}, the ASHA worker covering both {v1} and the hamlets around it, was midway through an immunization drive. She had eleven children on her list for the day and only nine mothers had turned up, so she was calling the missing families one by one from a battered phone book. {asha} mentioned that two of the mothers had shifted temporarily to {v2} for the sugarcane harvest and would need a follow-up visit there instead. She also flagged that the cold chain box lost power for an hour on Tuesday and she was not sure whether the vaccines already loaded were still usable; I told her to escalate that to the block medical officer directly rather than wait for our next visit.

The road on to {v2} is not motorable in the monsoon, so {driver}, who has been driving for the Trust for six years now, took the longer route around the ridge. On the way he complained, not for the first time, that the field vehicle's insurance renewal is overdue and that nobody at the head office has confirmed the payment. Once in {v2}, the sarpanch, {sarpanch}, was waiting with the water committee to discuss the borewell that failed again in April. {v2} has three functioning handpumps for close to four hundred households, and {sarpanch} wants the Trust to fund a fourth, ideally before the next election cycle rather than after it, which he said plainly and without embarrassment. I told him honestly that this falls outside our current grant and that I would only be able to raise it as a proposal, not a promise.

Also in {v2} was {trainee}, one of the newer entrants to the tailoring batch, whose disability certificate application has been stuck at the taluka office for three months. The enrolment form the block office finally sent back listed her Aadhaar as {trainee_aadhaar}, which I have copied into the case file so we can quote it if the office asks again why the earlier submission was rejected. {trainee} is otherwise doing well in the batch and finished her first blouse piece unassisted this week, which the trainer flagged as a small but real milestone.

Back at the guesthouse in the evening I finally managed to reach {colleague}, who handles community mobilization for the northern cluster and had been trying to loop me in on a joint visit to {v1} next month. We agreed to align our calendars over email rather than phone, since the signal near {v2} keeps dropping; her address is {em_colleague} if anyone else needs to reach her before then, though the district office switchboard on {ph_office} usually knows her whereabouts too. She also reminded me that the block coordinator, {block_coord}, wanted an update on the vehicle insurance issue {driver} had raised, so I called him directly at {ph_block} and left the same complaint with him that I had heard on the road that morning.

On a more irritating note, my own travel reimbursement of Rs 2,340 for last month is still stuck, apparently because the accounts team entered my account number, {acct}, IFSC {ifsc}, incorrectly against an older passbook page. I have written to {em_accounts} twice now with a photograph of the correct cheque leaf attached and have not had a reply either time. {driver}'s own mobile, {ph_driver}, is on the same claim if anyone from finance wants to cross-check the odometer photographs he sent for the {v1}-{v2} route.

Two more villages are on the list before month end, but for now this covers {v1} and {v2}. I will circulate a shorter summary to the programme group by Friday, with the loan request from {shg_leader}, the cold chain flag from {asha}, and the water committee ask from {sarpanch} as the three items that need a decision, not just an acknowledgement, from the head office.
"""
    plants = {
        "person": [narrator, shg_leader, sarpanch, asha, driver, colleague, trainee, block_coord],
        "phone": [ph_block, ph_driver, ph_office],
        "email": [em_colleague, em_accounts],
        "aadhaar": [trainee_aadhaar],
        "account": [acct],
        "ifsc": [ifsc],
    }
    return text, plants

def build_annual_report(rng):
    beneficiaries = [(full_name(rng, rng.choice(["M", "F"])), rng.randint(19, 52)) for _ in range(6)]
    ed, finance_officer, donor = full_name(rng, "F"), full_name(rng, "M"), full_name(rng, "M")
    donor_pan = pan(rng)
    ed_email = email_for(ed, "sahayogtrust.in", rng)
    fo_email = email_for(finance_officer, "sahayogtrust.in", rng, tag=".accounts")
    addr = f"14/2 Shaniwar Peth, Bhor, Pune District, Maharashtra - {pincode(rng)}"
    ben_line = "; ".join(f"{n} (age {a})" for n, a in beneficiaries)

    text = f"""Annual Report Extract 2025-26
Sahayog Trust, Registered Office: {addr}

This extract is prepared for internal circulation and covers the livelihoods and health outreach components of the Trust's 2025-26 programme year. It should be read alongside the audited financial statements filed separately with the Charity Commissioner.

Livelihoods programme. The tailoring and craft-based livelihoods cohort completed its second full cycle this year across four villages in Bhor and Velhe talukas. Individual progress was tracked against a standard skill and income rubric, and outcomes for the current reporting cohort were as follows: {ben_line}. All six beneficiaries listed above have completed at least eighty percent of the scheduled training days, and four have already begun taking independent stitching orders from within their own villages, a marked improvement on last year's cohort where only one trainee had reached that stage by the same point in the cycle. The programme team attributes this partly to a buddy system pairing newer trainees with the previous year's graduates, and partly to a steadier supply of raw material after the Trust renegotiated terms with its cloth vendor in December.

Health outreach. The community health component continued its partnership with the block primary health centre, running fortnightly camps that together reached just over eleven hundred individuals this year, a fourteen percent increase over the previous cycle. Referral completion -- the share of camp attendees who actually followed through on a hospital or specialist referral -- improved from fifty-eight to sixty-nine percent, which the team credits to a dedicated follow-up call introduced two weeks after each camp.

Staffing note. The programme currently runs with four full-time field coordinators, two ASHA-linked community health fellows, and a pool of part-time trainers who rotate across the four villages depending on batch schedules. Two of the four coordinator positions turned over this year, and induction for the incoming staff took longer than planned because the refreshed field manual was only finalised in November.

Governance and finance note. The Trust is grateful to its institutional and individual donors for their continued support this year. Among the individual donors whose contribution crossed the threshold requiring separate acknowledgement under Section 80G is {donor}, whose PAN, {donor_pan}, is held on file for compliance and tax-receipt purposes and should not be circulated outside the finance team. The Trust's total receipts this year grew by roughly eleven percent over the previous cycle, driven largely by two new institutional grants rather than by individual giving, which held roughly flat.

For queries on this extract, on the underlying data, or on any request for a corrected or reissued 80G receipt, please write to the Executive Director, {ed}, at {ed_email}, or to the Finance Officer, {finance_officer}, at {fo_email}. Postal correspondence may continue to be addressed to the registered office at {addr}. The Trust's board met twice during the reporting year, in October and again in March, and minutes of both meetings are available to members on request.

Looking ahead to 2026-27, the programme team plans to add a fifth village to the livelihoods cohort, contingent on final confirmation from the block office, and to pilot a shorter twelve-week batch for women who cannot commit to the full sixteen-week cycle because of agricultural labour or childcare commitments. The health outreach team is separately exploring a tele-consultation partnership with a private hospital chain, which would let camp attendees complete specialist consultations without travelling to the district hospital, though this remains at an early and unfunded stage. {ed} will present both proposals to the board at its next meeting, alongside a revised three-year plan that the programme committee began drafting in February. Donors and partners with questions about either proposal are welcome to raise them directly with the Finance Officer, {finance_officer}, ahead of the meeting.

This extract does not include the disaggregated financial schedules, which are appended separately to the full annual report along with the auditor's certificate and the list of institutional donors and grant-making partners for the year.
"""
    plants = {
        "person": [n for n, _ in beneficiaries] + [ed, finance_officer, donor],
        "email": [ed_email, fo_email],
        "pan": [donor_pan],
    }
    return text, plants

def build_helpline(rng):
    lines, persons, phones = [], [], []
    date = datetime.date(2026, 7, 1)
    for _ in range(40):
        date += datetime.timedelta(days=rng.choice([0, 0, 1, 1, 2]))
        time = f"{rng.randint(9, 18):02d}:{rng.randint(0, 59):02d}"
        name, town = full_name(rng), rng.choice(TOWNS)
        tmpl = rng.choice(HELPLINE_TEMPLATES)
        needs_phone = "{phone}" in tmpl
        phone = phone10(rng) if needs_phone else None
        filled = tmpl.format(name=name, town=town, phone=phone or "")
        lines.append(f"{date.strftime('%d/%m/%Y')} {time} - {filled}")
        persons.append(name)
        if needs_phone:
            phones.append(phone)
    return "\n".join(lines) + "\n", {"person": persons, "phone": phones}

def build_whatsapp(rng):
    participants = [full_name(rng, rng.choice(["M", "F"])) for _ in range(11)]
    lines, persons, phones = [], [], []
    date, time = datetime.date(2026, 5, 1), datetime.time(9, 0)
    for _ in range(260):
        date, time = _advance(rng, date, time)
        sender = rng.choice(participants)
        roll = rng.random()
        if roll < 0.14:
            msg = _structured_report(rng)
        elif roll < 0.20:
            other, ph = rng.choice([p for p in participants if p != sender]), phone10(rng)
            msg = rng.choice([
                f"{other} ka number save kar lo {ph}",
                f"call me on {ph} after 6, network kharab hai yahan",
                f"buyer ne apna number diya hai, {ph} pe WhatsApp kar dena",
            ])
            persons.append(other)
            phones.append(ph)
        elif roll < 0.26:
            msg = "<Media omitted>"
        else:
            msg = rng.choice(WHATSAPP_CASUAL)
        lines.append(f"{date.strftime('%d/%m/%y')}, {time.strftime('%H:%M')} - {sender}: {msg}")
        persons.append(sender)
    return "\n".join(lines) + "\n", {"person": persons, "phone": phones}

def build_telegram(rng):
    participants = [full_name(rng, rng.choice(["M", "F"])) for _ in range(6)]
    lines, persons, phones = [], [], []
    date, time = datetime.date(2026, 6, 1), datetime.time(9, 0)
    for _ in range(80):
        date, time = _advance(rng, date, time)
        sender = rng.choice(participants)
        roll = rng.random()
        if roll < 0.18:
            msg = _structured_report(rng)
        elif roll < 0.26:
            other, ph = rng.choice([p for p in participants if p != sender]), phone10(rng)
            msg = f"{other} se confirm kiya, number {ph} hai"
            persons.append(other)
            phones.append(ph)
        elif roll < 0.32:
            msg = "<Media omitted>"
        else:
            msg = rng.choice(WHATSAPP_CASUAL)
        lines.append(f"[{date.strftime('%d.%m.%y')} {time.strftime('%H:%M')}] {sender}: {msg}")
        persons.append(sender)
    return "\n".join(lines) + "\n", {"person": persons, "phone": phones}

def build_pdf_letter(rng, path):
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    donors = [(full_name(rng, rng.choice(["M", "F"])),
               rng.choice([2500, 5000, 7500, 10000, 15000, 20000, 35000, 50000])) for _ in range(6)]
    contact_name = full_name(rng, "F")
    phone, email = phone_plus91(rng), email_for(contact_name, "sahayogtrust.in", rng)
    addr = f"14/2 Shaniwar Peth, Bhor, Pune District, Maharashtra - {pincode(rng)}"

    body = (
        "Dear Friend of Sahayog Trust,\n\n"
        "On behalf of everyone at Sahayog Trust, thank you for your generosity during "
        "our 2025-26 fundraising cycle. Your contribution, together with those listed "
        "below, made it possible for us to continue the livelihoods and health outreach "
        "work described in this year's annual report.\n\n"
        "We are pleased to formally acknowledge the following individual donors and "
        "their contributions received between April 2025 and March 2026:\n\n"
    )
    donor_lines = "\n".join(f"  - {n}: Rs {a:,}" for n, a in donors)
    closing = (
        f"\n\nAll receipts under Section 80G have been issued separately by post. If you "
        f"have not received yours, or if any of the details above need correction, "
        f"please write to {contact_name} at {email} or call {phone}. You may also write "
        f"to us at {addr}.\n\nWith gratitude,\nProgramme Team, Sahayog Trust"
    )
    full_body = body + donor_lines + closing

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Donor Thank-You Letter - 2025-26", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, full_body)
    pdf.output(path)

    plants = {"person": [contact_name] + [n for n, _ in donors], "phone": [phone], "email": [email]}
    return full_body, plants

def build_sports_day(rng):
    houses = ["Red House", "Blue House", "Green House", "Yellow House"]
    events = ["100m Sprint", "Long Jump", "Relay Race", "Shot Put", "High Jump", "Sack Race"]
    rows, persons, phones = [], [], []
    for i in range(1, 23):
        participant, guardian_phone = full_name(rng, rng.choice(["M", "F"])), phone10(rng)
        remarks = ""
        if rng.random() < 0.45:
            other, other_phone = full_name(rng, rng.choice(["M", "F"])), phone10(rng)
            remarks = rng.choice([
                f"Guardian could not attend, called {other} instead on {other_phone}",
                f"Minor scrape during event, informed {other} at {other_phone}",
                f"Substitute guardian contact: {other} ({other_phone})",
            ])
            persons.append(other)
            phones.append(other_phone)
        rows.append({"SlNo": i, "Participant": participant, "Guardian Mobile": guardian_phone,
                     "House": rng.choice(houses), "Event": rng.choice(events),
                     "Score": rng.randint(1, 100), "Remarks": remarks})
        persons.append(participant)
        phones.append(guardian_phone)
    df = pd.DataFrame(rows)
    path = os.path.join(MIXED, "sports_day.xlsx")
    os.makedirs(MIXED, exist_ok=True)
    df.to_excel(path, index=False, engine="openpyxl")
    return path, df.to_csv(index=False), {"person": persons, "phone": phones}

def build_clinic_visits(rng):
    rows, persons = [], []
    for _ in range(20):
        patient = full_name(rng, rng.choice(["M", "F"]))
        other = full_name(rng, rng.choice(["M", "F"]))
        complaint = rng.choice(COMPLAINT_TEMPLATES).format(d=rng.randint(2, 7), name=other)
        rows.append([patient, rng.randint(1, 80), rng.choice(["M", "F"]), complaint,
                     phone10(rng), rng.choice(VILLAGES), rng.choice([0, 20, 50, 100, 150])])
        persons.extend([patient, other])
    path = os.path.join(MIXED, "clinic_visits.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Patient", "Age", "Sex", "Complaint", "Phone", "Village", "Fee"])
        w.writerows(rows)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return text, {"person": persons, "phone": [r[4] for r in rows]}

def build_mixed_headers(rng):
    rows, aadhaars, emails, persons = [], [], [], []
    for _ in range(15):
        item_code, batch_email = aadhaar(rng), email_for(full_name(rng), rng.choice(DOMAINS), rng)
        note_person = full_name(rng, rng.choice(["M", "F"]))
        note = rng.choice([
            f"Checked by {note_person}, batch passed visual inspection",
            f"{note_person} flagged colour mismatch, held for rework",
            f"Approved by {note_person} after second pass",
            f"{note_person} noted minor stitching defect, sent back to Molela unit",
        ])
        rows.append([item_code, batch_email, note])
        aadhaars.append(item_code)
        emails.append(batch_email)
        persons.append(note_person)
    path = os.path.join(MIXED, "mixed_headers.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Item Code", "Batch", "QC Notes"])
        w.writerows(rows)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return text, {"person": persons, "email": emails, "aadhaar": aadhaars}

def main():
    rng = random.Random(SEED)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MIXED, exist_ok=True)

    text, plants = build_blog(rng)
    write_text("field_visit_blog.txt", text)
    record_gold("field_visit_blog.txt", text, plants, extra=["ifsc"])

    text, plants = build_annual_report(rng)
    write_text("annual_report_extract.txt", text)
    record_gold("annual_report_extract.txt", text, plants)

    text, plants = build_helpline(rng)
    write_text("helpline_log.txt", text)
    record_gold("helpline_log.txt", text, plants)

    text, plants = build_whatsapp(rng)
    write_text("whatsapp_ekibeki.txt", text)
    record_gold("whatsapp_ekibeki.txt", text, plants)

    text, plants = build_telegram(rng)
    write_text("telegram_export.txt", text)
    record_gold("telegram_export.txt", text, plants)

    pdf_path = os.path.join(OUT, "donor_thankyou.pdf")
    body, plants = build_pdf_letter(rng, pdf_path)
    record_gold("donor_thankyou.pdf", body, plants)

    _, gold_text, plants = build_sports_day(rng)
    record_gold("mixed/sports_day.xlsx", gold_text, plants)

    text, plants = build_clinic_visits(rng)
    record_gold("mixed/clinic_visits.csv", text, plants)

    text, plants = build_mixed_headers(rng)
    record_gold("mixed/mixed_headers.csv", text, plants)

    GOLD["_meta"] = {
        "seed": SEED,
        "methodology": ("Counts are exact substring occurrences of each planted value inside "
                         "the generator's own source text for that file. For donor_thankyou.pdf "
                         "this is the letter body text fed to the PDF renderer (not a re-extraction "
                         "of the rendered PDF). For mixed/sports_day.xlsx this is a CSV rendering "
                         "of the same DataFrame written to the sheet. Values are deduplicated "
                         "before counting, so one value planted twice in prose is still counted twice."),
        "classes": ("person, phone, email, aadhaar, pan, account are the required classes; ifsc is "
                    "an extra bonus class tracked only for field_visit_blog.txt's bank-account gripe."),
    }
    with open(os.path.join(OUT, "gold.json"), "w", encoding="utf-8") as f:
        json.dump(GOLD, f, indent=2, ensure_ascii=False, sort_keys=True)
    print("wrote", len(GOLD) - 1, "fixture entries under", OUT)

if __name__ == "__main__":
    main()
