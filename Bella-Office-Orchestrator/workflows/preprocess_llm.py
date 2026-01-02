# workflows/preprocess_llm.py

import pandas as pd
import streamlit as st
import re
from pathlib import Path

from tools import db_tools, data_cleaner
from planner import plan

def log_df_overview(df: pd.DataFrame, logger):
    """Log row/column counts, dtypes, and nulls per column."""
    logger(f"ℹ️ Initial preview: {df.shape[0]} rows × {df.shape[1]} cols")
    for col in df.columns:
        dtype = df[col].dtype
        nulls = df[col].isna().sum()
        logger(f"   • `{col}` — type: {dtype}, nulls: {nulls}")

def run_nlp(request_text: str, logger):
    """
    Orchestrate the LLM-driven preprocess workflow.
    The planner now uses a full table catalog, so no 'ask' loops are needed.
    """
    # 1) Plan the action
    decision = plan(request_text)

    # 2) CSV upload path
    if decision["mode"] == "upload":
        st.info("📤 Upload the CSV you’d like me to clean:")
        csv_file = st.file_uploader("CSV file", type=["csv"])
        if not csv_file:
            return

        df = pd.read_csv(csv_file)

        # ——— Log overview & planned cleaning steps —————————————————
        log_df_overview(df, logger)
        logger("🔄 Cleaning steps:")
        logger("   1) Drop all rows containing any null values")
        logger("   2) Standardize column names to lowercase and trim whitespace")
        date_cols = [c for c in df.columns if c.endswith("_date")]
        if date_cols:
            logger(f"   3) Convert to datetime: {', '.join(date_cols)}")
        else:
            logger("   3) No *_date columns detected")

        # ——— Run cleaning ————————————————————————————
        url, md5 = data_cleaner.process_df(df, "clean_upload.csv")

        # ——— Download button —————————————————————————
        file_path = Path(url)
        if file_path.exists():
            with open(file_path, "rb") as f:
                st.download_button(
                    label="Download Cleaned CSV",
                    data=f,
                    file_name=file_path.name,
                    mime="text/csv"
                )

        logger(f"✅ Clean CSV → {url}\nMD5: `{md5}`")
        return

    # 3) SQL query path
    sql = decision.get("sql", "").strip()
    if not sql:
        logger("❌ No SQL to run. Please refine your request.")
        return

    # NEW: strip a trailing semicolon so sub-query is valid
    sql = sql.rstrip(";")

    # show the SQL
    st.code(sql, language="sql")

    # Approval if dangerous
    if decision.get("dangerous", False):
        if not st.button("⚠️ Approve running this SQL"):
            logger("Awaiting your approval…")
            return

    logger("⏳ Executing query …")
    df = db_tools.fetch_table_as_df(f"({sql}) AS sub")
    logger(f"🔍 Fetched {df.shape[0]:,} rows × {df.shape[1]} cols")

    # ——— Log overview & planned cleaning steps —————————————————
    log_df_overview(df, logger)
    logger("🔄 Cleaning steps:")
    logger("   1) Drop all rows containing any null values")
    logger("   2) Standardize column names to lowercase and trim whitespace")
    date_cols = [c for c in df.columns if c.endswith("_date")]
    if date_cols:
        logger(f"   3) Convert to datetime: {', '.join(date_cols)}")
    else:
        logger("   3) No *_date columns detected")

    # ——— Run cleaning ————————————————————————————
    url, md5 = data_cleaner.process_df(df, "clean_from_query.csv")

    # ——— Download button —————————————————————————
    file_path = Path(url)
    if file_path.exists():
        with open(file_path, "rb") as f:
            st.download_button(
                label="Download Cleaned CSV",
                data=f,
                file_name=file_path.name,
                mime="text/csv"
            )

    logger(f"✅ Clean CSV → {url}\nMD5: `{md5}`")
