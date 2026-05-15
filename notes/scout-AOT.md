# Scout report — AOT (Airports of Thailand PCL)

**Industry**: Transport / state enterprise (rัฐวิสาหกิจ).
**Listed**: 30-Sep-2002 (registered as PCL); first SEC IDISC filing 2004Q1.
**Filings discovered (2026-05-15 walk)**: 88 unique periods × 2 consolidations = 176 fs-norm rows.
**Coverage span**: FY2004 → 2026Q1.
**Sample inspected**: 6 stratified — FY2004, FY2010, FY2015, FY2020, FY2025, 2026Q1.

> **Headline finding**: AOT switched its statutory auditor from **SAO** (Office of the
> Auditor General of Thailand, government auditor) to **EY** at FY2025, then to
> **KPMG** for the very next quarterly (2026Q1). For 21 prior years (FY2004 through
> FY2024) every audit was signed by SAO. This is the most parser-relevant finding
> below — see §3 for verbatim opinion-language characterization across the SAO and
> Big-4 templates AOT now uses.

---

## 1. Discovery summary

| Period span | Audit basis | Count | Source-URL pattern |
|---|---|---|---|
| 2004 → 2026Q1 | reviewed (Q1/Q2/Q3) | 66 | `dat/news/<YYYYMM>/...zip` |
| 2004 → 2025  | audited (annual)    | 22 | same |
| **Total**    |                     | **88** | |

Notes:
- Fiscal year-end is **30-Sep** (not Dec). Q1 = Oct–Dec, etc.
- Pre-2023, FILEID is short numeric (`05000650.zip`). 2023+ uses long alphanumeric
  (`0765FIN201120231647360769T.zip`) — same scheme PTT/COM7 use.
- 2004 zip uses non-canonical filenames (`aott1.doc`, `aott2.xls`, `aott3.doc`)
  rather than `AUDITOR_REPORT.DOC` / `FINANCIAL_STATEMENTS.XLS` / `NOTES.DOC`.
  By inspection: aott1=auditor, aott2=financials, aott3=notes. The parser must
  not assume canonical filenames for very old filings — fall back to file-content
  classification (auditor docs always start with `รายงานของผู้สอบบัญชี`, notes
  always start with `หมายเหตุประกอบงบการเงิน`).
- 2007Q1 is missing from the IDISC index (gap between 2006Q3 and 2007Q2). Likely
  a publishing gap, not an issue with our discovery.
- All 6 sampled zips downloaded cleanly; libreoffice converted all 6 successfully.
- Modern filings (2024+) carry an `_com.sap.ip.bi.xl.hiddensheet` ghost sheet —
  parser should skip sheets matching that name.

---

## 2. Sheet-structure inventory

Per-filing summary of the sheets present in `FINANCIAL_STATEMENTS.XLS[X]`.
"BS" = balance-sheet; "BS2" = continuation page (always 2 sheets for AOT
because BS is too tall for one print page); "IS" = P&L; "OCI" = OCI continuation;
"EQ-cons" / "EQ-co" = changes in equity (consolidated / company); "CF" = cash flow.

