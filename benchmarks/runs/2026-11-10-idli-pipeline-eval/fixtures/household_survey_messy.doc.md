# Village household survey — team handover
These are invented livelihoods interviews. Households has one row per household, identified by
unique Household ID. Village is one of Kallar, Pudur, Mettu or Anaikatti; differences in case
and surrounding whitespace are accepted. Ward is a positive local ward number. Head of
household is a synthetic person label and Phone is exactly ten digits, stored as text.
Members is the household's positive integer size and must equal the number of Members records
for that Household ID. Monthly income, Debts and Savings are nonnegative numeric INR amounts;
Land is a nonnegative numeric acreage. Survey date uses dd/mm/yyyy and must be a valid date
no later than our fixed reporting cutoff, 31 March 2024.

Members has one person per row, with Household ID linking to an existing household, Name the
invented person label, Age in completed years (0–110), Sex F or M, and Works Y or N. Every
person belongs to exactly one household; each household needs at least one member. Household
counts and the person records should agree before analysing income per capita. Do not infer
real identities from these generated labels. Amounts and dates are entirely synthetic and
exist only to exercise the survey import and review workflow.
