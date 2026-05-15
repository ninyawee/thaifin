# Scout report — BBL (Bangkok Bank PCL)

**Symbol**: BBL
**Industry**: bank (commercial banking)
**Total filings on SEC IDISC**: 120 unique zips, oldest = FY1997, latest sampled = 2026Q1
**Sample size**: 7 filings (oldest, mid-history, recent)

> NOTE: Assignment hinted "since 1944, ~234 filings." SEC IDISC actually exposes
> only 120 unique BBL filings starting **1997** (BBL was founded in 1944 but pre-1997
> filings predate the SEC's electronic disclosure system). The "234 row count"
> in the assignment refers to the discovery-page rows, which double-count each
> filing once per consolidation (consolidated + company).

## 1. Sheet inventory

Five-sheet structure across the entire 1997-2026 sample. Bank filings differ
markedly from PTT's industrial layout: **no segmented IS lines for COGS/gross
profit/operating profit**; instead "interest income/expense", "fee income",
"non-interest income". The two `ปป-*` sheets are **per-consolidation** views of
the equity-changes statement (not separate statement types).

| filing | sheet name | statement type | row count | notes |
|---|---|---|---|---|
| **1997** (00010011.t98) | (single TIS-620 text file, no XLS) | mixed BS/IS/CF/notes | n/a | **legacy ad-hoc format**: plain `.t98`-extension TIS-620 plain text, NOT a zip; contains auditor report + all four statements as inline text. No structural separation. |
| **1999** (00010108.t00) | (single TIS-620 text file, no XLS) | mixed BS/IS/CF/notes | n/a | Same ad-hoc format as 1997. **Pre-2001 filings need a fundamentally different parser path.** |
| **2005** (06009450) | งบดุล | BS | 305 | filenames are `BBLT1.doc`, `BBLT2.xls`, `BBLT3.doc` — NOT the standard `FINANCIAL_STATEMENTS.XLS` triple. BBLT1=auditor, BBLT2=financials, BBLT3=notes. |
| 2005 | งบกำไรขาดทุน | IS | 133 | pre-IFRS9 layout (provision-for-bad-debt, no ECL) |
| 2005 | ปป-รวม | EQchg (consolidated) | 202 | |
| 2005 | ปป-เฉพาะ | EQchg (company) | 213 | |
| 2005 | งบกระแสเงินสด | CF | 134 | |
| **2010** (11006554) | งบดุล | BS | 227 | First standard-named filing in sample; legacy `.XLS`/`.DOC` binaries — needs libreoffice |
| 2010 | งบกำไรขาดทุน | IS | 278 | still pre-comprehensive-IS format (no OCI section) |
| 2010 | ปป-รวม | EQchg (consolidated) | 181 | |
| 2010 | ปป-เฉพาะ | EQchg (company) | 217 | |
| 2010 | งบกระแสเงินสด | CF | 125 | |
| **2018** (19015954) | งบแสดงฐานะการเงิน | BS | 86 | sheet name changed: 'งบดุล' → 'งบแสดงฐานะการเงิน' |
| 2018 | งบกำไรขาดทุนเบ็ดเสร็จ | IS+OCI | 309 | switched to comprehensive-income format (TFRS 1) |
| 2018 | ปป-รวม | EQchg (consolidated) | 157 | |
| 2018 | ปป-เฉพาะ | EQchg (company) | 196 | |
| 2018 | งบกระแสเงินสด | CF | 118 | |
| **2025** (0001FIN250220261153460896T) | งบฐานะการเงิน | BS | 102 | sheet name shortened again: 'งบแสดงฐานะการเงิน' → 'งบฐานะการเงิน' (~2020) |
| 2025 | งบกำไรขาดทุนเบ็ดเสร็จ | IS+OCI | 320 | IFRS-9 compliant: ECL replaces loan-loss provision |
| 2025 | ปป-รวม | EQchg (consolidated) | 142 | |
| 2025 | ปป-เฉพาะ | EQchg (company) | 200 | |
| 2025 | งบกระแสเงินสด | CF | 114 | |
| **2026Q1** (0001FIN130520261452000947T) | งบฐานะการเงิน | BS | 105 | quarterly is single-period (no comparative columns prior year) |
| 2026Q1 | งบกำไรขาดทุนเบ็ดเสร็จ | IS+OCI | 314 | |
| 2026Q1 | ปป-รวม | EQchg (consolidated) | 135 | |
| 2026Q1 | ปป-เฉพาะ | EQchg (company) | 191 | |
| 2026Q1 | งบกระแสเงินสด | CF | 114 | |

### Sheet-classification flags

- **No `OCI` standalone sheet.** OCI is appended to the IS sheet (2018+) as a
  continuation block after the net-profit row. The parser cannot rely on a
  separate sheet for OCI; it must split the IS sheet at the
  'กำไร (ขาดทุน) เบ็ดเสร็จอื่น' header row.
- **`ปป-รวม` and `ปป-เฉพาะ` are NOT ambiguous sheet names** — they are
  per-consolidation views of the EQchg statement. Suffix mapping:
  `รวม`=consolidated, `เฉพาะ`=company. Same convention used by PTT, but
  here both sheets always exist (BBL always has subsidiaries).
- **2005 filename triple is non-standard** (`BBLT1/2/3.doc/xls`). Pipeline
  must classify by file content/extension, not by filename pattern.
- **Pre-2001 filings (.t97/.t98/.t99/.t00) are NOT zips at all.** They are
  TIS-620 plain-text dumps containing the entire annual report. Decoding
  requires `iconv -f TIS-620 -t UTF-8` + a custom text-table parser. Out of
  scope for the v1 OOXML pipeline; either skip pre-2001 entirely or build a
  separate text-mode parser. Recommend documenting as "BBL coverage starts 2001".

### Cells-with-labels-in-column-C

Bank XLS files use a 3-level indentation pattern: section headers in column A,
sub-totals in column B, leaf items in column C. The naive
`take col-A only` approach captures section headers but misses leaf labels
(e.g., individual cash-flow line items like 'เงินสดจ่ายในการซื้ออาคาร และอุปกรณ์'
all live in column C). Parser must walk both A and C.

### No subsidiary-by-subsidiary breakdowns observed

BBL consolidates subsidiaries silently — no per-subsidiary sub-table on the
financial-statements sheet. (Subsidiary detail is in NOTES, out of scope.)

## 2. Auditor inventory (see also `data/auditors.BBL.csv`)

**Single-firm relationship**: BBL has been audited by Deloitte's local Thai
entity in every sampled year (1997-2026, full 30-year span).

The legal-entity name changed once during the firm-reorganization era ~2007-2010:

| era | legal entity (Thai) |
|---|---|
| 1997-2005 (and earlier) | สำนักงานดีลอยท์ ทู้ช โธมัทสุ ไชยยศ (Office form, partnership) |
| 2010-2026 | บริษัท ดีลอยท์ ทู้ช โธมัทสุ ไชยยศ สอบบัญชี จำกัด (Co. Ltd. form) |

Both legal entities map to `parent_firm = deloitte_global`.

**No joint audits observed.**

### Signing-partner roster (sample)

| year | partner | license # | firm form |
|---|---|---|---|
| 1997 | เติมศักดิ์ กฤษณามระ | 1106 | Office |
| 1999 | ดร. ศุภมิตร เตชะมนตรีกุล | 3356 | Office |
| 2005 | นิติ จึงนิจนิรันดร์ | 3809 | Office |
| 2010 | เพิ่มศักดิ์ วงศ์พัชรปกรณ์ | 3427 | Co. Ltd. |
| 2018 | ดร. ศุภมิตร เตชะมนตรีกุล | 3356 | Co. Ltd. (same partner returns ~19 years later) |
| 2025 | นิสากร ทรงมณี | 5035 | Co. Ltd. |
| 2026Q1 | นิสากร ทรงมณี | 5035 | Co. Ltd. (interim-review opinion) |

### Opinion-language samples

**Annual unqualified (2005-2025)** — opening:
> ข้าพเจ้าได้ตรวจสอบ... ข้าพเจ้าเห็นว่า งบการเงินรวมและงบการเงินเฉพาะ... แสดงฐานะการเงิน... โดยถูกต้องตามที่ควร...

**Quarterly review (2026Q1)** — distinct format, negative-form conclusion:
> รายงานการสอบทานข้อมูลทางการเงินระหว่างกาลโดยผู้สอบบัญชีรับอนุญาต
> ... ข้าพเจ้าไม่พบสิ่งที่เป็นเหตุให้เชื่อว่าข้อมูลทางการเงินระหว่างกาลดังกล่าวไม่ได้จัดทำขึ้นตามมาตรฐานการบัญชี ฉบับที่ 34 ...

The quarterly review uses TSA 2410 standard ("การสอบทาน"). The opinion-classifier
needs a SEPARATE branch for review reports — they will never say
"แสดงโดยถูกต้องตามที่ควร" so a strict regex on that phrase will mark every
quarterly filing as `qualified` or `disclaimer` by mistake. Recommend opinion
classifier branch on the report-title line first
(`รายงานของผู้สอบบัญชี` vs `รายงานการสอบทาน`).

**1997 emphasis-of-matter (Asian Financial Crisis)** — informational only, NOT
a qualification or going-concern flag:
> โดยที่มิใช่เป็นการแสดงความเห็นอย่างมีเงื่อนไข โปรดพิจารณาหมายเหตุประกอบงบการเงิน
> ข้อ 1 ข้อ 2 ข้อ 3 และข้อ 4.25 ความไม่มีเสถียรภาพของสถานการณ์ทางเศรษฐกิจของประเทศ
> ซึ่งมีผลกระทบในระดับหนึ่งและอาจจะยังมีผลกระทบต่อไปต่อการดำเนินงานตลอดจนการดำรง
> สถานภาพของสินทรัพย์และหนี้สินของระบบธนาคารพาณิชย์

The phrase `โดยที่มิใช่เป็นการแสดงความเห็นอย่างมีเงื่อนไข` ("without qualifying our opinion")
is the explicit Thai-language marker for an Emphasis-of-Matter paragraph in
unqualified opinions. Useful keyword for classifier.

## 3. Anomaly log

- **Pre-2001 filings are TIS-620 plain text, not zips.**
  Files like `00010011.t98` (FY1997) and `00010108.t00` (FY1999) are 200-400 KB
  TIS-620-encoded text dumps with the entire annual report inline. They are
  served by SEC IDISC under the same `Download?FILEID=` URL pattern. The
  `FilingFetcher` will save them with a `.zip` extension that is a LIE — they
  are not zip-format. Downstream `zipfile.ZipFile()` will raise `BadZipFile`.
  **Coverage decision needed**: skip pre-2001, or build a TIS-620 text parser?
  At minimum, `FilingFetcher` should detect non-zip magic bytes and route to
  a different code path (or fail-gracefully into an `unsupported_format` bucket).

- **Filename non-standardization in 2005-era filings.** The 2005 zip
  (`06009450.zip`) contains `BBLT1.doc / BBLT2.xls / BBLT3.doc` instead of
  the canonical `AUDITOR_REPORT.DOC / FINANCIAL_STATEMENTS.XLS / NOTES.DOC`.
  The pipeline currently identifies the financial XLS by filename heuristics
  in `_process_filings`; that will fail for 2005-era BBL filings.
  Recommendation: detect by file extension + content sniffing, not by filename.
  Estimate: ~5-10 years of BBL filings (~2002-2008?) follow this convention;
  same likely for other long-history symbols (SCB, KBANK, KTB, BAY).

- **Sheet-name evolution across regulatory regimes:**
  - Balance sheet: `งบดุล` (1997-2010) → `งบแสดงฐานะการเงิน` (2013+) → `งบฐานะการเงิน` (~2020+)
  - Income statement: `งบกำไรขาดทุน` (pre-2013) → `งบกำไรขาดทุนเบ็ดเสร็จ` (post-TFRS1 adoption)
  - The parser's sheet-classifier MUST accept all three BS variants and both IS variants.

- **2010 NOTES.DOC normalization failure for FY2025 filing.** libreoffice exits
  non-zero converting `NOTES.DOC` from the 2025 zip
  (`0001FIN250220261153460896T`). The XLS and AUDITOR_REPORT.DOC convert fine
  from the same zip. Suspect: the 2025 NOTES file may use a non-standard DOC
  variant or contain corrupt internal structures. Re-investigation needed for
  the notes-parser slice; out of scope for scout. (Auditor + financial parsing
  unaffected.)

- **OCI lives on the IS sheet, not its own sheet.** Banks have substantial OCI
  (FX-translation reserve, AFS revaluation, etc). Parser must split the IS
  sheet at the 'กำไร (ขาดทุน) เบ็ดเสร็จอื่น' header to separate IS and OCI
  rows in `financial_lines`. Failing to split will mis-tag OCI items as IS.

- **IFRS-9 transition 2020:** Three concept families changed across the
  IFRS-9 boundary, and the new and old concepts are NOT semantically
  equivalent:
  - Loan loss provision (`หนี้สูญและหนี้สงสัยจะสูญ`) → ECL (`ผลขาดทุนด้านเครดิตที่คาดว่าจะเกิดขึ้น`)
  - Investment classification: `เงินลงทุนชั่วคราว/ระยะยาว` → `สินทรัพย์ทางการเงินที่วัดมูลค่าด้วย FVTPL/FVOCI/AC`
  - Allowance: `ค่าเผื่อหนี้สงสัยจะสูญ` → ECL allowance (different statistical model)

  Treating them as one concept will mix incompatible accounting bases.
  **Recommend two separate concepts** (`loan_loss_provision` for pre-2020,
  `expected_credit_loss` for post-2020). I've staged both in `concepts.BBL.csv`.

- **No restatement columns observed** in the 2025 annual filing. (Compare to
  PTT 2025 which carries 4 columns per period for restated comparatives.)
  BBL appears to either not restate or to suppress the restatement column.
  Re-check on a year with a known restatement event.

- **No amendment/refiling pairs detected** in the 120-filing history (each
  period appears exactly once for each `(audit_basis, consolidation)` combo).

- **2026Q1 has consolidation = 'company' only** in the discovery row.
  Looking at the filing: it actually contains BOTH consolidated and company
  data side-by-side in the same XLS — but the discovery page only emits one
  row per filing for interim periods. This appears to be a discovery-page
  quirk, not a data quirk. Flag for the discovery layer to confirm.

- **Sign convention surprise — 'หนี้สูญและหนี้สงสัยจะสูญ' is reported POSITIVE on the IS** (it's a charge, but appears as a positive number with no parentheses; it gets subtracted in the chained subtotal). Pipeline must NOT auto-flip the sign for this concept; `as_reported` is correct. Same for ECL.

- **Quarterly XLS missing prior-period comparatives.** Standard quarterly filings
  (e.g., 2026Q1) carry only the current quarter and YTD; PTT-style 4-column
  layout doesn't apply. Parser must not assume 4 value columns.

- **Per-share data (R89-R90) reports BOTH bank-only and consolidated** in the
  same row group. EPS is consolidated, weighted-share-count is consolidated;
  bank-only EPS is on a different line. Parser needs care to bind per-share
  rows to the right consolidation column.

## Summary stats (counts)

- **New concepts proposed**: 21 (banking-specific: interest_income/expense,
  net_interest_income, fee_income/expense, ECL, loan_loss_provision,
  loans_to_customers, deposits_from_customers, interbank_assets/liabilities,
  investments_net, debt_issued_and_borrowings, allowance_for_doubtful_accounts,
  interest_paid_bank, interest_received, dividends_received, gain_on_investments,
  profit_before_tax_bank, net_profit_bank, other_equity_components,
  non_controlling_interests).
- **Alias-only extensions**: 3 (cash, capex (2 variants), depreciation_amortization).
- **Auditor rows**: 2 (Deloitte Office form + Deloitte Co. Ltd. form, both → deloitte_global).
- **Sample filings inspected**: 7 (5 successfully OOXML-normalized, 2 pre-2001 in TIS-620 plain text).