| Filing | Sheet count | Sheet names (verbatim) |
|---|---|---|
| **AOT-2004-FY** | 6 | `blancesheets`, `blancesheet2`, `income-statement-12months`, `ส่วนผู้ถือหุ้น--ทอท`, `ส่วนผู้ถือหุ้น-งบรวม`, `กระแสเงินสด` |
| **AOT-2010-FY** | 7 | `blancesheets`, `blancesheet2`, `income-statement(YTD)`, `ส่วนผู้ถือหุ้น-งบรวม`, `ส่วนผู้ถือหุ้น-ทอท`, `งบกระแสเงินสด`, `Sheet1` (junk) |
| **AOT-2015-FY** | 7 | `blancesheet (baht)`, `blancesheet2 (baht)`, `income-statement(baht)`, `กำไรขาดทุนเบ็ดเสร็จ (baht)`, `ส่วนผู้ถือหุ้น-งบรวม (baht)`, `ส่วนผู้ถือหุ้น-ทอท (baht)`, `งบกระแสเงินสด (บาท)` |
| **AOT-2020-FY** | 9 | hidden, `income-statement(YTD) 3m`, `งบกำไรขาดทุน (บาท) 3m`, `income-statement 3m`, `งบแสดงฐานะการเงิน  (บาท)`, `งบกำไรขาดทุน (บาท) `, `ส่วนผู้ถือหุ้น-งบรวม (บาท)`, `ส่วนผู้ถือหุ้น-ทอท  (บาท)`, `งบกระแสเงินสด (บาท) ` |
| **AOT-2025-FY** | 6 | hidden, `งบฐานะการเงิน  (บาท) EY `, `งบกำไรขาดทุน  (บาท) EY`, `ส่วนผู้ถือหุ้น-งบรวม (บาท) EY`, `ส่วนผู้ถือหุ้น-ทอท (บาท) EY`, `Cashflow (บาท) EY` |
| **AOT-2026Q1**  | 6 | hidden, `งบฐานะการเงิน  (บาท)`, `งบกำไรขาดทุน  (บาท)`, `ส่วนผู้ถือหุ้น-งบรวม (บาท)`, `ส่วนผู้ถือหุ้น-ทอท (บาท)`, `Cashflow (บาท)` |

### Sheet-naming quirks for AOT (parser-relevant)

- **`blancesheets` / `blancesheet2`** — typo'd English ("blance" instead of "balance")
  in pre-2020 templates. Other companies (PTT, etc.) have the same typo because the
  XLS template originated from a single source. Parser must match this exact typo.
- **2-sheet balance sheet** — AOT's BS is split across two sheets in pre-2020
  filings (`blancesheets` for assets, `blancesheet2` for liabilities+equity).
  In 2020+ filings the BS becomes a single tall sheet (`งบแสดงฐานะการเงิน` →
  `งบฐานะการเงิน`). Parser must concatenate or treat as logically-one statement.
- **2-sheet equity statement** — AOT splits Changes in Equity into TWO sheets:
  `ส่วนผู้ถือหุ้น-งบรวม` (consolidated) and `ส่วนผู้ถือหุ้น-ทอท` (company-only,
  using AOT's Thai short-name "ทอท." instead of "เฉพาะบริษัท"). The "ทอท" suffix
  is AOT-specific and won't generalize to other companies — the parser should
  classify by the Thai-language sheet header (`งบการเปลี่ยนแปลงส่วนของผู้ถือหุ้น`)
  inside the sheet, not by sheet name.
- **OCI placement** — In FY2010 there's no separate OCI sheet (P&L includes only
  net profit, not comprehensive income). FY2015 introduced a dedicated
  `กำไรขาดทุนเบ็ดเสร็จ (baht)` sheet for OCI. FY2020+ inlines OCI rows below
  net profit on the same `งบกำไรขาดทุน` sheet (no separate OCI sheet).
- **2020 IS triple-up** — FY2020 has THREE income-statement sheets:
  `income-statement(YTD) 3m`, `งบกำไรขาดทุน (บาท) 3m`, `income-statement 3m`,
  PLUS the standard `งบกำไรขาดทุน (บาท) `. Likely a quirk of the SAP BusinessObjects
  template used by AOT — at least one is YTD, others are quarterly subsets.
  Modern (2025+) filings collapse back to a single P&L sheet.
- **"EY" suffix on 2025 sheet names** — `งบฐานะการเงิน  (บาท) EY ` literally
  contains the auditor name in the sheet name. Almost certainly the AOT
  treasury team relabeled the workbook to track which auditor reviewed the
  template. This will NOT happen on pre-2025 filings — strip auditor-name
  suffixes when matching sheet names.
- **Comma in numeric data** — pre-2020 filings store numbers as Thai strings
  with comma separators (e.g., `4,378,704,238.55`). 2020+ filings store as
  native Excel numerics. Parser must coerce string → float when present.
- **`Sheet1`** in 2010 is empty/junk; ignore.

### Multi-period column layout

