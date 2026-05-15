# Scout report: SCB

Symbol: **SCB** (Siam Commercial Bank → SCB X holding co.)
Industry hint: bank
Worktree: `scout/SCB` off `feat/v2-dataset-pipeline`
Sample staged at: `/tmp/scout-SCB/`

## TL;DR — three most surprising findings

1. **The SCB ticker silently switched legal entities in 2022.** All filings 2022Q1 and earlier are
   for *Siam Commercial Bank Public Co. Ltd.* (ธนาคารไทยพาณิชย์ จำกัด (มหาชน)). From 2022Q2/FY2022
   onwards the same SEC IDISC ticker (SCB) returns filings for *SCB X Public Co. Ltd.* (บริษัท
   เอสซีบี เอกซ์ จำกัด (มหาชน)) — the holding company that absorbed the bank in April 2022.
   Sheet structure is largely identical (because the holdco's main subsidiary is still the bank),
   but the entity-row label and a handful of sub-line items differ. Downstream queries that
   join by `(symbol='SCB', period < '2022Q2')` vs `(symbol='SCB', period >= '2022Q2')` are
   talking about *different legal entities* even though the ticker is stable.
2. **SEC IDISC fs-norm endpoint only exposes filings since 2022Q1 for SCB** — a 50-year-old
   listed company shows just 17 unique filings. The PRD's "back to IPO (1976)" assumption does
   not hold against the public IDISC fs-norm endpoint. Pre-2022 filings appear to be either on
   a different IDISC view or only in the regulator's restricted-archive endpoints not exposed
   under `/Viewmore/fs-norm`. Worth verifying with another long-listed scout (BBL).
3. **SCB's 2022 annual filing carries an `Emphasis-of-Matter` paragraph about the SCBX restructure**
   (auditor cites note 45) — and the equity-statement workbook has explicit `CE_Conso (Before Re.)`
   and `CE_Conso (After Re.)` sheets capturing the *pre-* and *post-* restructure equity rolls.
   This is the first observed example of a non-restatement-but-still-restructure parser hazard:
   the sheet count jumps from 7 to 9 specifically in the restructure year, and the comparative
   columns mean different things in the two CE sheets. A naive parser that merges by sheet name
   would conflate the two.

## Sample coverage

| filing_id | period | audit_basis | entity (BS row 1) | source_url |
|---|---|---|---|---|
| `22062377` | 2022Q1 | reviewed | ธนาคารไทยพาณิชย์ จำกัด (มหาชน) และบริษัทย่อย | `Download?FILEID=dat/news/202205/22062377.zip` |
| `23016979` | 2022 | audited | บริษัท เอสซีบี เอกซ์ จำกัด (มหาชน) และบริษัทย่อย | `Download?FILEID=dat/news/202302/23016979.zip` |
| `1706FIN200220241653550737T` | 2023 | audited | บริษัท เอสซีบี เอกซ์ จำกัด (มหาชน) และบริษัทย่อย | `Download?FILEID=dat/news/202402/1706FIN200220241653550737T.zip` |
| `1706FIN190220251132070328T` | 2024 | audited | บริษัท เอสซีบี เอกซ์ จำกัด (มหาชน) และบริษัทย่อย | `Download?FILEID=dat/news/202502/1706FIN190220251132070328T.zip` |
| `1706FIN190220261234280476T` | 2025 | audited | บริษัท เอสซีบี เอกซ์ จำกัด (มหาชน) และบริษัทย่อย | `Download?FILEID=dat/news/202602/1706FIN190220261234280476T.zip` |
| `1706FIN141120251632000394T` | 2025Q3 | reviewed | บริษัท เอสซีบี เอกซ์ จำกัด (มหาชน) และบริษัทย่อย | `Download?FILEID=dat/news/202511/1706FIN141120251632000394T.zip` |
| `1706FIN130520261402470059T` | 2026Q1 | reviewed | บริษัท เอสซีบี เอกซ์ จำกัด (มหาชน) และบริษัทย่อย | `Download?FILEID=dat/news/202605/1706FIN130520261402470059T.zip` |

Stratification rationale: spans both legal entities (2022Q1 = bank; 2022+ = holdco), all four
recent annuals (2022-2025), one mid-year quarterly (2025Q3), and the most recent quarterly
(2026Q1). All 7 zips fetched + extracted + normalised; payload was OOXML (zip) under all
extensions including the apparent legacy `.DOC` files in the FY2023 zip (those were OOXML
disguised, not real CFB binary — `libreoffice` was not invoked).

## Sheet inventory

The SCB workbooks use **English-named sheets** (`BS`, `PL`, `CF`, `CE_Conso`, `CE_Separate`,
`CE_Bank`), NOT the 5-Thai-named sheets the assignment hypothesised. This contradicts the
"bank-specific Thai sheet structure" expectation; SCB's parser path will look more like the
general-industrial pattern (sheet name → statement type via a small lookup) than a separate
bank-only path.

| filing | sheet | statement type | non-empty rows |
|---|---|---|---|
| 22062377 (2022Q1) | BS | balance sheet (combined assets + liabilities + equity) | 70 |
| 22062377 | PL | P&L + OCI (3-month) | 63 |
| 22062377 | CE_Conso 1Q22 | Consolidated equity changes 1Q22 | 26 |
| 22062377 | CE_Conso 1Q21 | Consolidated equity changes 1Q21 (comparative) | 24 |
| 22062377 | CE_Bank 1Q22 | Bank-only equity changes 1Q22 (separate sheet, not CE_Separate) | 23 |
| 22062377 | CE_Bank 1Q21 | Bank-only equity changes 1Q21 (separate sheet) | 25 |
| 22062377 | CF | Cash flow (3-month) | 85 |
| 23016979 (2022 annual) | BS | balance sheet | 73 |
| 23016979 | PL | P&L + OCI | 74 |
| 23016979 | CE_Conso (After Re.) | Consolidated equity 2022 *after* SCBX restructure | 36 |
| 23016979 | CE_Conso (Before Re.) | Consolidated equity 2021 *before* restructure (comparative) | 28 |
| 23016979 | CE_Separate 22 | Holdco-only equity 2022 | 19 |
| 23016979 | CE_Separate 21 | Holdco-only equity 2021 (comparative) | 16 |
| 23016979 | CF | Cash flow (annual) | 106 |
| 23016979 | CE_Separate Q2'22 | **Stale leftover sheet from 2022Q2** filing (see anomaly) | 23 |
| 23016979 | CE_Bank Q2'21 | **Stale leftover sheet from 2022Q2** filing (see anomaly) | 25 |
| 1706FIN200220241653550737T (2023) | BS | balance sheet | 63 |
| 1706FIN200220241653550737T | PL | P&L + OCI | 67 |
| 1706FIN200220241653550737T | CE_Conso 2566 | Consolidated equity 2023 | 28 |
| 1706FIN200220241653550737T | CE_Conso 2565 | Consolidated equity 2022 (comparative) | 36 |
| 1706FIN200220241653550737T | CE_Separate 2566 | Holdco-only equity 2023 | 17 |
| 1706FIN200220241653550737T | CE_Separate 2565 | Holdco-only equity 2022 (comparative) | 21 |
| 1706FIN200220241653550737T | CF | Cash flow | 98 |
| 1706FIN200220241653550737T | CE_Separate Q2'22 | **Stale leftover sheet** (see anomaly) | 23 |
| 1706FIN200220241653550737T | CE_Bank Q2'21 | **Stale leftover sheet** (see anomaly) | 25 |
| 1706FIN190220251132070328T (2024) | BS | balance sheet | 63 |
| 1706FIN190220251132070328T | PL | P&L + OCI | 67 |
| 1706FIN190220251132070328T | CE_Conso 2567 | Consolidated equity 2024 | 28 |
| 1706FIN190220251132070328T | CE_Conso 2566 | Consolidated equity 2023 (comparative) | 28 |
| 1706FIN190220251132070328T | CE_Separate 2567 | Holdco-only equity 2024 | 17 |
| 1706FIN190220251132070328T | CE_Separate 2566 | Holdco-only equity 2023 (comparative) | 19 |
| 1706FIN190220251132070328T | CF | Cash flow | 95 |
| 1706FIN190220261234280476T (2025) | BS | balance sheet | 63 |
| 1706FIN190220261234280476T | PL | P&L + OCI | 67 |
| 1706FIN190220261234280476T | CE_Conso 2568 | Consolidated equity 2025 | 28 |
| 1706FIN190220261234280476T | CE_Conso 2567 | Consolidated equity 2024 (comparative) | 28 |
| 1706FIN190220261234280476T | CE_Separate 2568 | Holdco-only equity 2025 | 21 |
| 1706FIN190220261234280476T | CE_Separate 2567 | Holdco-only equity 2024 (comparative) | 19 |
| 1706FIN190220261234280476T | CF | Cash flow | 95 |
| 1706FIN141120251632000394T (2025Q3) | BS | balance sheet | 60 |
| 1706FIN141120251632000394T | PL (3M) | P&L + OCI for the 3-month period | 64 |
| 1706FIN141120251632000394T | PL (9M) | P&L + OCI for the 9-month period | 65 |
| 1706FIN141120251632000394T | CE_Conso 3Q25 | Consolidated equity 9M 2025 | 27 |
| 1706FIN141120251632000394T | CE_Conso 3Q24 | Consolidated equity 9M 2024 (comparative) | 27 |
| 1706FIN141120251632000394T | CE_Separate 3Q25 | Holdco-only equity 9M 2025 | 21 |
| 1706FIN141120251632000394T | CE_Separate 3Q24 | Holdco-only equity 9M 2024 (comparative) | 18 |
| 1706FIN141120251632000394T | CF | Cash flow (9M YTD) | 94 |
| 1706FIN130520261402470059T (2026Q1) | BS | balance sheet | 59 |
| 1706FIN130520261402470059T | PL | P&L + OCI (3-month) | 67 |
| 1706FIN130520261402470059T | CE_Conso 1Q26 | Consolidated equity Q1 2026 | 25 |
| 1706FIN130520261402470059T | CE_Conso 1Q25 | Consolidated equity Q1 2025 (comparative) | 27 |
| 1706FIN130520261402470059T | CE_Separate 1Q26 | Holdco-only equity Q1 2026 | 18 |
| 1706FIN130520261402470059T | CE_Separate 1Q25 | Holdco-only equity Q1 2025 (comparative) | 15 |
| 1706FIN130520261402470059T | CF | Cash flow (3-month YTD) | 79 |

### Sheet-structure observations

- **No Thai-named sheets.** All sheet names are English-coded; statement type is encoded in
  the prefix (`BS`/`PL`/`CF`/`CE_*`). Prior version (1Q22) used `CE_Bank` for the bank-only
  equity sheet; from FY2023 onward the same role is filled by `CE_Separate`. Both names exist
  in the sample — the parser needs to recognise both.
- **The pre-restructure 2022Q1 filing** uses `CE_Bank 1Q22` and `CE_Bank 1Q21` for the
  separate (parent-only, where parent = the bank) equity statements. Post-restructure
  filings use `CE_Separate <YEAR>` for the equivalent holdco-parent role. Statement-type
  classification rule: any sheet whose name starts with `CE_` is a `EQ` (statement of changes
  in equity); whether it's consolidated vs separate comes from the suffix (`Conso` vs
  `Separate`/`Bank`).
