

Ran the script — here are the results (56 of 260 pumps are not functional, 12 of 14 blocks affected):

| Block | Not Functional |
|---|---|
| Nabarangpur Sadar | 9 |
| Boipariguda | 8 |
| Koraput Sadar | 8 |
| Kashipur | 6 |
| Dabugaon | 5 |
| Bhawanipatna | 4 |
| Gunupur | 3 |
| Narla | 3 |
| Rayagada Sadar | 3 |
| Semiliguda | 3 |
| Junagarh | 2 |
| Umerkote | 2 |

**Notes**
- Script saved at `count_not_functional.py`; it uses the pump `Status` column (there's a second, duplicate `Status` column holding water-test results — the script picks the first one, which contains Functional/Not Functional).
- The remaining 2 blocks have zero not functional pumps.
- Column headers had stray spaces, so the script normalizes them before grouping.