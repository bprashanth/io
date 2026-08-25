

Done. The ledger reconciles perfectly when ordered by `txn_id` (each `balance_after` = opening + cumulative net), so closing stock is unambiguous.

**Answer**

| Device type | Stock remaining |
|---|---|
| **Calipers** | **60** |
| Walking stick | 168 |
| Wheelchair | 170 |
| Crutches | 181 |
| Tricycle | 225 |
| Hearing aid | 241 |
| Braille kit | 280 |

**Calipers** have the lowest stock remaining at 60 units. Note the rows in `device_inventory.csv` aren't in date order, so I replayed the IN/OUT transactions in `txn_id` order and verified the running total matches the `balance_after` column for all 260 transactions.