- **Quarterly P&L splits into two sheets at Q2/Q3** (`PL (3M)` + `PL (9M)`) — but Q1 and Q4
  filings have just `PL`. Parser must accept both layouts under statement_type=IS.
- **Header rows are not row 1.** Most numeric columns start with their period label at row 6
  or 7 (BS/PL); CF has the period label at row 7 with the actual numeric block starting at
  row 9. There is no consistent `header_row` index — discovery has to scan for the row
  containing `(พันบาท)` (the units indicator) to anchor.
- **All values are in thousands of THB** — sheets explicitly say `(พันบาท)`. Parser must
  multiply by 1000 to land in raw THB as the schema requires.
- **Note-reference column.** Column 2 (B) contains note numbers (`34`, `35`, `36`…) for the
  PL; for BS the note column appears at column 4 (D) in some sheets and column 2 in others.
  The numeric columns in the PL are 3,5,7,9 (consolidated current, consolidated prior, company
  current, company prior); BS uses 4,6,8,10. The parser must detect column layout by header
  row content (`งบการเงินรวม` / `งบการเงินเฉพาะกิจการ`) rather than fixed column indices.

## Auditor inventory

Single firm across the entire 7-filing sample: **KPMG Phoomchai Audit Ltd.** (เคพีเอ็มจี
ภูมิไชย สอบบัญชี). Single signing partner: **Orawan Chunhakitpaisarn** (อรวรรณ ชุณหกิจไพศาล),
CPA registration **6105**. No joint audits. No auditor switch within the visible window.

