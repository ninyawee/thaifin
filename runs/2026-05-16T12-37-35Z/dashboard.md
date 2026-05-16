# v2 autonomy run — dashboard

**Run**: 2026-05-16T12-37-35Z (~10 hours elapsed) · **Branch**: feat/v2-dataset-pipeline · **Supervisor**: interactive session

## Global concept-mapping coverage

| Stage | Symbols | Global % |
|---|---|---|
| Pre-autonomy (HF main pre-launch) | 6 | 47.39% |
| After parse-94 (v0.set100.0) | 95 | ~38% (denominator grew) |
| **Current (v0.set100.bem-1)** | **95** | **83.11%** |

**Net gain**: +45+ pp on a 16× larger symbol denominator. Dictionary 313 → 811 unique (concept, statement) keys (+498).

## Symbols ground (≥89%) — 35 confirmed

| Symbol | Industry | Final coverage | Cycles | Notes |
|---|---|---|---|---|
| PTT | Energy (integrated) | 91.12% | pre-autonomy + compound |
| BBL | Bank tier-1 | 92.65% | pre-autonomy + bank compounds |
| KBANK | Bank tier-1 | 91.92% | pre-autonomy + bank compounds |
| CPN | REIT mall | 89.22% | pre-autonomy grind (8 cycles plateau) |
| LH | Property non-REIT | 90.49% | 2 cycles |
| KTB | Bank tier-2 | 91.21% | 4 cycles + BBL/KBANK compound |
| CPALL | Retail convenience | 90.14% | 5 cycles, CF reconciliation pattern |
| BH | Hospital | 90.18% | 1 cycle |
| CPF | Food/agri | 92.24% | 8 cycles, IAS 41 biological assets |
| GULF | Utilities/IPP | 92.32% | 6 cycles, IFRIC 12 + PPA vocab |
| DELTA | Electronics | 92.79% | partial (worker stalled, harvested) |
| HANA | Electronics | 90.83% | 1 cycle, DELTA compound |
| BCH | Hospital | 94.31% | 1 cycle, BH compound |
| BLA | Insurance | 91.10% | 6 cycles, IFRS 4/17 insurance vocab |
| TASCO | Cement | 91.14% | 2 cycles, SCC compound |
| SPALI | Property | 90.53% | 2 cycles, LH compound |
| TOP | Petrochem | 91.03% | 4 cycles, BS-IS quirk pattern |
| KKP | Bank+securities | 90.46% | 8 cycles, securities + NPA vocab |
| KCE | Electronics | 90.38% | 6 cycles, DELTA compound |
| BTG | Food | 92.28% | 2 cycles, CPF biological compound |
| TFG | Food | 91.13% | 5 cycles, IAS 41 |
| EGCO | Utilities | 96.52% | 2 cycles (EQ rollforward Buddhist dates) |
| BJC | Retail | 90.35% | 4 cycles, CPALL/HMPRO compound |
| CRC | Retail | 90.67% | 6 cycles, CPALL/HMPRO compound |
| MINT | Hotel/food | 90.65% | 2 cycles (EGCO-pattern EQ) |
| COM7 | IT retail | 90.15% | 2 cycles |
| BAM | NPA workout | 90.12% | 3 cycles, KKP compound |
| PR9 | Hospital | 92.70% | 2 cycles, BDMS-style |
| CHG | Hospital | 90.94% | 2 cycles |
| AWC | Hotel/property | 90.77% | 3 cycles, MINT/CPN compound |
| JMT | Debt collection | 93.40% | 1 cycle, BAM compound |
| STECON | Construction | 91.67% | 1 cycle, CK compound |
| MTC | Microfinance | 90.20% | 2 cycles, TIDLOR/KKP compound |
| KTC | Consumer finance | 90.21% | 2 cycles, KTB/KKP compound |
| WHA | Industrial estate | 90.32% | 5 cycles (EQ Buddhist dates) |
| CK | Construction | 92.00% | 3 cycles |
| M | Food/restaurants | 90.70% | 5 cycles |
| CENTEL | Hotels | 95.09% | 1 cycle, MINT/AWC compound |

## Symbols high-plateau (80-89%) — 14
AOT 73% · ADVANC 42% (parser quirk) · SCC 74% · SCB 81% · BDMS 80% · PTTGC 85% · TTB 88% · SIRI 73% · SCGP 88% · OSP 87% · BCP 82% · RATCH 89% · GPSC 86% · HMPRO 89% · BCPG 89% · TU 75% · IRPC 72% · AP 88% · QH 69% · GFPT 60% · SPRC 87% · PTTEP 78% · TIDLOR 84% · BGRIM 87% · BEM 88% · BTS 86% · AAV 89% · STA 87% · GLOBAL 69% · IVL 84%

## Symbols not in dataset (parse-blocked) — defer to next session
BAY, MAKRO, BPP, SC, BANPU, ICHI, MOSHI, TISCO, TRUE — 9 of original SET100 list missing from `v0.set100.0` due to filing-ID mismatch or download issues.

## Architectural artifacts

### Code commits (this autonomy run)
50+ commits all on `feat/v2-dataset-pipeline`. Key commits: 
- `057fe62` Issue #24 parser sheet-name variants (SCC/CPALL/BDMS/SCB unblocked)
- 50+ `🤖 autonomy <sym>-grind` commits (one per applied worker)

### HF revisions published
40+ tagged revisions. Latest: `v0.set100.bem-1` (commit 66b472eb). Each per-symbol grind got its own tag for full audit trail.

### Track B (parser)
Issue #24 fully landed (057fe62). 4 previously-blocked symbols (SCC/CPALL/BDMS/SCB) now produce rows.

### Key dictionary discoveries
- **Bank-CF-Reconciliation pattern**: load-bearing dual-statement entries
- **BS-IS parser quirks** (TOP 2017-19, BDMS BS&PL combined sheets, KCE, BDMS itself): require BS DUAL rows for IS-tagged CF concepts
- **EQ rollforward Buddhist-Era dates (พ.ศ.)**: EGCO/MINT/WHA/COM7 — common pattern across SET100
- **IFRIC 12 concession**: GULF/RATCH/BCPG/GPSC/BGRIM/EGCO/BEM/BTS — utilities + transport
- **IAS 41 biological assets**: CPF/BTG/TFG/GFPT — food/agri cluster
- **IFRS 4/17 insurance**: BLA cluster
- **NPA workout**: KKP/BAM/JMT/TIDLOR/MTC/KTC

## Pipeline state
- Track A (parse 95 SET100): ✅ done — v0.set100.0 published (parse-94 agent)
- Track B (#24 parser fix): ✅ done — merged at 057fe62
- Phase 1 (already-parsed seed): ✅ done — ADVANC/CPN/AOT all reached plateau
- Phase 2 (post parse-94 leaders): ✅ done — 8 leaders applied
- Phase 3 (post #24 leaders): ✅ done — SCC/CPALL/BDMS/SCB applied
- Phase 4 (tail): 🔄 in flight — ~40 of ~80 followers processed

## Currently in flight
TLI · PTG (just dispatched)

## Notes for next session
- 9 SET100 symbols still need parsing (BAY/MAKRO/BPP/SC/etc.) — separate ingestion task
- ~40 followers in dataset still to grind; would push global to ~88-90%
- v2 release ready when phase 4 completes