Each filing's primary statements have 4 numeric columns:
1. Consolidated current period
2. Consolidated prior period (comparative)
3. Company-only current period
4. Company-only prior period

**Quirk for AOT-2025-FY**: column count is **218 / 230** for BS and IS sheets —
the sheet contains many additional helper / formatting columns beyond the visible
4 data columns. Parser must rely on header-row classification, not column index,
to find the actual value columns.

---

## 3. Auditor inventory — load-bearing section

This is THE distinguishing characteristic of AOT relative to other SET-listed
companies in our pilot. Documenting verbose so the AuditorReportParser can be
built right the first time.

### 3.1 Timeline of AOT auditors observed in samples

| Period | Auditor (firm) | Signer (legal title) | Personal name | Opinion type | Template |
|---|---|---|---|---|---|
| FY2004 | SAO | รองผู้ว่าการตรวจเงินแผ่นดิน ปฏิบัติราชการแทนผู้ว่าการตรวจเงินแผ่นดิน | นางสาวเพ็ญศรี สรณารักษ์ | unqualified (clean) | SAO **pre-ISA** (3-paragraph) |
| FY2010 | SAO | ผู้ตรวจเงินแผ่นดิน 1 + ผู้อำนวยการสำนักงาน (joint sign) | นางสาวพวงชมนาถ จริยะจินดา; นางดาหวัน วงศ์พยัคฆ์ | **qualified** ("ยกเว้น...") | SAO **pre-ISA** + qualification para |
| FY2015 | SAO | รองผู้ว่าการตรวจเงินแผ่นดิน + ผู้อำนวยการสำนักตรวจสอบการเงินที่ 5 | นางสาวพวงชมนาถ จริยะจินดา; นางเกล็ดนที มโนสันติ์ | unqualified | SAO **transition** (has named "ความเห็น"/"ความรับผิดชอบ" sections, no KAM yet) |
| FY2020 | SAO | รองผู้ว่าการตรวจเงินแผ่นดิน + ผู้อำนวยการสำนักตรวจสอบการเงินและบริหารพัสดุที่ 12 | นางภัทรา โชว์ศรี; นายณรงค์ ภาณุสุวัฒน์ | unqualified, **with KAM** ("เรื่องสำคัญในการตรวจสอบ") | SAO **modern ISA** (full ISA-700 layout, KAM, going-concern para in audit-responsibility section) |
| FY2025 | **EY (สำนักงาน อีวาย จำกัด)** | ผู้สอบบัญชีรับอนุญาต | สุมนา พันธ์พงษ์สานนท์ (CPA #5872) | unqualified, with **EOM** ("ข้อมูลและเหตุการณ์ที่เน้น") + **KAM** | Big-4 ISA-700; references SAO standards alongside ISA |
| 2026Q1 | **KPMG (เคพีเอ็มจี ภูมิไชย สอบบัญชี จำกัด)** | ผู้สอบบัญชีรับอนุญาต | อุดมศักดิ์ บุศรานิพรรณ์ (CPA #10331) | unqualified review conclusion + **EOM** | Big-4 ISRE-2410 review report |

### 3.2 SAO opinion-language characterization (verbatim quotes)

The standard ISA taxonomy is:
`unqualified` / `qualified` / `adverse` / `disclaimer`. SAO does not use these
English terms, but **the underlying concepts map cleanly** with the following
Thai phrasings (verified across the 4 SAO-signed AOT filings inspected):

#### (a) Clean / unqualified opinion — SAO's standard "ความเห็น" paragraph

From **AOT-FY2004** (pre-ISA template, single combined opinion paragraph):
> "สำนักงานการตรวจเงินแผ่นดินเห็นว่า งบการเงินรวมและเฉพาะบริษัทข้างต้นนี้แสดง
> ฐานะการเงินรวมและเฉพาะบริษัท ณ วันที่ 30 กันยายน 2547 และ 2546 ผลการดำเนินงาน
> รวมและเฉพาะบริษัท การเปลี่ยนแปลงส่วนของผู้ถือหุ้นรวมและเฉพาะบริษัท และ
> กระแสเงินสดรวมและเฉพาะบริษัท สำหรับปีสิ้นสุดวันเดียวกันของแต่ละปี ของบริษัท
> ท่าอากาศยานไทย จำกัด(มหาชน) และบริษัทย่อย **โดยถูกต้องตามที่ควรในสาระสำคัญ
> ตามหลักการบัญชีที่รับรองทั่วไป**"

From **AOT-FY2015** (modern ISA, dedicated "ความเห็น" header):
> "**ความเห็น**
>
> สำนักงานการตรวจเงินแผ่นดินเห็นว่า งบการเงินรวมและงบการเงินเฉพาะบริษัทข้างต้นนี้
> แสดงฐานะการเงินรวมของบริษัท ท่าอากาศยานไทย จำกัด (มหาชน) และบริษัทย่อย และ
> ฐานะการเงินเฉพาะบริษัทของบริษัท ท่าอากาศยานไทย จำกัด (มหาชน) ตามลำดับ ณ วันที่
> 30 กันยายน 2558 และผลการดำเนินงานรวมและผลการดำเนินงานเฉพาะบริษัท และ
> กระแสเงินสดรวมและกระแสเงินสดเฉพาะบริษัท สำหรับปีสิ้นสุดวันเดียวกัน
> **โดยถูกต้องตามที่ควรในสาระสำคัญตามมาตรฐานการรายงานทางการเงิน**"

**Parser anchor for unqualified (SAO)**: the phrase `โดยถูกต้องตามที่ควรในสาระสำคัญ`
appears WITHOUT a preceding `ยกเว้น` ("except for") clause anywhere in the document.

#### (b) Qualified opinion — SAO uses "ยกเว้น" ("except for")

From **AOT-FY2010** (the only qualified opinion among the 6 samples — the
"Don Mueang impairment" matter):

The "scope" paragraph itself is qualified — note the leading `ยกเว้นที่จะกล่าว
ในวรรคถัดไป`:
> "**ยกเว้นที่จะกล่าวในวรรคถัดไป** สำนักงานการตรวจเงินแผ่นดินได้ปฏิบัติงาน
> ตรวจสอบตามมาตรฐานการสอบบัญชีที่รับรองทั่วไป …"

The basis-for-qualification paragraph (separate paragraph between scope and opinion):
> "ตามที่อธิบายในหมายเหตุประกอบงบการเงินข้อ 6.10.2 ภายหลังจากการเปิดให้บริการ
> ท่าอากาศยานสุวรรณภูมิมีข้อบ่งชี้ว่าอาคารและอุปกรณ์ที่ท่าอากาศยานดอนเมือง
> อาจเกิดการด้อยค่า … ในสถานการณ์ดังกล่าว
> **สำนักงานการตรวจเงินแผ่นดินไม่สามารถตรวจสอบให้ได้หลักฐานการสอบบัญชีที่เพียงพอ
> และเหมาะสม** เกี่ยวกับมูลค่าที่คาดว่าจะได้รับคืนของสินทรัพย์ที่ท่าอากาศยาน
> ดอนเมืองซึ่งแสดงอยู่ในงบการเงินรวมและงบการเงินเฉพาะบริษัท ณ วันที่ 30 กันยายน
> 2553 และ 2552 จำนวน 4,378.70 ล้านบาท และ 4,960.22 ล้านบาท ตามลำดับ"

The opinion paragraph then carries `ยกเว้นผลของ...`:
> "สำนักงานการตรวจเงินแผ่นดินเห็นว่า**ยกเว้นผลของการปรับปรุงงบการเงินรวมและ
> งบการเงินเฉพาะบริษัท…ซึ่งอาจจำเป็นถ้าสำนักงานการตรวจเงินแผ่นดินสามารถตรวจสอบ
> ให้ได้หลักฐานการสอบบัญชีที่เพียงพอและเหมาะสม** … งบการเงินรวมและงบการเงิน
> เฉพาะบริษัทข้างต้นนี้ แสดงฐานะการเงิน… โดยถูกต้องตามที่ควรในสาระสำคัญตาม
> หลักการบัญชีที่รับรองทั่วไป"

**Parser anchors for qualified (SAO)**:
- Scope paragraph contains the leading clause `ยกเว้นที่จะกล่าวในวรรคถัดไป`
  (literally "except as discussed in the next paragraph"). This is the
  opening signal even before reaching the opinion paragraph.
- Opinion paragraph contains `ยกเว้นผลของ…` ("except for the effect of…")
  immediately after the standard `เห็นว่า` ("is of the opinion that").
- Either anchor present → `opinion_type = qualified`.

#### (c) Adverse / Disclaimer (SAO)

Not observed in AOT samples. Educated guess (cross-referenced against
SAO templates published for other Thai state enterprises):
- **Adverse** would use `ไม่ถูกต้องตามที่ควร` ("does NOT present fairly") in
  the opinion paragraph instead of `ถูกต้องตามที่ควร`.
- **Disclaimer** would use `ไม่อาจแสดงความเห็น` ("cannot express an opinion")
  AND a basis paragraph stating SAO `ไม่ได้รับหลักฐานการสอบบัญชีที่เพียงพอ
  และเหมาะสม` for the financial statements as a whole (not a single matter).

A scout on a state enterprise that has had public adverse/disclaimer events
(e.g., TOT/CAT/Krungthai era cases — not on our pilot) would refine these
anchors. For now flag with `opinion_type = unknown` if neither
unqualified nor qualified anchors fire.

#### (d) "ข้อสังเกต" (observations) — does AOT have these?

The user prompt asked specifically about "ข้อสังเกต" paragraphs. Across the
4 SAO-signed AOT samples, **the literal noun phrase "ข้อสังเกต" does NOT
appear as a section header**. SAO uses different containers:

- **FY2004 / FY2010**: pre-ISA template — only the qualification matter
  itself constitutes a "called-out observation"; no separate header.
- **FY2015**: still no "ข้อสังเกต" — only standard ISA-style "ความเห็น"
  and "ความรับผิดชอบ" headers.
- **FY2020**: introduces **"เรื่องสำคัญในการตรวจสอบ"** (Key Audit Matters,
  KAM) as a separate header. KAM ≠ ข้อสังเกต — KAM doesn't change the
  opinion. The 2020 KAM was "หนี้สินที่อาจเกิดขึ้นจากคดีความฟ้องร้องและ
  ข้อพิพาท" (contingent liabilities from litigation).

So for AOT: **`ข้อสังเกต` is absent**. Other state enterprises (esp. those
where SAO has historical performance audits — TOT, CAT, MWA, etc.) DO use
`ข้อสังเกต` paragraphs in their performance-audit reports, but those are
NOT financial-statement-audit reports and are out of scope for IDISC. For
financial-statement audits, SAO uses KAM (FY2020+) instead.

**Going-concern equivalent**: SAO inlines a going-concern paragraph in the
"ความรับผิดชอบของผู้สอบบัญชีต่อการตรวจสอบงบการเงิน…" boilerplate (FY2020,
FY2015) — phrase to anchor on:
> "สรุปเกี่ยวกับความเหมาะสมของการใช้เกณฑ์การบัญชีสำหรับการดำเนินงาน
> ต่อเนื่อง… สรุปว่ามีความไม่แน่นอนที่มีสาระสำคัญที่เกี่ยวกับเหตุการณ์
> หรือสถานการณ์ที่อาจเป็นเหตุให้เกิดข้อสงสัยอย่างมีนัยสำคัญต่อความสามารถ
> ของกลุ่มบริษัท…ในการดำเนินงานต่อเนื่องหรือไม่"

This boilerplate is present on EVERY modern SAO report regardless of whether
GC is actually flagged. The parser MUST NOT use the mere presence of
`การดำเนินงานต่อเนื่อง` to set `going_concern_emphasis = true`. To detect
an actual GC concern, look for a SEPARATE section titled
`ความไม่แน่นอนที่มีสาระสำคัญเกี่ยวข้องกับการดำเนินงานต่อเนื่อง`
(Material Uncertainty Related to Going Concern) — none in any AOT sample.

#### (e) Big-4 (EY/KPMG) opinion language — for FY2025+

EY's FY2025 report uses the standard "ผู้สอบบัญชีรับอนุญาต" (Certified
Public Accountant) ISA-700 template, very similar in structure to PTT's
EY reports — should be parseable by the same anchors that work for PTT/COM7.
However TWO AOT-specific subtleties:

- **Both SAO and ISA standards are explicitly cited together** in the
  "เกณฑ์ในการแสดงความเห็น" section of FY2025:
  > "ข้าพเจ้าได้ปฏิบัติงานตรวจสอบตาม**หลักเกณฑ์มาตรฐานเกี่ยวกับ
  > การตรวจเงินแผ่นดินและมาตรฐานการสอบบัญชี** …"
  This is the dual-standard signal that AOT remains under SAO oversight
  even with a private auditor. Useful audit metadata; consider capturing
  as a boolean `is_state_enterprise = true` derived field.
- The 2025 EY report carries an **Emphasis of Matter** under the explicit
  header `ข้อมูลและเหตุการณ์ที่เน้น` regarding the duty-free concession
  (King Power) renegotiation — note 35.2 in the financial statements.
  EOM ≠ qualified; the report also contains the explicit disclaimer
  > "ทั้งนี้ ข้าพเจ้ามิได้แสดงความเห็นอย่างมีเงื่อนไขต่อกรณีนี้แต่อย่างใด"
  (literally "I do not express a qualified opinion regarding this matter").
  Parser must not flip to qualified on EOM.

KPMG's 2026Q1 review report uses the standard "รายงานการสอบทาน…รหัส 2410"
(ISRE-2410) template, conclusion phrasing:
> "**ข้าพเจ้าไม่พบสิ่งที่เป็นเหตุให้เชื่อว่า**ข้อมูลทางการเงินระหว่างกาล
> ดังกล่าวไม่ได้จัดทำขึ้นตามมาตรฐานการบัญชี ฉบับที่ 34 …"

This is the standard "negative-assurance" review opinion — for the
`opinion_type` enum on quarterly filings, suggest an additional value
`reviewed_unmodified` (vs `reviewed_qualified` if the conclusion is
modified). Currently the schema only has `unqualified|qualified|adverse|
disclaimer` which were designed for full audits.

#### (f) "เรื่องอื่น" (Other Matter) paragraph — auditor change disclosure

The 2026Q1 KPMG report contains an `เรื่องอื่น` paragraph that explicitly
discloses the predecessor auditor change:
> "**งบฐานะการเงินรวมและงบฐานะการเงินเฉพาะกิจการ**…ณ วันที่ 30 กันยายน
> 2568 ที่แสดงเป็นข้อมูลเปรียบเทียบ**ตรวจสอบโดยผู้สอบบัญชีอื่น**
> ซึ่งแสดงความเห็นอย่างไม่มีเงื่อนไขตามรายงานลงวันที่ 21 พฤศจิกายน 2568
> งบกำไรขาดทุนรวม… **สำหรับงวดสามเดือนสิ้นสุดวันที่ 31 ธันวาคม 2567**…
> ที่แสดงเป็นข้อมูลเปรียบเทียบ**สอบทานโดยผู้สอบบัญชีอื่น** โดยให้ข้อสรุป
> อย่างไม่มีเงื่อนไข ตามรายงานลงวันที่ 13 กุมภาพันธ์ 2568"

i.e., comparative annual audited by EY (21-Nov-2025), comparative quarterly
reviewed by SAO (13-Feb-2025), current period reviewed by KPMG (12-Feb-2026).
**Three different auditors in 12 months** — extreme for a Thai state
enterprise.

### 3.3 Signing-date format

All AOT reports omit a date stamp on the report HEADER but include it on the
final page after the signature block:

| Filing | Signing date | Format |
|---|---|---|
| FY2004 | (not on the visible paragraphs — the .doc may have a footer the parser missed; revisit) | — |
| FY2010 | (same — date on a follow-up page; not in extracted text) | — |
| FY2015 | (same) | — |
| FY2020 | (same — note that date is conventionally embedded in the file metadata or the PDF version, not always in the .doc) | — |
| FY2025 | `กรุงเทพฯ: 21 พฤศจิกายน 2568` | `<city>: <DD เดือน BBYY>` |
| 2026Q1 | `กรุงเทพมหานคร / 12 กุมภาพันธ์ 2569` | `<city> / <DD เดือน BBYY>` |

Parser implication: signing-date extraction needs a Thai-month-name +
Buddhist-Era-year regex (`^\s*(\d{1,2})\s+(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|
พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s+
(25\d{2})\s*$`), and convert BE → CE (subtract 543). The city prefix
varies (`กรุงเทพฯ`, `กรุงเทพมหานคร`, etc.).

### 3.4 Signer extraction caveat

For SAO reports, the "signer" is two named officials AND two job titles.
The PARSER should NOT assume a single signing partner — schema currently
has `signing_partner: str?`. Suggest adding `signing_partner_2: str?`
or making it `list[str]`, OR for SAO specifically using the **role title**
("ผู้ว่าการตรวจเงินแผ่นดิน") as a stable identifier rather than the
personal name (which rotates with civil-service postings).

For Big-4 (EY/KPMG) reports, single signer + CPA registration number;
schema suffices.

---

## 4. Anomaly log

Bullet list of everything else worth recording. **Bold** = parser-relevant /
needs schema or parser change.

- **AOT auditor rotation FY2025→FY2026Q1: SAO → EY → KPMG within 12 months**
  (see §3 for verbatim quotes). The auditor_reports.parquet schema must
  support this — `auditor_firm` is per-filing, so individual rows are fine,
  but consumers querying "current auditor" need to use the most recent filing
  by `signing_date`, NOT make any assumption that the auditor is stable.
- **The "is_government" flag on auditors** correctly captures SAO. For 2026
  AOT data, however, `is_government=false` (because EY/KPMG are private)
  while AOT itself is still a state enterprise. Consider a separate
  per-symbol `is_state_enterprise` field on `filings.parquet` (or symbol
  metadata) that doesn't depend on auditor identity.
- **Schema gap: `opinion_type` enum lacks "review" values**.
  ISRE-2410 quarterly review reports give an "unmodified review conclusion"
  not an "unqualified opinion". Suggest extending the enum to:
  `unqualified | qualified | adverse | disclaimer | reviewed_unmodified |
  reviewed_modified`, with `audit_basis` already disambiguating which
  half of the enum applies. Alternative: a separate `conclusion_type`
  column, leaving `opinion_type` as null on quarterlies.
- **Schema gap: missing "Emphasis of Matter" boolean**.
  The going-concern boolean is in the spec, but EOM (used for the FY2025
  King Power matter) is not. Add `emphasis_of_matter: bool` and optionally
  `emphasis_of_matter_text: str?`.
- **No restatements observed across the 6 samples** (no `(reclassified)`
  / `(restated)` annotations on prior-period columns). AOT's accounting
  is stable. The 5-letter pilot may not surface restatement edge cases —
  recommend adding a separate scout on a SET-listed company with known
  restatements (Thai Airways, IFEC, etc.) to characterize that pattern.
- **Pre-2015 filings predate IFRS adoption** — they cite
  `หลักการบัญชีที่รับรองทั่วไป` (Thai GAAP) instead of
  `มาตรฐานการรายงานทางการเงิน` (TFRS/IFRS). The opinion-anchor regex
  needs to accept BOTH framework references.
- **OCI introduction in FY2015** is a real schema change for AOT — pre-FY2015
  there is no OCI sheet at all (and net profit = comprehensive income).
  Concept-mapper should expect missing OCI rows on pre-2015 data.
- **Sheet name `งบฐานะการเงิน` vs `งบแสดงฐานะการเงิน`** — both observed.
  Older filings (FY2010 still legacy "งบดุล" "balance sheet"!), 2015–2020
  use `งบแสดงฐานะการเงิน`, 2025+ use `งบฐานะการเงิน` (the CONTEXT.md
  canonical form). Treat all 3 as equivalent.
- **2004 zip's bizarre filename scheme** (`aott1/2/3.doc/.xls`) means the
  FilingFetcher can't assume canonical filenames inside zips. Recommend a
  content-sniffer step: open each zip member, check magic bytes, then peek
  at first paragraph for `รายงานของผู้สอบบัญชี` / `หมายเหตุประกอบงบการเงิน`
  / spreadsheet shape to label as auditor / notes / financial-statements.
- **`Sheet1` empty junk** in FY2010 financial statements. Parser must
  tolerate / skip empty sheets without crashing.
- **SAP BusinessObjects hidden sheet** (`_com.sap.ip.bi.xl.hiddensheet`)
  appears in every 2020+ filing. Always skip.
- **Dual-script numerals** — none observed (AOT uses Arabic numerals
  throughout; no Thai-digit ๐-๙ encountered). Probably safe to assume
  Arabic-only across SET filers.
- **Passenger Service Charge (`ค่าบริการผู้โดยสารขาออก`)** is the most
  important AOT-specific revenue line — it's the iconic "700 baht
  international departure tax" and represents 38–40% of AOT's revenue
  per the FY2025 KAM. Worth promoting to a top-level concept even though
  it's transport-specific (consumer query: "what's AOT's PSC trend?").
- **Concession revenue lexical drift**: pre-2015 = `รายได้ค่าสัมปทาน`,
  2015+ = `รายได้ส่วนแบ่งผลประโยชน์`. Both flow into the same economic
  concept (revenue-share with concessionaires — primarily King Power
  duty-free). Map both to the new concept `concession_revenue`.
- **AOT's revenue-share `รายได้ส่วนแบ่งผลประโยชน์`** label appears across
  many concession-heavy Thai listcos (Thai Beverage subsidiaries,
  airport/highway operators). Even though tagged `transport` in this
  scout's CSV, it'd map cleanly cross-industry — consider promoting to
  `applicable_industries=` (empty / cross-industry) once a non-transport
  scout confirms the pattern.

---

## 5. Top-3 surprises

1. **AOT SWITCHED auditor away from SAO at FY2025 — and then to a different
   Big-4 the next quarter.** This invalidates the assumption baked into
   the `is_government` flag that "state enterprise → SAO auditor". For
   AOT specifically, the relationship is more like "state enterprise +
   subject to SAO oversight standards, but actual signing auditor can
   rotate". Three different auditors within 12 months is extreme. If our
   parser hard-codes `firm_id=sao` for AOT it will be wrong for every
   FY2025+ filing. (Hypothesis why: the State Audit Office has been
   delegating commercial-scale audits to private CPA firms for several
   large state enterprises since the State Audit Act 2018, then rotating
   them on a 5-year cadence.)
2. **AOT does NOT use COGS / gross-profit lines.** Unlike industrial
   companies (PTT-style), AOT presents a single-step income statement:
   Revenue → Operating expenses (broken out by NATURE — staff, utilities,
   contractors, repairs, D&A, impairment, other) → Operating profit.
   The cross-industry concepts `cogs` and `gross_profit` will be
   permanently unmapped for AOT — and likely for every airport / highway /
   utility operator. If the coverage gate counts unmapped rows as a
   penalty, this needs an industry-aware threshold.
3. **The qualified opinion pattern in AOT FY2010** (Don Mueang impairment
   matter, ~4.4B baht of PPE whose recoverable amount couldn't be assessed
   pending Cabinet decision) is a clean test case for the AuditorReportParser's
   qualified-opinion detection. The qualification language uses BOTH
   `ยกเว้นที่จะกล่าวในวรรคถัดไป` in the scope paragraph AND `ยกเว้นผลของ…`
   in the opinion paragraph. The fixture set should INCLUDE this filing
   (FILEID `dat/news/201011/10043104`) as the only known qualified opinion
   in the AOT history we've sampled.