| filing | sign date | partner | CPA reg | firm |
|---|---|---|---|---|
| 22062377 (2022Q1) | 12 พฤษภาคม 2565 (12 May 2022) | อรวรรณ ชุณหกิจไพศาล | 6105 | บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด |
| 23016979 (2022) | 17 กุมภาพันธ์ 2566 (17 Feb 2023) | อรวรรณ ชุณหกิจไพศาล | 6105 | บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด |
| 1706FIN200220241653550737T (2023) | 20 กุมภาพันธ์ 2567 (20 Feb 2024) | อรวรรณ ชุณหกิจไพศาล | 6105 | บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด |
| 1706FIN190220251132070328T (2024) | 19 กุมภาพันธ์ 2568 (19 Feb 2025) | อรวรรณ ชุณหกิจไพศาล | 6105 | บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด |
| 1706FIN190220261234280476T (2025) | 19 กุมภาพันธ์ 2569 (19 Feb 2026) | อรวรรณ ชุณหกิจไพศาล | 6105 | บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด |
| 1706FIN141120251632000394T (2025Q3) | 14 พฤศจิกายน 2568 (14 Nov 2025) | อรวรรณ ชุณหกิจไพศาล | 6105 | บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด |
| 1706FIN130520261402470059T (2026Q1) | 13 พฤษภาคม 2569 (13 May 2026) | อรวรรณ ชุณหกิจไพศาล | 6105 | บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด |

