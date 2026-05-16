"""
This module provides the `Stock` class, which serves as the main API for accessing individual Thai stock fundamental data.
"""

import re
import warnings
from typing import Any, Literal

import arrow
import pandas as pd

from thaifin.data import DatasetClient, get_data_revision
from thaifin.sources.finnomena.model import QuarterFinancialSheetDatum
from thaifin.sources.thai_securities_data.models import SecurityData
from thaifin.sources.finnomena import FinnomenaService
from thaifin.sources.thai_securities_data import ThaiSecuritiesDataService


# Sentinel that lets us tell "user passed source=..." from "user omitted it".
# Using object() (not None) so users can still pass None explicitly if they ever
# want the default-with-warning behavior.
_DEFAULT_SOURCE: Any = object()


_PERIOD_RE = re.compile(r"^(\d{4})(?:Q([1-3]))?$")

# Flow concepts (IS/CF) need standalone-quarter derivation from YTD-as-stored;
# stock concepts (BS/EQ) are point-in-time snapshots and have no Q4 column
# (Thai SEC IDISC publishes no Q4 filing). See docs/adr/0002.
_FLOW_STATEMENTS = frozenset({"IS", "CF"})
_FLOW_PERIOD_TYPES = ("Q1", "Q2", "Q3", "Q4", "FY")
_STOCK_PERIOD_TYPES = ("Q1", "Q2", "Q3", "FY")
_PERIOD_TYPE_ORDER = {pt: i for i, pt in enumerate(_FLOW_PERIOD_TYPES)}


def _parse_period(period: str) -> tuple[int, str]:
    """Parse a raw ``period`` value into ``(year, raw_period_type)``.

    ``"YYYY"`` → ``(YYYY, "FY")``; ``"YYYYQq"`` → ``(YYYY, "Q{q}_YTD")``
    for ``q ∈ {1, 2, 3}``. The ``_YTD`` suffix is an internal column tag
    on the pivot intermediate — the consumer-facing frame renames Q1..Q3
    to standalone names after derivation.
    """
    m = _PERIOD_RE.match(period)
    if m is None:
        raise ValueError(f"unrecognised period: {period!r}")
    year = int(m.group(1))
    q = m.group(2)
    return year, "FY" if q is None else f"Q{q}_YTD"


_RAW_FLOW_COLS = ["Q1_YTD", "Q2_YTD", "Q3_YTD", "FY"]
_RAW_STOCK_COLS = ["Q1_YTD", "Q2_YTD", "Q3_YTD", "FY"]
_STOCK_RENAME = {"Q1_YTD": "Q1", "Q2_YTD": "Q2", "Q3_YTD": "Q3", "FY": "FY"}


def _derive_flow_standalones(wide: pd.DataFrame) -> pd.DataFrame:
    """Convert a ``(concept, period_type_raw)`` pivot into standalone-Q columns.

    ``wide`` has whatever subset of ``{Q1_YTD, Q2_YTD, Q3_YTD, FY}`` was
    present in the data for each concept. The output has all five
    standalone columns ``Q1, Q2, Q3, Q4, FY`` per concept; missing
    inputs propagate as ``NaN``.
    """
    concepts = wide.columns.get_level_values(0).unique()
    out_frames = []
    for concept in concepts:
        sub = wide[concept].reindex(columns=_RAW_FLOW_COLS)
        q1, q2, q3, fy = sub["Q1_YTD"], sub["Q2_YTD"], sub["Q3_YTD"], sub["FY"]
        standalone = pd.DataFrame(
            {
                "Q1": q1,
                "Q2": q2 - q1,
                "Q3": q3 - q2,
                "Q4": fy - q3,
                "FY": fy,
            },
            index=wide.index,
        )
        standalone.columns = pd.MultiIndex.from_product(
            [[concept], standalone.columns]
        )
        out_frames.append(standalone)
    return pd.concat(out_frames, axis=1)


