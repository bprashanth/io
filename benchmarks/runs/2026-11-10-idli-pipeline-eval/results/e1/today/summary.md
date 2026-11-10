# E1 fake-copy fidelity

V2: False. Source: installed filekit.

Kinds count once per file. Survival requires a real detector hit; ambiguous heuristics and missed detectors are detailed in JSON.

| File | Kinds surviving / present | Detector missed |
|---|---:|---:|
| tree_plots_transects | 12 / 17 | 0 |
| germination_protocol_filled | 5 / 12 | 0 |
| household_survey_messy | 11 / 11 | 0 |
| field_visits_messy | 7 / 9 | 0 |
| tax_missing_info_fake | 8 / 13 | 0 |
| **Total** | **43 / 62** | **0** |

## tree_plots_transects

| Kind | Real | Fake survives |
|---|---|---|
| bad_date | yes | yes |
| casing | yes | yes |
| code_not_in_key | yes | yes |
| code_typo | yes | yes |
| count_mismatch | yes | no |
| dbh2_without_dbh1 | yes | yes |
| duplicate_id | yes | yes |
| key_missing_species | yes | yes |
| mixed_date_format | yes | yes |
| na_text | yes | no |
| notes_row | yes | no |
| out_of_range | yes | yes |
| repeated_header | yes | yes |
| spacer | yes | no |
| subheading | yes | yes |
| team_code | yes | yes |
| unit_in_cell | yes | no |

Template rows kept verbatim: 0 / 0.

## germination_protocol_filled

| Kind | Real | Fake survives |
|---|---|---|
| bad_email | yes | no |
| bad_phone | yes | no |
| casing | yes | yes |
| duplicate_id | yes | yes |
| info_block | yes | no |
| merged_header | yes | no |
| na_text | yes | no |
| not_a_number | yes | yes |
| notes_row | yes | no |
| out_of_range | yes | yes |
| required_missing | yes | yes |
| unit_in_cell | yes | no |

Template rows kept verbatim: 0 / 2.

## household_survey_messy

| Kind | Real | Fake survives |
|---|---|---|
| bad_phone | yes | yes |
| casing | yes | yes |
| code_not_in_key | yes | yes |
| code_typo | yes | yes |
| count_mismatch | yes | yes |
| duplicate_id | yes | yes |
| future_date | yes | yes |
| mixed_date_format | yes | yes |
| na_text | yes | yes |
| out_of_range | yes | yes |
| unit_in_cell | yes | yes |

Template rows kept verbatim: 0 / 0.

## field_visits_messy

| Kind | Real | Fake survives |
|---|---|---|
| bad_email | yes | yes |
| bad_phone | yes | yes |
| casing | yes | yes |
| code_typo | yes | yes |
| future_date | yes | yes |
| spacer | yes | no |
| total | yes | yes |
| total_mismatch | yes | no |
| unit_in_cell | yes | yes |

Template rows kept verbatim: 0 / 0.

## tax_missing_info_fake

| Kind | Real | Fake survives |
|---|---|---|
| code_typo | yes | yes |
| count_mismatch | yes | yes |
| end_before_start | yes | yes |
| info_block | yes | no |
| merged_header | yes | no |
| mixed_date_format | yes | no |
| na_text | yes | no |
| not_a_number | yes | yes |
| notes_row | yes | no |
| out_of_range | yes | yes |
| total | yes | yes |
| total_mismatch | yes | yes |
| unit_in_cell | yes | yes |

Template rows kept verbatim: 0 / 0.
