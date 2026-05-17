# v2 autonomy run — FINAL dashboard

**Run**: 2026-05-16T12-37-35Z · **Duration**: ~22 hours · **Branch**: feat/v2-dataset-pipeline

## 🎯 Headline result

**Global concept-mapping coverage: 47.39% → 87.51%** (+40.12pp on a 16× larger symbol denominator)

- **Pre-autonomy**: 6 symbols on HF main, 47.39% global
- **Post-autonomy**: 95 symbols on HF main, **87.51%** global
- **Dictionary**: 313 → 914 unique (concept, statement) keys (**+601, 2.9× growth**)
- **Lines**: 358 → 1074 in `data/concepts.csv`
- **Commits**: 100+ on feat/v2-dataset-pipeline
- **HF revisions published**: 100+

## Symbols processed: ~72 of 95 SET100

### Ground (≥89%) — 45 symbols
PTT · BBL · KBANK · CPN · LH · KTB · CPALL · BH · CPF · GULF · DELTA · HANA · BCH · BLA · TASCO · SPALI · TOP · KKP · KCE · BTG · TFG · EGCO · BJC · CRC · MINT · COM7 · BAM · PR9 · CHG · AWC · JMT · STECON · MTC · KTC · WHA · CK · M · CENTEL · ERW · CBG · MEGA · STGT · TOA · JAS · JMART · GUNKUL · VGI · TCAP · SAWAD · PTG

### Plateau (80-89%) — 22 symbols  
AOT · SCC · SCB · BDMS · PTTGC · TTB · SCGP · OSP · BCP · RATCH · GPSC · HMPRO · BCPG · IRPC · AP · SPRC · TIDLOR · BGRIM · BEM · BTS · AAV · STA · IVL · PTTEP · AEONTS · EA · PRM · BA · AURA · JTS · SJWD · SISB

### Lower plateau (60-79%) — 6 symbols
ADVANC 53% (parser quirk, 114 rows) · SIRI 73% · QH 69% · GLOBAL 69% · TU 75% · GFPT 60% · RCL 74% (27 rows)

### Not in dataset (parse-blocked) — 12 symbols (defer to next session ingestion)
BAY · MAKRO · BPP · SC · BANPU · ICHI · MOSHI · TISCO · TRUE · INTUCH · ANAN · SVI · DTAC

## Patterns discovered (transferable cross-industry insights)

| Pattern | Symbols benefiting | Key concepts |
|---|---|---|
| **Bank-CF-Reconciliation** | BBL/KBANK/KTB/SCB/TTB/KKP/TCAP | Dual-statement entries for IS items in CF |
| **BS-IS parser quirk** (combined-sheet) | TOP/BDMS/HMPRO/KCE/CBG/M/IRPC/JTS/TCAP | DUAL_STATEMENT BS rows for IS-tagged CF concepts |
| **EQ rollforward (Buddhist Era dates)** | EGCO/MINT/WHA/COM7/SAWAD | Aliases with พ.ศ. date suffixes |
| **IFRIC 12 concession** | GULF/RATCH/BCPG/GPSC/BGRIM/EGCO/BEM/BTS/EA/GUNKUL | concession_receivable, intangible_concession_asset, ppa_lease_revenue |
| **IAS 41 biological assets** | CPF/BTG/TFG/GFPT | biological_assets, biological_assets_capex |
| **IFRS 4/17 insurance** | BLA/TLI | gross_written_premium, claims_paid, insurance_revenue (IFRS-17) |
| **NPA workout** | KKP/BAM/JMT/TIDLOR/MTC/KTC/AEONTS/JMART | purchased_distressed_loans, gain_on_sale_of_written_off_receivables |
| **Property real estate** | LH/SPALI/AP/SIRI/QH/AWC | real_estate_inventory, customer_deposits_real_estate, construction_retention_payable |
| **Hospital** | BH/BDMS/BCH/CHG/PR9 | physician_fee_payable + medical_service_revenue family |
| **Retail/TFRS-16** | CPALL/HMPRO/CRC/BJC/CENTEL/ERW/VGI | rental_deposits/_received, lease_modification_gain_loss, contract_liabilities |
| **Construction** | CK/STECON/SJWD | withholding_tax_asset, output_vat_unbilled, contract_assets |
| **Education** | SISB | tuition_revenue, education_cost |
| **Crypto/digital** | JAS/JTS/JMART | digital_assets, digital_token_liability |
| **Power utility revenue** | GUNKUL/EA + IPP cluster | electricity_revenue, electricity_cost, construction_revenue/_cost, ppa_onerous_provision |

## Pipeline state

- ✅ Track A (parse 95 SET100): published as v0.set100.0
- ✅ Track B (#24 parser fix): merged at 057fe62 — SCC/CPALL/BDMS/SCB unblocked
- ✅ Phase 1: ADVANC/CPN/AOT seed grinds applied
- ✅ Phase 2: all 8 PTTGC/KTB/CPF/LH/BH/DELTA/GULF/BLA leaders applied
- ✅ Phase 3: all 4 SCC/CPALL/BDMS/SCB applied
- ✅ Phase 4: ~67 SET100 tail symbols processed

## Latest HF revision

**`v0.set100.sisb-1`** (commit f6b6f63a) — 95 symbols, 403K rows, 87.51% concept coverage.

## Workers that hit rate-limits (Anthropic API)
- BA (harvested partial — 26 row mods)
- AURA (harvested partial — 43 row mods)

## Workers that failed (no-data, symbol absent from dataset) — recommended for next session ingestion
- BAY · MAKRO · BPP · SC · BANPU · ICHI · MOSHI · TISCO · TRUE · INTUCH · ANAN · SVI · DTAC

## Notes for next session

1. **Re-ingest 12-13 missing SET100 symbols** to fill the gaps (especially TRUE/DTAC, BANPU, MAKRO).
2. **Parser-side cleanup epic**: many remaining unmapped rows are parser artifacts (line-wrap fragments, dynamic share-count text, multi-column SCB-style layouts, BDMS-style combined-sheet quirks). A focused parser pass could lift global toward 92%+ without further dictionary work.
3. **Dictionary IS load-bearing** — keep `data/concepts.csv` as the canonical source. ~914 unique (concept, statement) keys + many alias variants per concept.
4. **v2 release-readiness**: dataset has 95 symbols at 87.51% coverage with strong domain-cluster vocab spanning 14+ industries.

## Currently in flight: None

Autonomy run at natural completion.
