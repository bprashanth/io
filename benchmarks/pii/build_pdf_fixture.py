#!/usr/bin/env python3
"""Synthetic digital PDF: a quarterly training report with a trainee table and narrative."""
import random
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

out = sys.argv[1]
rng = random.Random(5)
first = ["Sunita", "Ramesh", "Kavita", "Imran", "Pooja", "Santosh", "Meena", "Arjun", "Fatima", "Dnyaneshwar",
         "Lata", "Vikram", "Rukhsana", "Prakash", "Sangita"]
last = ["Pawar", "Shaikh", "Kulkarni", "Jadhav", "Naidu", "Gaikwad", "Sayyed", "More", "Patil", "Bhosale"]
vill = ["Ambegaon", "Khed Shivapur", "Bhor", "Velhe", "Nasrapur", "Saswad", "Kanhe", "Talegaon"]
rows = [["Sr", "Trainee name", "Village", "Mobile", "Age", "Pre-test", "Post-test", "Attendance %"]]
for i in range(28):
    pre = rng.randint(20, 60)
    rows.append([i + 1, f"{rng.choice(first)} {rng.choice(last)}", rng.choice(vill),
                 f"9{rng.randint(100000000, 999999999)}", rng.randint(19, 52), pre,
                 min(100, pre + rng.randint(5, 35)), rng.choice([100, 92, 85, 77, 69])])
ss = getSampleStyleSheet()
doc = SimpleDocTemplate(out, pagesize=A4)
story = [
    Paragraph("Tailoring Skill Training - Quarter 1 2026 Report", ss["Title"]),
    Paragraph("Implemented by Saksham Mahila Sanstha, Pune district, under the livelihoods programme. "
              "Batch coordinator: Meena Gaikwad (mobile 9822011223). Venue: Gram Panchayat hall, Ambegaon.", ss["Normal"]),
    Spacer(1, 12),
    Paragraph("Table 1: Trainee outcomes", ss["Heading3"]),
    Table(rows, repeatRows=1, style=TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                                                 ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                                                 ("FONTSIZE", (0, 0), (-1, -1), 8)])),
    Spacer(1, 12),
    Paragraph("Observations", ss["Heading3"]),
    Paragraph("Of 28 trainees, 24 completed the batch. Sunita Pawar of Velhe (age 34) has started taking stitching "
              "orders and earned Rs 2,400 in March. Rukhsana Sayyed could not attend after week 6 due to illness; "
              "follow-up call to 9822077665 is pending. Two trainees from Kanhe requested an advanced batch.", ss["Normal"]),
    Spacer(1, 8),
    Paragraph("Source: batch register and pre/post assessment sheets, verified by the field team on 2026-04-03.", ss["Normal"]),
]
doc.build(story)
print("wrote", out)
