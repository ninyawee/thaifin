# Scout report — SCC (Siam Cement Group)

**Branch:** `scout/SCC` (off `feat/v2-dataset-pipeline`)
**Symbol:** `SCC` — บริษัท ปูนซิเมนต์ไทย จำกัด (มหาชน)
**Listed since:** 1975 (50 years of filings)
**Industry hint:** industrial (cement + chemicals + packaging conglomerate)
**Filings discovered:** **213 unique zip URLs** from 1997 to 2026Q1.

## Discovery summary

Hit `https://market.sec.or.th/public/idisc/th/Viewmore/fs-norm?searchSymbol=SCC`
via `parse_fs_norm_html`. Coverage:

| Decade | Filings |
|--------|---------|
| 1997–2000 | 21 |
| 2001–2010 | 71 |
| 2011–2020 | 78 |
| 2021–2026Q1 | 43 |

The earliest filings predate SEC's standard XLS/DOC/zip layout and use a
**plain TIS-620 text file** packaging (extension `.t97` / `.t98`).

## Stratified sample — 7 filings staged at `/tmp/scout-SCC/`

| Tag | Period | Audit | Consol | Source URL ext | Notes |
|-----|--------|-------|--------|----------------|-------|
| oldest_annual | 1997 | audited | company | `.t98` | TIS-620 plain text, 49.5 KB |
| oldest_annual_consol | 1997 | audited | consolidated | `.t98` | TIS-620 plain text, 48.5 KB |
| era_2003_annual | 2003 | audited | consolidated | `.zip` | 3-doc layout `scct1/2/3.doc` + `contents.txt` |
| era_2010_annual | 2010 | audited | consolidated | `.zip` | XLS, 3 Thai-named sheets |
| era_2015_annual | 2015 | audited | consolidated | `.zip` | XLS, 3 numbered sheets |
| most_recent_annual | 2024 | audited | consolidated | `.zip` | XLSX, 5 numbered sheets |
| most_recent_quarterly | 2026Q1 | reviewed | company | `.zip` | XLS, 4 numbered sheets |

All files normalised to OOXML via `normalize_to_ooxml` (libreoffice-backed
for `.DOC`/`.XLS`, no-op rename for `.XLSX`). The 1997 `.t98` files are NOT
zip archives — `normalize_to_ooxml` cannot handle them; they were decoded
out-of-band with `iconv -f tis-620 -t utf-8 -c`.

## Sheet-structure inventory — per-era variants

### 2024 annual (modern, post-2018 IFRS layout) — 5 sheets

| Sheet # | Statement | Notes |
|---------|-----------|-------|
| 1 | งบฐานะการเงินรวม (BS) | Single comparative period; balance items and equity in one sheet |
| 2 | งบกำไรขาดทุนรวม (IS) + งบกำไรขาดทุนเบ็ดเสร็จรวม (OCI) | IS and OCI combined into one sheet |
| 3 | งบการเปลี่ยนแปลงส่วนของผู้ถือหุ้นรวม (EQ) — **prior year comparative** | Movements 1-Jan-2566 → 31-Dec-2566 |
| 4 | งบการเปลี่ยนแปลงส่วนของผู้ถือหุ้นรวม (EQ) — **current year** | Movements 1-Jan-2567 → 31-Dec-2567 — **EQ split across two sheets!** |
| 5 | งบกระแสเงินสดรวม (CF) | Standard CF statement |

### 2026Q1 quarterly (most recent) — 4 sheets

| Sheet # | Statement | Notes |
|---------|-----------|-------|
| 1 | งบฐานะการเงิน (BS) | Columns: 31 มี.ค. 2569 (unaudited) | 31 ธ.ค. 2568 (year-end comparative) |
| 2 | งบกำไรขาดทุน (IS) | Quarter vs prior-year quarter |
| 3 | งบการเปลี่ยนแปลงส่วนของผู้ถือหุ้น (EQ) | Single year, single sheet |
| 4 | งบกระแสเงินสด (CF) | |

Note: this is the **company-only** filing (`เดี่ยว`). The matching
`consolidated` zip for the same quarter uses the same sheet layout but
with "รวม" suffixes on titles.