### Opinion-language samples

**Annual filings (audited)** — opening of the opinion paragraph:

> เสนอ ผู้ถือหุ้นบริษัท เอสซีบี เอกซ์ จำกัด (มหาชน)
> ความเห็น
> ข้าพเจ้าได้ตรวจสอบงบการเงินรวมและงบการเงินเฉพาะกิจการของบริษัท เอสซีบี เอกซ์ จำกัด (มหาชน) และบริษัทย่อย…

The literal opinion-type marker is the section heading **"ความเห็น"** ("Opinion") followed by
the unqualified statement **"ข้าพเจ้าเห็นว่า งบการเงิน… แสดง… โดยถูกต้องตามที่ควร"**
("In my opinion, the financial statements present fairly…"). All five audited samples carry
this pattern — clean unqualified opinions.

**Quarterly filings (reviewed)** — opening:

> เสนอ คณะกรรมการบริษัท เอสซีบี เอกซ์ จำกัด (มหาชน)
> รายงานการสอบทานข้อมูลทางการเงินระหว่างกาลโดยผู้สอบบัญชีรับอนุญาต
> ข้าพเจ้าได้สอบทานงบฐานะการเงินรวมและงบฐานะการเงินเฉพาะกิจการ ณ วันที่ …

Reviewed-quarterly conclusion uses **"ข้อสรุป"** (not "ความเห็น") followed by the standard
ISRE 2410 phrasing **"ข้าพเจ้าไม่พบสิ่งที่เป็นเหตุให้เชื่อว่าข้อมูลทางการเงินระหว่างกาล…
ไม่ได้จัดทำขึ้นตามมาตรฐานการบัญชี ฉบับที่ 34…"** ("Nothing has come to my attention that
causes me to believe the interim financial information is not prepared in accordance with
TAS 34…"). Parser hint: the section heading **"ข้อสรุป"** vs **"ความเห็น"** is a clean
binary signal for `reviewed` vs `audited` opinion phrasing.

**FY2022 emphasis-of-matter** (the SCBX-restructure one, in filing 23016979) — section
heading **"ข้อมูลและเหตุการณ์ที่เน้น"** ("Emphasis of matter"):

> ข้าพเจ้าขอให้สังเกตหมายเหตุข้อ 45 ซึ่งได้อธิบายถึงแผนการปรับโครงสร้างการถือหุ้น ในวันที่
> 22 เมษายน 2565 บริษัทได้จัดสรรหุ้นสามัญเพิ่มทุนจำนวน 3,367,107,286 หุ้น… แทนหลักทรัพย์
> ของธนาคาร ซึ่งถูกเพิกถอนจากการเป็นหลักทรัพย์จดทะเบียน… ความเห็นของข้าพเจ้าไม่ได้เปลี่ยน
> แปลงไปเนื่องจากเรื่องนี้