def _rename_stock_columns(wide: pd.DataFrame) -> pd.DataFrame:
    """Drop the ``_YTD`` suffix on stock-statement columns; no Q4 emitted.

    Each cell is already a point-in-time snapshot at period end — no
    derivation is needed. Q4 has no source (no Q4 filing) and is omitted
    by construction.
    """
    concepts = wide.columns.get_level_values(0).unique()
    out_frames = []
    for concept in concepts:
        sub = wide[concept].reindex(columns=_RAW_STOCK_COLS)
        renamed = sub.rename(columns=_STOCK_RENAME)
        renamed.columns = pd.MultiIndex.from_product(
            [[concept], renamed.columns]
        )
        out_frames.append(renamed)
    return pd.concat(out_frames, axis=1)


class Stock:

    def __init__(
        self,
        symbol: str,
        language: str = "en",
        source: Literal["dataset", "live"] = _DEFAULT_SOURCE,  # type: ignore[assignment]
        revision: str | None = None,
    ):
        """
        Initialize a Stock object with the given symbol and language.

        Args:
            symbol (str): The stock symbol.
            language (str): Language preference ("en" or "th"). Defaults to "en".
            source (str): Data source. ``"live"`` reaches Finnomena and
                ThaiSecuritiesData over HTTP (v1.x behavior). ``"dataset"``
                reads from the HuggingFace-hosted parquet via DuckDB streaming.
                When omitted, ``"dataset"`` is used and a ``DeprecationWarning``
                fires noting that the v3.0 default will be explicit-only. Pass
                ``source="live"`` or ``source="dataset"`` to silence.
            revision (str | None): HF dataset revision (git tag, branch, or
                sha) when ``source="dataset"``. Falls back to
                ``thaifin.get_data_revision()`` when omitted. Ignored when
                ``source="live"``.
        """
        if source is _DEFAULT_SOURCE:
            warnings.warn(
                "Stock() default source will become 'dataset' in v3.0. "
                "Pass source='live' or source='dataset' explicitly to silence.",
                DeprecationWarning,
                stacklevel=2,
            )
            source = "dataset"
        self.symbol_upper: str = symbol.upper()
        self.language: str = language
        self.source: Literal["dataset", "live"] = source
        self.revision: str | None = revision
        self.info: SecurityData = ThaiSecuritiesDataService().get_stock(self.symbol_upper, language=self.language)
        self.updated: arrow.Arrow = arrow.utcnow()

    class SafeProperty:
        """ Descriptor for safely accessing attributes with a default value.
        This allows for cleaner access to attributes that may not always be present.
        Usage:
        symbol = SafeProperty('info', 'symbol')
        company_name = SafeProperty('info', 'name')
        """
        def __init__(self, obj_attr: str, field_attr: str, default: str = '-'):
            self.obj_attr: str = obj_attr
            self.field_attr: str = field_attr
            self.default: str = default

        def __get__(self, instance, owner):
            if instance is None:
                return self
            obj: SecurityData = getattr(instance, self.obj_attr)
            value: str | None = getattr(obj, self.field_attr, None)
            return value if value else self.default

    symbol = SafeProperty('info', 'symbol')
    company_name = SafeProperty('info', 'name')
    industry = SafeProperty('info', 'industry')
    sector = SafeProperty('info', 'sector')
    market = SafeProperty('info', 'market')
    address = SafeProperty('info', 'address')
    website = SafeProperty('info', 'web')

    @property
    def quarter_dataframe(self) -> pd.DataFrame:
        """
        The quarterly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing quarterly financial data.
        """
        fundamental: list[QuarterFinancialSheetDatum] | list[dict] = FinnomenaService().get_financial_sheet(self.symbol_upper, language=self.language)
        if not fundamental:
            raise ValueError(f"No financial sheet data available for stock {self.symbol_upper}.")
        
        if self.language == 'th' and isinstance(fundamental[0], dict):
            # Handle Thai data (list of dicts)
            df: pd.DataFrame = pd.DataFrame(fundamental)

            # Remove security_id column if it exists
            security_id_col = 'รหัสหลักทรัพย์'
            if security_id_col in df.columns:
                df = df.drop(columns=[security_id_col])

        else:
            # For English, fundamental is a list of QuarterFinancialSheetDatum
            # Convert all to dicts excluding security_id
            dicts:list[dict] = []
            for item in fundamental:
                if isinstance(item, QuarterFinancialSheetDatum):
                    dicts.append(item.model_dump(exclude={"security_id"}))
                elif isinstance(item, dict):
                    dicts.append({k: v for k, v in item.items() if k != 'security_id'})
            df = pd.DataFrame(dicts)
                    
        
        # Quarter 9 means yearly values - filter for quarterly data only
        quarter_col:str = 'ไตรมาส' if self.language == 'th' else 'quarter'
        fiscal_col:str = 'ปีการเงิน' if self.language == 'th' else 'fiscal'
        df = df[df[quarter_col] != 9]

        if self.language == 'th':
            df["ช่วงเวลา"] = df[fiscal_col].astype(str) + "Q" + df[quarter_col].astype(str)
            df = df.set_index("ช่วงเวลา")
        else:
            df["time"] = df[fiscal_col].astype(str) + "Q" + df[quarter_col].astype(str)
            df = df.set_index("time")
            
        df.index = pd.to_datetime(df.index).to_period("Q")
        df = df.drop(columns=[fiscal_col, quarter_col])
        return df

    @property
    def yearly_dataframe(self) -> pd.DataFrame:
        """
        The yearly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing yearly financial data.
        """
        fundamental:list[QuarterFinancialSheetDatum] | list[dict] = FinnomenaService().get_financial_sheet(self.symbol_upper, language=self.language)
        if self.language == 'th' and isinstance(fundamental[0], dict):
            # Handle Thai data (list of dicts)
            df:pd.DataFrame = pd.DataFrame(fundamental)
            # Remove security_id column if it exists
            security_id_col = 'รหัสหลักทรัพย์'
            if security_id_col in df.columns:
                df = df.drop(columns=[security_id_col])
        else:
            # For English, fundamental is a list of QuarterFinancialSheetDatum
            # Convert all to dicts excluding security_id
            dicts:list[dict] = []
            for item in fundamental:
                if isinstance(item, QuarterFinancialSheetDatum):
                    dicts.append(item.model_dump(exclude={"security_id"}))
                elif isinstance(item, dict):
                    dicts.append({k: v for k, v in item.items() if k != 'security_id'})
            df = pd.DataFrame(dicts)
        # Quarter 9 means yearly values - filter for yearly data only
        quarter_col:str = 'ไตรมาส' if self.language == 'th' else 'quarter'
        fiscal_col:str = 'ปีการเงิน' if self.language == 'th' else 'fiscal'
        df = df[df[quarter_col] == 9]
        df = df.set_index(fiscal_col)
        df.index = pd.to_datetime(df.index, format="%Y").to_period("Y")
        df = df.drop(columns=[quarter_col])
        return df

    # --- v2 dataset-only statement / report properties ----------------------
    #
    # All five raise NotImplementedError under source="live" — they require
    # a tagged-long ``financial_lines`` table or its DOC/DOCX siblings, none
    # of which the v1.x Finnomena/ThaiSecuritiesData live sources expose.
    # Revision resolution mirrors ``.capex`` above:
    # ``self.revision -> get_data_revision() -> "main"``.

    def _ensure_dataset_source(self, prop_name: str) -> str:
        if self.source != "dataset":
            raise NotImplementedError(
                f"Stock.{prop_name} is only available with source='dataset'. "
                "Pass source='dataset' (and revision='...') to Stock(...)."
            )
        return self.revision or get_data_revision()

    def _statement_dataframe(self, statement: str) -> pd.DataFrame:
        """Wide statement DataFrame indexed by fiscal year.

        Rows are ``PeriodIndex(freq='Y')``; columns are a ``MultiIndex`` of
        ``(concept, period_type)``.

        For **flow** statements (``IS``, ``CF``), ``period_type`` is one of
        ``{Q1, Q2, Q3, Q4, FY}`` with ``Q1..Q4`` as standalone-quarter
        values derived from the YTD-as-stored raw filings:
        ``Q1 = Q1_YTD``, ``Q2 = Q2_YTD − Q1_YTD``,
        ``Q3 = Q3_YTD − Q2_YTD``, ``Q4 = FY − Q3_YTD``. ``Q1..Q3`` are
        reviewed-basis, ``Q4`` is mixed-basis (audited FY − reviewed
        Q3-YTD), ``FY`` is audited.

        For **stock** statements (``BS``, ``EQ``), ``period_type`` is one
        of ``{Q1, Q2, Q3, FY}`` — each cell is a per-filing point-in-time
        snapshot. There is no ``Q4`` column because Thai SEC IDISC
        publishes no Q4 filing; the audited annual is the year-end
        snapshot. ``Q1..Q3`` are reviewed; ``FY`` is audited.

        Missing inputs propagate as ``NaN`` — no gap-filling. See
        ``docs/adr/0002`` for the design rationale.
        """
        revision = self._ensure_dataset_source(f"{statement.lower()}_statement")
        client = DatasetClient()
        df = client.query(
            "SELECT period, concept, value "
            "FROM {lines} "
            f"WHERE symbol = '{self.symbol_upper}' "
            f"AND statement = '{statement}' "
            "AND consolidation = 'consolidated' "
            "AND concept IS NOT NULL "
            "ORDER BY period",
            revision=revision,
        )
        if df.empty:
            return pd.DataFrame()

        parsed = df["period"].map(_parse_period)
        df = df.assign(
            _year=parsed.map(lambda t: t[0]),
            _period_type_raw=parsed.map(lambda t: t[1]),
        )

        wide = df.pivot_table(
            index="_year",
            columns=["concept", "_period_type_raw"],
            values="value",
            aggfunc="first",
        )

        result = (
            _derive_flow_standalones(wide)
            if statement in _FLOW_STATEMENTS
            else _rename_stock_columns(wide)
        )

        result.index = pd.PeriodIndex(result.index, freq="Y")
        result.index.name = "year"

        sorted_cols = sorted(
            result.columns,
            key=lambda t: (t[0], _PERIOD_TYPE_ORDER[t[1]]),
        )
        return result.reindex(
            columns=pd.MultiIndex.from_tuples(
                sorted_cols, names=["concept", "period_type"]
            )
        )

    @property
    def income_statement(self) -> pd.DataFrame:
        """Wide IS table: rows = fiscal year, columns = ``(concept, {Q1,Q2,Q3,Q4,FY})``.

        Flow concepts. ``Q1..Q4`` are standalone-quarter values; ``FY`` is
        the audited annual. See :meth:`_statement_dataframe` for details.
        """
        return self._statement_dataframe("IS")

    @property
    def balance_sheet(self) -> pd.DataFrame:
        """Wide BS table: rows = fiscal year, columns = ``(concept, {Q1,Q2,Q3,FY})``.

        Stock concepts (point-in-time snapshots). No ``Q4`` column —
        IDISC publishes no Q4 filing; the audited annual is the year-end
        snapshot. See :meth:`_statement_dataframe` for details.
        """
        return self._statement_dataframe("BS")

    @property
    def cash_flow_statement(self) -> pd.DataFrame:
        """Wide CF table: rows = fiscal year, columns = ``(concept, {Q1,Q2,Q3,Q4,FY})``.

        Flow concepts. ``Q1..Q4`` are standalone-quarter values; ``FY`` is
        the audited annual. See :meth:`_statement_dataframe` for details.
        """
        return self._statement_dataframe("CF")

    @property
    def capex(self) -> pd.Series:
        """Capital expenditure series (PRD #11 headline metric).

        Convenience accessor: returns the ``(capex, FY)`` annual time
        series from :attr:`cash_flow_statement` as a flat
        ``pd.Series`` indexed by fiscal year. For quarter-level values,
        use ``self.cash_flow_statement[('capex', q)]`` directly
        (``q`` in ``{'Q1','Q2','Q3','Q4','FY'}``).
        """
        cf = self.cash_flow_statement
        if ("capex", "FY") not in cf.columns:
            return pd.Series(dtype="float64", name="capex")
        return cf[("capex", "FY")].rename("capex")

    @property
    def notes(self) -> pd.DataFrame:
        """Notes markdown keyed by ``period``.

        Reads ``notes_text.parquet`` directly from HF (the default
        ``DatasetClient`` query path resolves ``financial_lines.parquet``
        only — for sibling tables we construct the URL inline).
        """
        revision = self._ensure_dataset_source("notes")
        url = (
            f"https://huggingface.co/datasets/ninyawee/thaifin-financials"
            f"/resolve/{revision}/notes_text.parquet"
        )
        client = DatasetClient(parquet_url=url)
        return client.query(
            "SELECT period, filing_id, raw_text_md FROM {lines} "
            f"WHERE symbol = '{self.symbol_upper}' "
            "ORDER BY period"
        ).set_index("period")

    @property
    def auditor_report(self) -> pd.DataFrame:
        """Auditor-report rows keyed by ``period``."""
        revision = self._ensure_dataset_source("auditor_report")
        url = (
            f"https://huggingface.co/datasets/ninyawee/thaifin-financials"
            f"/resolve/{revision}/auditor_reports.parquet"
        )
        client = DatasetClient(parquet_url=url)
        return client.query(
            "SELECT period, filing_id, audit_basis, opinion_type, "
            "going_concern_emphasis, auditor_firm, signing_date, "
            "signing_partner, raw_text_md FROM {lines} "
            f"WHERE symbol = '{self.symbol_upper}' "
            "ORDER BY period"
        ).set_index("period")

    def __repr__(self) -> str:
        """
        String representation of the Stock object.

        Returns:
            str: A string representation showing the stock symbol and last update time.
        """
        return f'<Stock "{self.symbol}" - updated {self.updated.humanize()}>'
    