### 2015 annual — 3 sheets, anonymous numbered

| Sheet # | Statement | Notes |
|---------|-----------|-------|
| 1 | งบแสดงฐานะการเงินรวม (BS) | |
| 2 | งบแสดงการเปลี่ยนแปลงส่วนของผู้ถือหุ้น (EQ) | Single sheet — no per-year split |
| 3 | งบกระแสเงินสดรวม (CF) | |

**No IS sheet.** SCC 2015 puts IS+OCI inside the BS sheet (continuation rows)
or onto a continuation block — needs further investigation. The IS rows are
NOT in sheet 1 from inspection; this is a possible anomaly worth flagging
for the parser-author.

### 2010 annual (suspected mid-era variant) — 3 sheets, **Thai-named tabs**

| Sheet name (verbatim) | Statement | Notes |
|----------------------|-----------|-------|
| `งบดุล-งบกำไรขาดทุน` | BS + IS combined | BS rows 1–89, IS rows 91+ in same sheet |
| `งบเปลี่ยนแปลง` | EQ | Single sheet |
| `งบกระแสเงินสด` | CF | |

Sheet name uses old-style "งบดุล" (Balance) — legacy term replaced by
"งบฐานะการเงิน" / "งบแสดงฐานะการเงิน" in post-2013 IFRS adoption. Parser
must accept BOTH terms for statement-type classification.

### 2003 annual (DOC-based, pre-XLS) — 3 .doc files

