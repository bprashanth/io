# Ekibeki pattern extraction (fixture chat, @ mention restricted)

Question: @whatsapp_ekibeki this is a field WhatsApp group. Communication gets lost in here. Extract the recurring reporting patterns: what do people report, in what format, how often, and what would a weekly summary table look like? Use the codes as-is.

{"files_used": ["whatsapp_ekibeki"], "model": "google/gemini-3.7-flash"}

### 1. Recurring Reporting Patterns & Formats

Based on the message logs, group members report across five standardized operational categories:

| Report Type | Message Format Template | Key Data Captured | Frequency |
| :--- | :--- | :--- | :--- |
| **Cluster Production Updates** | `[Cluster] update: [X] artisans, [Y] toys done, [Z] pending orders` | Cluster name (e.g., `Molela`, `Channapatna`, `Bagru`, `Cheriyal`, `Etikoppaka`), Active artisans, Units produced, Pending orders | ~1–2 times per day |
| **Buyer Order Confirmations** | `order from [Location] buyer [Amount] rs confirmed` | Buyer location (`Hyderabad`, `Pune`, `Mumbai`, `Jaipur`, `Bengaluru`, `Delhi`), Order value (in INR) | ~2–4 times per day |
| **Payment Receipts** | `payment of [Amount] rs received for [Cluster] order, thanks` | Amount received (INR), Cluster/Order associated | ~1–2 times per day |
| **Exhibition / Event Schedules** | `exhibition dates confirmed: [Dates] at [Venue]` | Event dates, Venue/location name | Multiple updates per scheduling cycle |
| **Buyer Contact Sharing** | `buyer ne apna number diya hai, [PHONE] pe WhatsApp kar dena` | Contact phone number, Buyer lead flag | ~1–2 times per day |
| **Inventory & Logistics Status** | • `packing material khatam ho raha hai godown mein`<br>• `order ka fabric abhi tak nahi mila courier se`<br>• `sample approve ho gaya buyer se` | Stock arrival, Raw material receipt, Sample approval status | Frequent (multiple times daily) |

---

### 2. Operational Logistics & Administrative Routines
In addition to standard metrics, recurring administrative and coordination updates follow set templates:
- **Contact Sharing:** `[NAME] ka number save kar lo [PHONE]`
- **Meeting/Logistics Coordination:** `kal exhibition ke liye stall setup karna hai, 8 baje pahunch jana` / `meeting 4 baje rakhte hain kal`
- **Field Constraints:** `call me on [PHONE] after 6, network kharab hai yahan` / `weather kharab hai, delivery kal tak ho payegi shayad` / `traffic bahut hai, thoda late ho jaunga`

---

### 3. Proposed Weekly Summary Table Structure

To streamline reporting and prevent communication loss, messages should be aggregated into weekly operational summaries:

#### Table A: Production & Cluster Performance
| Date / Period | Cluster Name | Active Artisans | Total Toys Completed | Pending Orders |
| :--- | :--- | :--- | :--- | :--- |
| `01/05/26` | `Molela` | 18 | 58 | 0 |
| `02/05/26` | `Channapatna` | 8 | 17 | 0 |
| `02/05/26` | `Bagru` | 15 | 23 | 5 |
| `02/05/26` | `Molela` | 15 | 31 | 0 |
| `03/05/26` | `Channapatna` | 9 | 21 | 3 |
| `03/05/26` | `Cheriyal` | 10 | 42 | 2 |
| `04/05/26` | `Molela` | 10 | 33 | 5 |
| `05/05/26` | `Etikoppaka` | 15 | 35 | 6 |

#### Table B: Financial & Commercial Summary
| Date | Type (Order / Payment) | Source / Cluster | Amount (₹) | Status / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `01/05/26` | Order | `Hyderabad` | 8,000 | Confirmed |
| `01/05/26` | Order | `Mumbai` | 5,000 | Confirmed |
| `01/05/26` | Payment | `Bagru` | 9,000 | Received |
| `01/05/26` | Payment | `Channapatna` | 15,000 | Received |
| `02/05/26` | Order | `Pune` | 18000 | Confirmed |
| `02/05/26` | Payment | `Etikoppaka` | 6,000 | Received |
| `02/05/26` | Payment | `Molela` | 9,000 | Received |
| `02/05/26` | Order | `Pune` | 28000 | Confirmed |
| `03/05/26` | Payment | `Cheriyal` | 9,000 | Received |
| `03/05/26` | Order | `Pune` | 22,000 | Confirmed |
| ... | ... | ... | ... | ... |