if __name__ == "__main__":
    # Example usage - English (default)
    stock_en = Stock("ptt")
    print("=== English Version ===")
    print("Symbol:", stock_en.symbol)
    print("Company Name:", stock_en.company_name)
    print("Industry:", stock_en.industry)
    print("Sector:", stock_en.sector)
    print("Market:", stock_en.market)
    print()
    
    # Example usage - Thai
    stock_th = Stock("ptt", language="th")
    print("=== Thai Version ===")
    print("ชื่อหุ้น:", stock_th.symbol)
    print("ชื่อบริษัท:", stock_th.company_name)
    print("อุตสาหกรรม:", stock_th.industry)
    print("กลุ่มอุตสาหกรรม:", stock_th.sector)
    print("ตลาดหลักทรัพย์:", stock_th.market)
    print()
    
    # Financial data examples
    print("=== English Financial Data ===")
    print("Quarter DataFrame (English):")
    print(stock_en.quarter_dataframe.head())
    print()
    print("Yearly DataFrame (English):")
    print(stock_en.yearly_dataframe.head())
    print()
    
    print("=== Thai Financial Data ===")
    print("Quarter DataFrame (Thai):")
    print(stock_th.quarter_dataframe.head())
    print()
    print("Yearly DataFrame (Thai):")
    print(stock_th.yearly_dataframe.head())