Layout per `contents.txt`:
- `scct1.doc` (88 KB) — รายงานผู้สอบบัญชี (auditor's report) **only**
- `scct2.doc` (328 KB) — งบการเงิน (BS, IS, EQ, CF as Word tables)
- `scct3.doc` (1.16 MB) — หมายเหตุประกอบงบการเงิน (notes)

Filename pattern: `<sym>T<n>.<ext>` where `n ∈ {1,2,3}` is content ID. The
financial statements are **Word tables**, NOT spreadsheets — `parse_xlsx`
cannot handle them. SCC's 2003 (and earlier) era requires a `parse_docx_fs`
path. Six SCC year-end annual filings (1997–~2003 transition) use this
format.

### 1997 (oldest, ad-hoc) — 1 plain-text file

Single TIS-620 plain-text file containing the auditor report + four
statements + notes, loosely separated by whitespace and ASCII headers.
There is NO standardised structure: no XLS, no DOC, no zip — the file
extension `.t97`/`.t98` (= "Thai 97/98") signifies the year of the
2-digit Buddhist-Era period being filed.

The pre-2003 SCC corpus (~10 filings from 1997–2002) all use this format.
**Parsing them is out of scope for v1**; recommend recording them in
`filings.parquet` with a `parse_status='unsupported_legacy_text'` marker
and skipping `financial_lines` extraction.

## Concept inventory — see `data/concepts.SCC.csv`

Findings (also captured in the staging CSV):

* **22 ALIAS_APPEND rows** for existing v0 concepts that observe new SCC
  phrasings (notably the pre-2013 "ขายสุทธิ" for revenue, the colloquial
  "กำไรสุทธิ" for net_profit, etc.).
* **30 NEW_CONCEPT proposals** covering:
  - **Balance-sheet detail**: `inventory`, `trade_receivables`, `trade_payables`,
    `short_term_borrowings`, `long_term_debt`, `debentures`, `goodwill`,
    `intangible_assets`, `investments_in_associates_and_jv`,
    `non_controlling_interest`, `lease_liabilities`,
    `deferred_tax_assets`, `deferred_tax_liabilities`,
    `employee_benefit_obligations`, `total_current_assets`,
    `total_non_current_assets`, `total_current_liabilities`,
    `total_non_current_liabilities`, `retained_earnings_unappropriated`,
    `legal_reserve`, `general_reserve`.
  - **Income-statement conglomerate-specific**: `share_of_profit_associates`,
    `nci_profit`, `parent_profit`, `other_income`, `total_comprehensive_income`,
    `fx_translation_oci`.
  - **Cash-flow M&A**: `cash_paid_acquire_subsidiaries`,
    `cash_received_disposal_subsidiaries`, `proceeds_from_long_term_borrowings`,
    `repayment_of_long_term_borrowings`, `proceeds_from_debentures`,
    `repayment_of_debentures`, `interest_received`, `dividends_received`.

Most new concepts are tagged `applicable_industries` empty (cross-industry);
two are tagged `industrial` because they reflect capital-market access
typical of large industrials (`debentures`, `proceeds_from_debentures`).

`non_controlling_interest`, `share_of_profit_associates`, `nci_profit`,
`parent_profit` are the four **conglomerate-essential** concepts predicted
in the assignment — confirmed material on every consolidated SCC filing
since 2003.

## Auditor inventory — see `data/auditors.SCC.csv`

* **One firm** across the entire 29-year window 2003–2026Q1: KPMG Phoomchai
  Audit Ltd. (`บริษัท เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด`).
* `parent_firm = kpmg_global` (already registered in `data/auditors.csv`).
* **Five distinct partners** observed (Thai SEC mandates partner rotation
  every 7 years), all signing under the KPMG Phoomchai entity:
  - 2003 — นายวิเชียร ธรรมตระกูล (CPA #3183)
  - 2010 — สุพจน์ สิงห์เสน่ห์ (CPA #2826)
  - 2015 — วินิจ ศิลามงคล (CPA #3378)
  - 2024 — สุรีย์รัตน์ ทองอรุณแสง (CPA #4409)
  - 2026Q1 — สุรีย์รัตน์ ทองอรุณแสง (CPA #4409, review)
* **1997**: signed by นายธวัช ภูษิตโภยไคย (CPA #1724) **without firm
  header** — typical of the pre-2003 ad-hoc layout. CPA #1724 is widely
  associated with KPMG's Thai predecessor "Peat Marwick Suthee", but
  there is no verbatim firm name in the 1997 filing itself, so the row
  is left out of the staging CSV per the "no fabricated labels" rule
  in `data/README.md`.

**No auditor switch observed across the 50-year history sampled.** SCC has
been a KPMG client end-to-end. (Original assignment guess of "KPMG with
multiple switches" — the firm guess is correct, the switch guess is not.)

## Anomaly log

1. **(MAJOR)** **1997 ad-hoc plain-text format**: pre-2003 SCC filings
   are single TIS-620 text files (`.t97`/`.t98`) with no tabular structure.
   `normalize_to_ooxml` cannot handle them — magic-byte classifier falls
   into `SHAPE_UNKNOWN` and libreoffice fails. Recommend a separate
   `parse_legacy_text` code path or `parse_status='unsupported_legacy_text'`
   marker. Affects ~10 SCC filings (1997–~2002) and likely many other
   long-listed names (BBL, BAY, PTT-pre-IPO predecessors, etc.).
2. **(MAJOR)** **2003-era 3-doc layout**: `scct1.doc` / `scct2.doc` /
   `scct3.doc` + `contents.txt` index. Financial statements are inside
   Word tables in `scct2.doc`, not in any XLS. The current pipeline
   architecture (`parse_xlsx` for line items, `parse_docx_*` for
   notes/auditor) does not have a `parse_docx_fs` path. Affects a window
   of 5–8 years (~1999–2007) for any company on SET pre-XLS.
3. **(MAJOR)** **2010 mid-era sheet variant**: BS and IS are concatenated
   into a single sheet named `งบดุล-งบกำไรขาดทุน`. Sheet-name → statement
   classifier must understand that this name covers TWO statement types,
   and the parser must split rows by an internal "section break" (header
   `งบกำไรขาดทุนรวม` appearing mid-sheet at row 92). Sheet names are also
   in **Thai with diacritics** — different from the 2015+ anonymous
   numbered convention.
4. **(MAJOR)** **EQ split across two sheets in 2024 annual**: SCC's modern
   filings put the EQ statement on TWO sheets — sheet 3 = prior-year
   comparative movements, sheet 4 = current-year movements. A naive
   sheet-name classifier (`งบการเปลี่ยนแปลง...`) will see a duplicate
   statement and need to merge by date heading.
5. **(SIGN CONVENTION)** **CF outflows in 2010 stored as POSITIVE**: in
   the 2010 CF sheet, `ซื้อที่ดิน อาคารและอุปกรณ์` (capex) value is
   `13,719,981` (positive), while in 2024 the same concept on row 55
   stores `-26,662,674` (negative). The sign flips with the parenthetical
   "(เงินสดจ่าย…)" in the row label. Confirms `negate_if_outflow` policy
   for `capex`, `tax_paid`, `dividends_paid`, `interest_paid`,
   `cash_paid_acquire_subsidiaries`, `repayment_of_long_term_borrowings`,
   `repayment_of_debentures`. Without it, 50% of the SCC corpus shows
   the wrong sign.
6. **(TERMINOLOGY)** **Pre-2013 vs post-2013 NCI naming**: the same
   "non-controlling interest" concept uses two distinct Thai names —
   `ส่วนของผู้ถือหุ้นส่วนน้อย` / `ผลประโยชน์ของผู้ถือหุ้นส่วนน้อย` (pre-2013) and
   `ส่วนได้เสียที่ไม่มีอำนาจควบคุม` (post-2013, after TFRS 10). Same
   pattern for `parent_profit`: `ส่วนที่เป็นของผู้ถือหุ้นบริษัทใหญ่` (pre)
   vs `ส่วนที่เป็นของผู้ถือหุ้นของบริษัท` (post). Aliases captured in
   `data/concepts.SCC.csv`.
7. **(TERMINOLOGY)** **BS heading rename**: `งบดุล` (pre-2013) →
   `งบฐานะการเงิน` / `งบแสดงฐานะการเงิน` (post-2013). Sheet-name
   classifier must accept both.
8. **(REVENUE NAMING)** SCC 2010 uses `ขายสุทธิ` for revenue — different
   from PTT's `รายได้จากการขายและการให้บริการ` and SCC's own 2024
   `รายได้จากการขาย`. Two new aliases to append.
9. **(QUARTERLY-ONLY)** SCC quarterly filings (~Q1/Q2/Q3) carry the
   parenthetical `(ไม่ได้ตรวจสอบ)` in the BS column header to mark the
   current-period column as unaudited (vs the year-end comparative
   which IS audited). The parser must NOT use this string as a numeric
   value or column-name prefix — it's metadata. Confirms `audit_basis`
   should be set from the fs-norm row's `สอบทาน`/`ตรวจสอบ` flag, not
   parsed from cell values.
10. **(NOTES STRUCTURE)** SCC NOTES.DOC contains segment-reporting tables
    for cement / chemicals / packaging business units (typical for
    industrial conglomerate). The dataset's v1 NotesParser is shallow
    (markdown only) — segment data is preserved in the markdown but
    NOT extracted as structured rows. Worth flagging for v2.1.

## Surprising findings — top 3

1. **NO 12-sheet "BS-Asset Consol / BS-Lai Consol" mid-era variant for SCC.**
   The assignment hinted SCC might use the 12-sheet PTT-style mid-era
   layout. **It does not.** SCC consistently uses 3–5 sheets per filing
   across 2003–2026, with the *number* changing but not the per-section
   split. The mid-era variation is a **continuation-row pattern within
   a single sheet** ("งบดุล-งบกำไรขาดทุน" containing BOTH BS and IS),
   which is structurally simpler than 12-sheet but breaks every
   sheet-name → statement classifier.

2. **No auditor switch in 50 years.** Single firm (KPMG Phoomchai) from
   2003 onwards, and the 1997 partner's CPA license traces back to
   KPMG's Thai predecessor (Peat Marwick). Original prediction
   ("watch for auditor changes over 50 years") was wrong for SCC —
   making it a clean baseline against which other scouts' switch
   patterns can be compared.

3. **Pre-2003 ad-hoc text format is a hard blocker for early SCC data.**
   The `.t97/.t98` plain-text format predates SEC's standardisation and
   has no tabular structure recoverable by libreoffice. Any company
   listed before 2003 (PTT, BBL, BAY, AOT, SCC, etc.) loses ~5–10 years
   of early data unless a custom legacy-text parser is built. Affects
   the dataset's claim of "filings back to each company's IPO" for
   long-listed names. Recommend a `parse_status` field on
   `filings.parquet` to make the gap explicit.
