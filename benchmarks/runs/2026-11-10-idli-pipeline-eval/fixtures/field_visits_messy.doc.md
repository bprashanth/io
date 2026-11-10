# Field visits register — team handover
Visits contains one visit per row. Visit date is dd/mm/yyyy, valid and no later than the
fixed reporting cutoff of 31 March 2024. Village names are Kallar, Pudur, Mettu and Anaikatti.
Field officer must match a Name in Officers exactly. Households visited is a nonnegative
integer count; Amount disbursed (Rs) is a nonnegative numeric rupee amount. Status must be
exactly Done, Follow-up or Cancelled, including capitalization. A Cancelled visit must have
zero amount disbursed and zero households visited. Notes is optional free-text field context.
The final total sums counts and numeric disbursements, excluding unavailable values until
resolved; blank separator rows and the total are not visit records.

Officers contains one officer per Name: District is the synthetic service area, Phone is a
text string of exactly ten digits, and Email must have one @ with nonempty local and domain
parts and a dotted domain. All names, districts and contacts are fictional. The reserved
example.invalid domain is deliberate and is acceptable for this training workbook; do not
try to contact these people. This register is designed to teach reconciling recorded visits
with the staff directory and checking status-dependent disbursement rules.
