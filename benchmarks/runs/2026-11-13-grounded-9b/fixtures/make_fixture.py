"""Synthetic households sheet with the real ward names and the taught v2 layout. Fake values only. Deterministic.
Unequal ward sizes, a few blanks (unknown income/score), two outlier debts in Yerawada, one 0-income household."""
import random, sys
import openpyxl
random.seed(7)
WARDS = {"Yerawada Ward": 9, "Kasewadi": 14, "Janata Vasahat": 6, "Ramtekdi": 11, "Hadapsar Ward": 4}
PROFILE = {  # mean monthly income, mean debt, mean savings, mean score
    "Yerawada Ward": (11000, 60000, 9000, 6.8), "Kasewadi": (17000, 30000, 22000, 4.6),
    "Janata Vasahat": (14000, 42000, 15000, 5.4), "Ramtekdi": (15500, 38000, 18000, 5.1),
    "Hadapsar Ward": (21000, 25000, 30000, 3.9)}
FIRST = ["Asha", "Ravi", "Sunita", "Mahesh", "Lata", "Ganesh", "Meena", "Sanjay", "Kavita", "Anil", "Rekha", "Vijay"]
LAST = ["Pawar", "Jadhav", "Shinde", "More", "Gaikwad", "Kamble", "Salve", "Patil"]
H = ["household_head", "ward", "members", "monthly_income_inr", "savings_inr", "debts_inr",
     "vulnerability_score_1to10", "lat", "lon"]
rows = []
for w, n in WARDS.items():
    inc, debt, sav, score = PROFILE[w]
    for i in range(n):
        r = {"household_head": f"{random.choice(FIRST)} {random.choice(LAST)}", "ward": w,
             "members": random.randint(2, 8),
             "monthly_income_inr": int(random.gauss(inc, inc * 0.25) // 100 * 100),
             "savings_inr": max(0, int(random.gauss(sav, sav * 0.4) // 500 * 500)),
             "debts_inr": max(0, int(random.gauss(debt, debt * 0.3) // 1000 * 1000)),
             "vulnerability_score_1to10": max(1, min(10, round(random.gauss(score, 1.4)))),
             "lat": round(18.5 + random.random() * 0.1, 4), "lon": round(73.85 + random.random() * 0.1, 4)}
        rows.append(r)
ye = [r for r in rows if r["ward"] == "Yerawada Ward"]
ye[0]["debts_inr"], ye[1]["debts_inr"] = 410000, 295000          # outliers
ye[2]["monthly_income_inr"] = None                                  # unknown income
rows[20]["vulnerability_score_1to10"] = None                        # unknown score (Kasewadi)
rows[30]["monthly_income_inr"] = 0                                  # zero income (Ramtekdi)
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "households.csv"
ws.append(H)
for r in rows:
    ws.append([r[h] for h in H])
wb.save(sys.argv[1])
print(len(rows), "rows")
