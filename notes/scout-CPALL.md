# Scout report — CPALL (CP All Public Company Limited)

**Industry**: Retail (7-Eleven Thailand operator; consolidated with Makro and Lotus's after 2021).
**SET symbol**: CPALL.
**IPO**: 2003 (first inspected filing dates Feb 2004 / FY2003).
**Total filings on SEC IDISC**: 91 unique zips (182 fs-norm rows; each filing has both `consolidated` + `company` rows).
**Period coverage**: FY2003 → 2026Q1 (current). All quarterly + annual filings present, no gaps observed.

**Scout author**: scout/CPALL agent.
**Scout commit**: see HEAD of `scout/CPALL` branch.
**Sample window**: 6 stratified zips downloaded (oldest → most recent quarterly).

## Sample filings inspected

| Period | Audit basis | FILEID (path under `dat/news/...`) | File shape | Key observation |
|---|---|---|---|---|
| FY2003 | audited | `200402/04004428.zip` | 3 × `.DOC` (no XLS!) | Pre-XLS era; financial statements distributed as Word tables. Filed under old company name "ซี.พี. เซเว่นอีเลฟเว่น". |
| FY2008 | audited | `200902/09007190.zip` | `cpallt1.doc` + `cpallt2.xls` + `cpallt3.doc` | Mixed filing — XLS for statements, DOC for auditor + notes. Compact prefix-style labels. |
| FY2015 | audited | `201602/16017244.zip` | Standard `FINANCIAL_STATEMENTS.XLS` + 2 `.DOC` | TFRS adoption restatement — BS includes a 3rd date column "1 มกราคม 2556". |
| FY2020 | audited | `202102/21018726.zip` | Standard XLS + 2 DOC | TFRS-16 first-time adoption — ROU asset and lease liability lines appear; comparative 2019 column shows 0 / legacy "สิทธิการเช่า". |
| FY2025 | audited | `202602/0737FIN250220261406350902T.zip` | OOXML (`.XLSX` + 2 `.DOCX`) | Modern format. New treasury-share line. |
| 2026Q1 | reviewed | `202605/0737FIN130520261329450345T.zip` | OOXML + extra `DS_INTERNAL_*` storage sheets | Quarterly format uses thousands of baht (not raw baht!), period vs year wording. |

## Sheet structure inventory

### CPALL **does not** match the PTT 8-sheet pattern. Key deviation: OCI is appended to the same sheet as the regular P&L, not a separate sheet.

| Period | Sheets | Statement mapping (sheet → statement type) |
|---|---|---|
| FY2008 | `BL`, `SH 7`, `SH 8`, `sh-9`, `CF` (5 total) | BL→BS, SH 7-9→EQ (3 separate equity-change sheets), CF→CF. Older 5-sheet legacy layout. NB: lowercase `sh-9`, mixed casing. |
| FY2015 | `BS 4-6`, `PL 7-8`, `SH 9-10`, `sh 11-12`, `CF 13-16` (5 total) | BS→BS, PL→IS+OCI combined, SH×2→EQ (consolidated + company), CF→CF. PL contains both regular PL and the OCI continuation in one sheet. NB: lowercase `sh 11-12`. |
| FY2020 | `BS 8-10`, `PL 11-12`, `SH13`, `SH 14`, `SH15`, `SH 16`, `CF 17-19` (7 total) | BS→BS, PL→IS+OCI, SH×4→EQ (4 separate equity-change views — consolidated, company, and possibly comparative-period restated). |
| FY2025 | `BS 7-9`, `PL 10-11`, `SH-12`, `SH-13`, `SH-14`, `SH-15`, `CF 16-19` (7 total) | Same 7-sheet structure as 2020. SH×4 unchanged. |
| 2026Q1 | `BS 3-5`, `PL3M-6-7`, `SH 8`, `SH 9`, `SH 10`, `CF-11-14` + 4 × `DS_INTERNAL_*` (10 total, 6 real) | Quarterly: only 3 EQ sheets (vs 4 in annual). PL sheet name encodes period — `PL3M` (3-month), other quarters likely `PL6M`/`PL9M` (NOT inspected — flag for follow-up). **The 4 `DS_INTERNAL_SETTINGS_STORAGE` / `_DOCGROUP_STORAGE` / `_DOCUMENT_STORAGE` / `_SNIP_STORAGE` sheets MUST be skipped by the parser** (filing-tool metadata, not financial data). |

### Sheet naming patterns to support (regex hints)

- BS / Balance Sheet: `^B[SL][\s-]*\d` (covers `BS`, `BL`, `BS 7-9`, `BS-3-5`).
- PL / Income Statement: `^PL` then optional period token `3M`/`6M`/`9M` then digit range.
- EQ / Equity changes: `^[Ss][Hh][\s-]*\d` (case-insensitive — observed `SH`, `sh`, `SH-12`, `sh-9`, `SH 14`).
- CF / Cash Flow: `^CF[\s-]*\d?` (sometimes plain `CF` for older filings).
- Skip: any sheet starting with `DS_INTERNAL_`.

### Header structure (column layout)

CPALL's annual XLS uses **4 numeric columns** with the canonical layout:

```
                 งบการเงินรวม                        งบการเงินเฉพาะกิจการ
                 (Consolidated)                      (Company)
                 [current FY]   [prior FY]           [current FY]   [prior FY]
```

**Exception**: FY2014 annual filing (and likely FY2013) include a **3rd date column** `1 มกราคม [year-1]` (the TFRS first-adoption opening-balance restatement). Layout becomes 6 numeric columns. Verified in FY2015 BS: `งบการเงินรวม (31 ธ.ค. 2558, 31 ธ.ค. 2557, 1 ม.ค. 2557)`. Parser must accept variable column count.

2026Q1 quarterly statements report values in **thousands of baht** `(พันบาท)` — not raw baht — while annual filings report raw baht `(บาท)`. The unit-of-currency cell appears in the row immediately under the column-headers row.

## Auditor inventory & opinion-language patterns

**One firm across all periods**: `บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด` (KPMG Phoomchai Audit Ltd.). Three different signing partners observed across the sample, no firm change.

| Period | Signing partner (Thai) | CPA reg. # | Sign date (BE) | Opinion language pattern |
|---|---|---|---|---|
| FY2003 | นางสุดจิตร์ บุญประกอบ | 2991 | 19 กุมภาพันธ์ 2547 | Pre-2016 short-form unqualified. Two paragraphs: scope + opinion. Phrase: "ข้าพเจ้าเห็นว่า งบการเงิน...แสดงฐานะการเงิน... โดยถูกต้องตามที่ควรในสาระสำคัญ". |
| FY2008 | นายเจริญ ผู้สัมฤทธิ์เลิศ | 4068 | 19 กุมภาพันธ์ 2552 | Same pre-2016 short form. Includes "Emphasis of matter" paragraph (note 32 — accounting policy change re: goodwill). |
| FY2015 | นายเจริญ ผู้สัมฤทธิ์เลิศ | 4068 | 29 กุมภาพันธ์ 2559 | Pre-KAM TSA-700 long-form (introduced before TSA-701 mandate). Sections: Auditor's Responsibility, Management's Responsibility, Opinion, Emphasis of Matter. EOM cites note 3 (new accounting policy). |
| FY2020 | (not extracted by scout) | — | — | TSA-701-style with **Key Audit Matters** ("เรื่องสำคัญในการตรวจสอบ"). Going-concern paragraph not flagged as separate EOM in the language sampled. |
| FY2025 | นายวีระชัย รัตนจรัสกุล | 4323 | (not extracted) | TSA-701 standard layout. No qualified/adverse markers. |
| 2026Q1 | นางมัญชุภา สิงห์สุขสวัสดิ์ | 6112 | 13 พฤษภาคม 2569 | TSAR 2410 review report. Conclusion phrase: "ข้าพเจ้าไม่พบสิ่งที่เป็นเหตุให้เชื่อว่าข้อมูลทางการเงินระหว่างกาลดังกล่าว ไม่ได้จัดทำขึ้นตามมาตรฐานการบัญชีฉบับที่ 34". |

### Opinion-classification heuristics (CPALL-specific)

All 6 inspected reports are **unqualified**. None contain `แสดงความเห็นแบบมีเงื่อนไข` (qualified), `แสดงความเห็นว่างบการเงิน...ไม่ถูกต้อง` (adverse), or `ไม่แสดงความเห็น` (disclaimer). The FY2015 EOM paragraph is benign (accounting-policy-change disclosure, not a going-concern flag).

For the parser:
- `unqualified` heuristic: presence of `เห็นว่า งบการเงิน...แสดง...โดยถูกต้องตามที่ควร` AND absence of qualifier markers.
- `going_concern_emphasis` heuristic: search for `การดำเนินงานต่อเนื่อง` AND (`มีนัยสำคัญ` OR `เน้น`) within an `ข้อมูลและเหตุการณ์ที่เน้น` (Emphasis of Matter) section. None of CPALL's 6 sampled reports trigger this.

## Concept inventory summary

See `data/concepts.CPALL.csv` for the full table. Counts:
- **Concepts confirmed (label_th matches canonical exactly)**: 8.
- **Concepts needing alias appends** (canonical exists but CPALL phrasing differs): 11.
- **New concepts proposed** (mostly retail-relevant + TFRS-16-related + reporting-completeness): 25.

### Top alias appends (by impact)

1. `revenue` — CPALL uses `รายได้จากการขายสินค้าและการให้บริการ` (adds "สินค้า"/goods); canonical is `รายได้จากการขายและการให้บริการ`. Without the alias, every CPALL revenue row would be unmapped.
2. `cogs` — CPALL: `ต้นทุนขายสินค้าและต้นทุนการให้บริการ` (parallel structure with "สินค้า" insert).
3. `selling_expenses` — CPALL: bare `ต้นทุนในการจัดจำหน่าย` (distribution cost only — no "selling" wording). Canonical exists already as one of two existing aliases; CPALL form is the SHORT alias, already covered. Confirmed.
4. `ocf` / `investing_activities` / `financing_activities` — CPALL prefixes with `กระแสเงินสด` (full "cash-flow" prefix); canonical uses bare `เงินสด`. Extending alias list.
5. `capex` — CPALL labels are SHORTER than PTT's combined PPE+investment-property line; CPALL splits these into two lines. Use the bare PPE line (`เงินสดจ่ายเพื่อซื้อที่ดิน อาคารและอุปกรณ์`) as the `capex` mapping.
6. `interest_paid` — CPALL labels this `ดอกเบี้ยจ่าย` (interest paid) and reports it under FINANCING activities (TFRS allowance), not OCF. Canonical mapping to `interest_paid` is still correct, but downstream queries that expect interest-paid to live in the OCF subtotal will need to know it's elsewhere.

### Top new concepts proposed (retail-specific)

The following are highly material for CPALL but absent from the v0.1 canonical dictionary:

- `right_of_use_asset` (TFRS-16; 102B THB) + `lease_liability_current` (12B) + `lease_liability_noncurrent` (104B) + `lease_payments` (-17.3B/yr in CF financing).
- `goodwill` (363B THB — single largest asset, from Lotus's & Makro acquisitions).
- `non_controlling_interest` (193B THB equity, 3.7B/yr profit share).
- `inventory` (74B THB BS), `trade_payables` (134B THB), `trade_receivables` (5.2B).
- `investment_property` (60B THB — Lotus's malls).
- `debentures` (245B), `proceeds_from_debentures` / `repayment_of_debentures`.
- `acquisition_of_subsidiaries` (-6.9B FY2025; recurring M&A).
- IS attribution split: `profit_attributable_to_parent` vs `profit_attributable_to_nci` (group materiality from Lotus/Makro).

## Anomaly log

### A1 — KPMG, not EY (brief was wrong for this symbol)
The scout brief hinted "Likely auditor: EY". CPALL is a **KPMG** client across the ENTIRE inspected window (FY2003 → 2026Q1). No auditor change observed. The EY-rename watch (Ernst & Young Office Limited → EY Office Limited) is not testable from CPALL's filings — recommend verifying that hypothesis from a known EY-audited symbol (PTT, SCC are typical EY clients).

### A2 — 2003 filing has no XLS at all
The pre-2009 filings (at least FY2003) are distributed as 3 `.DOC` files (`*t1.doc` = auditor report; `*t2.doc` = financial statements as Word tables; `*t3.doc` = notes), not the canonical `XLS + 2 DOC` triplet. The downstream `FinancialStatementParser` (slice #15) currently assumes XLSX input. **Either**: (a) extend the parser to extract Word tables when no XLS is found, or (b) document the lost coverage for the pre-XLS era. The fs-norm `contents.txt` file in older zips documents the file-naming scheme (XXXXXXTN.DOC where N=1/2/3).

### A3 — Company-name change embedded in old filings
The FY2003 auditor report names the company `บริษัท ซี.พี. เซเว่นอีเลฟเว่น จำกัด (มหาชน)` (CP 7-Eleven). The current name `บริษัท ซีพี ออลล์ จำกัด (มหาชน)` (CP All) appears from FY2008 onward (rebrand effective 2007). Symbol `CPALL` is unchanged throughout.

### A4 — TFRS-16 lease adoption (1-Jan-2020)
CPALL transitioned from operating-lease expense + finance-lease BS line (`สิทธิการเช่า` / `หนี้สินตามสัญญาเช่าการเงิน`) to the new ROU model (`สินทรัพย์สิทธิการใช้` / `หนี้สินตามสัญญาเช่า`) on 1-Jan-2020. The 2020 BS is hugely affected:
- ROU asset 0 → 53B THB
- Lease liability (current + non-current) 0.7B → 50B THB
- Total assets +147B THB year-over-year (mostly TFRS-16 plus the Tesco/Lotus's acquisition consummated the same year).

The 2020 BS also embeds explanatory text in the line label itself, e.g. `ส่วนของหนี้สินตามสัญญาเช่าที่ถึงกำหนดชำระภายในหนึ่งปี (2562: หนี้สินตามสัญญาเช่าการเงินที่ถึงกำหนดชำระภายในหนึ่งปี)` — the row header explicitly notes that the 2019 comparative number is the legacy finance-lease line. The parser must either treat parenthetical-clarification text as part of the label or strip it; either choice impacts alias matching.

### A5 — Quarterly filings use thousands of baht
2026Q1 reports values in `(พันบาท)`, not raw baht. The header row immediately under the date row carries the unit-of-measure marker. **The parser MUST detect this marker and scale values by 1000** before storing in `financial_lines.value` (which the schema spec defines as raw THB). Without scaling, CPALL Q1 figures will be off by 3 orders of magnitude.

### A6 — Multi-line labels
Several CPALL line-item labels are split across 2-4 cells in the source XLS (typographic line breaks for printing layout). Examples:
- `ทุนที่ออกและชำระแล้ว (หุ้นสามัญจำนวน 8,983 ล้านหุ้น มูลค่า 1 บาทต่อหุ้น)` — split across 3 rows, label on row N, parenthetical on N+1, N+2.
- `ส่วนของหนี้สินตามสัญญาเช่าที่ถึงกำหนดชำระภายในหนึ่งปี (2562: หนี้สินตามสัญญาเช่าการเงินที่ถึงกำหนดชำระภายในหนึ่งปี)` — 3 rows.
- Several CF lines start indented with `   ` (3 spaces) as continuation rows — semantically part of the previous line.

The parser likely needs a "stitch consecutive empty-numeric-column rows into the previous label" pass.

### A7 — Sign convention: outflows reported positive in CPALL CF
Multiple CF outflow lines are stored as POSITIVE values (e.g., `ภาษีเงินได้จ่ายออก` = +7,676,690,930). The subtotal line `กระแสเงินสดสุทธิได้มาจากกิจกรรมดำเนินงาน` then SUBTRACTS them, despite the line above showing positive. PTT (per the existing tracer) used negative values for outflows. **The `sign_convention` column in concepts.csv is load-bearing**: any concept whose CPALL value is reported absolute must be tagged `negate_if_outflow` so the parser flips it. I marked all known outflow concepts in `concepts.CPALL.csv` accordingly.

### A8 — Investment in associates appears mid-year (FY2020)
The FY2020 BS shows `เงินลงทุนในบริษัทร่วม` (investment in associates) at 85B THB in 2020 vs **zero** in 2019 — this reflects the Tesco Lotus acquisition (Mar 2020), which became an associate before being further consolidated. Scout flag for any historical analysis crossing the 2019/2020 boundary.

### A9 — D&A is split into 4 separate add-back lines
Unlike PTT's single `ค่าเสื่อมราคาและค่าตัดจำหน่าย` line, CPALL CF shows depreciation as 4 separate lines (Investment Property, PPE, ROU, Intangibles amortization). The canonical concept `depreciation_amortization` (label `ค่าเสื่อมราคาและค่าตัดจำหน่าย`) **will not match any CPALL line**. Two paths:
1. Keep `depreciation_amortization` as-is; add per-asset-class concepts (`depreciation_ppe`, `depreciation_rou`, `amortization_intangibles`, etc.) — proposed in `concepts.CPALL.csv`. Downstream consumers compute the sum.
2. Add a derived/computed concept that auto-sums the 4 components.

I prefer option (1) — derived concepts are out-of-scope per the v0 README ("Better an empty cell than a mislabeled one").

### A10 — CP-group cross-references in notes
The Notes file (`NOTES.DOCX`) is dense with related-party transactions to other CP-group entities (CPF, True, Makro, Lotus's). For any future "extract structured note tables" work, a CPALL filing is a stress test for the related-party-transactions section.

## Top-3 surprising findings

1. **CPALL is a KPMG client, not EY** — directly contradicts the scout brief. KPMG Phoomchai Audit Ltd. has audited CPALL continuously from FY2003 through 2026Q1. The EY-rename investigation cannot be done from CPALL filings.
2. **The FY2003 filing has zero XLS files** — financial statements are distributed as Word tables in `cp7-11t2.doc`. The pipeline's parser path assumes XLSX input; pre-2009 CPALL filings will silently produce zero rows unless a DOC-table fallback is added.
3. **Quarterly filings use thousands of baht, annual filings use baht** — a 1000× scale difference between `2026Q1` and `FY2025` data within the same symbol. Without per-filing unit detection, quarterly figures will be 3 orders of magnitude smaller than annual figures.

## Pointers for downstream slices

- `data/concepts.CPALL.csv` — staging input for slice #15's concept-mapper. 25 new concepts proposed; 11 alias appends needed.
- `data/auditors.CPALL.csv` — staging input for slice #18's auditor-report parser. Single firm `kpmg_phoomchai`.
- The `2026Q1` filing's `DS_INTERNAL_*` sheet pattern (Inflow Tools / DataSnipper artifact) is likely to appear in many recent quarterly filings across symbols — flag for the FilingDiscovery / parser sheet-skip allowlist.
- Sheet-naming regex above should accommodate other retailers (BIGC, MAKRO standalone pre-2021, GLOBAL).