Note that this paragraph closes with **"ความเห็นของข้าพเจ้าไม่ได้เปลี่ยนแปลงไปเนื่องจาก
เรื่องนี้"** ("Our opinion is not modified in respect of this matter") — i.e., the emphasis
is informational, the opinion is still unqualified. The auditor parser must distinguish
*emphasis of matter* (clean opinion + commentary) from *qualified* (modified opinion).

### Auditor parser hints

- The opinion-type indicator is the section header label, in this consistent ordering:
  - `ความเห็น` → unqualified annual opinion follows
  - `ความเห็นแบบมีเงื่อนไข` → qualified (not observed in SCB sample)
  - `ความเห็นแบบไม่ให้ข้อสรุป` → disclaimer (not observed)
  - `ความเห็นแบบไม่เห็นด้วย` → adverse (not observed)
  - `ข้อสรุป` → reviewed-quarterly clean conclusion
- `going_concern_emphasis` heuristic: search for **"ข้อมูลและเหตุการณ์ที่เน้น"** then check
  whether the paragraph mentions **"การดำเนินงานต่อเนื่อง"** (going concern) — only emit
  `going_concern_emphasis=true` when both phrases appear in the same emphasis section. The
  SCB FY2022 filing's emphasis is about restructure, NOT going-concern, so it should set
  `emphasis_of_matter=true` but `going_concern_emphasis=false`. The current PRD schema has
  only `going_concern_emphasis` — recommend extending to also surface `emphasis_of_matter`
  as a separate boolean so non-GC emphases are not lost.
- Sign-date format is always Thai Buddhist Era (`YYYY` = CE + 543), e.g.
  `19 กุมภาพันธ์ 2569` → 19 Feb 2026 CE.
- Partner name is always inside parentheses two paragraphs above the firm name: `(อรวรรณ
  ชุณหกิจไพศาล)\nผู้สอบบัญชีรับอนุญาต\nเลขทะเบียน 6105\n\nบริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี
  จำกัด`. CPA registration number lives on its own line as `เลขทะเบียน NNNN`.

## Anomaly log

- **Entity migration mid-ticker (2022).** SCB ticker shifted from "Siam Commercial Bank PCL"
  (the bank) to "SCB X PCL" (the holding company) between 2022Q1 (last bank-entity filing)
  and FY2022 / 2022Q2 (first holdco filing). The IDISC ticker is unchanged. Downstream users
  who time-series the SCB ticker are crossing an entity boundary at 2022Q2.
  Recommend: surface the entity name in `filings.parquet` (extracted from BS row 1) so a
  consumer can detect this kind of migration.
- **Stale leftover sheets in FY2022 and FY2023 workbooks.** Both filings carry trailing
  sheets named `CE_Separate Q2'22` (rows: 23) and `CE_Bank Q2'21` (rows: 25) that are
  inconsistent with the annual scope of the rest of the workbook. These look like
  copy-paste leftovers from the SCBX restructure transition; their content is the 2022Q2
  intra-period equity statement. Parser must NOT treat these as valid annual EQ sheets.
  Heuristic: a sheet whose period suffix (`Q2'22` etc.) doesn't match the filing period
  should be flagged or skipped.
- **Non-standard pre-2024 filename pattern.** Filings before 2024 use 8-digit filenames
  (`22062377.zip`, `23016979.zip`); from 2024 onward they use the symbol-prefixed format
  (`1706FIN<DDMMYYYY><HHMMSS><N>T.zip`). The `parse_filing_id` utility handles both, but
  this means the `filing_id` column in `filings.parquet` will have a discontinuous shape
  for any company whose history straddles the 2024 transition. Worth documenting in the
  schema spec.
- **Restatement-by-restructure in FY2022.** FY2022 (filing 23016979) is the only annual
  workbook in the sample with both `CE_Conso (After Re.)` and `CE_Conso (Before Re.)`
  sheets. The `(Before Re.)` sheet shows 2021 equity using the *bank's* opening balance;
  the `(After Re.)` sheet shows 2022 equity using the *holdco's* post-restructure balance.
  This is NOT a v1 "restatement" in the PRD sense (no "company refiled prior period") —
  it's a legal re-domiciliation. The parser should still capture both as separate EQ rows
  with a `consolidation_variant` or similar tag, otherwise the 2021 vs 2022 equity rolls
  silently conflate two different accounting entities.
