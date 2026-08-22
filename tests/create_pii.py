import pandas as pd

data = {
    "Full_Tag": [
        "Rajesh Kumar Sharma",
        "Priya Venkatesh",
        "Amitav Sengupta",
        "Deepa Hariprasad",
        "Mohammed Farhan"
    ],
    "Alias": ["Raju", "PV", "Amit", "Deepu", "Farhan"],
    "Ref_ID": [
        "2342342",
        "32465346",
        "456746576",
        "[Aadhaar Redacted]",
        "[Aadhaar Redacted]"
    ],
    "Comm_Route": [
        "rajesh.sharma91@gmail.com",
        "priya.v@outlook.com",
        "sengupta.amitav@yahoo.co.in",
        "deepa.hari@rediffmail.com",
        "farhan.m@zohomail.in"
    ],
    "Loc_Pin": [
        "+91 98230 12345",
        "+91 87654 98710",
        "+91 94321 45678",
        "+91 70123 65432",
        "+91 91567 89012"
    ],
    "Tax_Code": [
        "ABCDE1234F",
        "BKLPV5678M",
        "CDEFA9012K",
        "ZXCVB3456N",
        "MNOPQ7890L"
    ]
}

df = pd.DataFrame(data)

# Export to Excel and CSV
df.to_excel("test_pii_data.xlsx", index=False)
df.to_csv("test_pii_data.csv", index=False)

print("Created test_pii_data.xlsx and test_pii_data.csv successfully.")