- **Auditor opinion emphasis-of-matter not flagged by current schema.** The PRD's
  `auditor_reports.parquet` schema has `going_concern_emphasis` only. The SCB FY2022
  emphasis paragraph is about restructure, not GC — it would be lost. Recommend adding
  a generic `emphasis_of_matter` boolean and a free-text `emphasis_topic_hint` so credit
  analysts can find non-GC emphases too.
- **The `.DOC` files in FY2023 zip are OOXML-disguised, not real CFB binary.** Magic bytes
  on `AUDITOR_REPORT.DOC` and `NOTES.DOC` from filing 1706FIN200220241653550737T are
  `PK\x03\x04`, so `normalize_to_ooxml` short-circuits without invoking libreoffice. The
  scout sample has zero true legacy-binary files — useful data point for FormatNormalizer
  test coverage estimation: large banks may not need libreoffice at all.
- **No bank-only sheets.** The PRD's "5 Thai-named sheets" hypothesis for banks does NOT
  hold. SCB sheets are English-coded and look structurally similar to a non-bank filing.
  The bank-ness shows up in the Thai *row labels*, not in the sheet structure. The parser
  doesn't need a separate bank pipeline — it needs a richer concept dictionary.
- **No COGS / no gross profit / no revenue line.** As expected for a bank, the IS starts
  directly with `รายได้ดอกเบี้ย` (interest income) and `ค่าใช้จ่ายดอกเบี้ย` (interest
  expense). The general-industry `revenue` and `cogs` concepts will have zero coverage on
  SCB filings. The coverage-gate (`coverage_gate.py`) needs an industry-aware threshold
  or it will spuriously fail on banks. Recommend: track coverage per `(symbol, statement)`
  rather than overall, and gate per-statement.
- **Q3 quarterly has TWO P&L sheets** (`PL (3M)` and `PL (9M)`). The 9M sheet contains the
  YTD numbers. Whether the parser emits both as separate periods (`2025Q3_3M` and `2025Q3_9M`)
  or just the 3M (canonical quarter) is a design call — flagged for parser-spec discussion.
- **Pre-2022 filings are not visible via fs-norm.** SEC IDISC `/Viewmore/fs-norm?searchSymbol=SCB`
  returns only 17 unique filings (2022Q1 → present). For SCB the bank entity was listed in 1976,
  so 50+ years of pre-2022 filings are somewhere else (or not exposed by IDISC at all). The
  PRD's "back to IPO" promise needs a discovery-coverage caveat. Recommend the discover step
  log a per-symbol "earliest period" so this is visible in `filings.parquet` from day one.

## Coverage estimate

Of the curated cross-industry concepts in `data/concepts.csv` (v0.1):

- **Will hit on SCB**: `total_assets`, `total_liabilities`, `equity`, `cash` (with the alias
  `เงินสด`), `paid_up_capital`, `net_profit` (alias `กำไรสุทธิ`), `profit_before_tax`,
  `income_tax_expense`, `eps_basic`, `ocf`, `investing_activities`, `financing_activities`,
  `dividends_paid`, `depreciation_amortization` (alias `ค่าเสื่อมราคาและรายจ่ายตัดบัญชี`).
- **Will NOT hit on SCB**: `revenue`, `cogs`, `gross_profit`, `selling_expenses`, `admin_expenses`,
  `operating_profit`, `ebit`, `finance_costs`, `ppe` (banks use `ที่ดิน อาคารและอุปกรณ์สุทธิ`
  with `สุทธิ` suffix; existing alias only matches if normaliser strips trailing `สุทธิ`),
  `capex` (banks use `เงินสดจ่ายในการซื้อที่ดิน อาคารและอุปกรณ์`, not the curated PTT phrasing
  `เงินสดจ่ายสำหรับที่ดิน อาคารและอุปกรณ์ และอสังหาริมทรัพย์เพื่อการลงทุน`),
  `tax_paid` (banks use `เงินสดจ่ายภาษีเงินได้`, currently not aliased), `interest_paid`
  (banks use `เงินสดจ่ายดอกเบี้ย`, currently not aliased).
- After applying the SCB-staged aliases (`aliases_th_to_append`) and bank-specific concepts
  (`applicable_industries=bank`), expected coverage of SCB line items rises from roughly
  20% (a dozen rows mapped) to roughly 75–80% of meaningful (non-subtotal, non-header)
  rows.
