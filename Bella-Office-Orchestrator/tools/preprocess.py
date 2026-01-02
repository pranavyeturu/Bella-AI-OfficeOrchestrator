import pandas as pd, streamlit as st
from tools import db_tools, data_cleaner

def run_uploaded(file, logger):
    df = pd.read_csv(file)
    url, md5 = data_cleaner.process_df(df, "clean_upload.csv")
    logger(f"✅ Clean CSV ready → {url}\n\nMD5: `{md5}`")

def run_db(table: str, where: str | None, logger):
    logger("⏳ Querying Postgres…")
    df = db_tools.fetch_table_as_df(table, where)
    logger(f"🔍 {len(df):,} rows fetched")
    url, md5 = data_cleaner.process_df(df, f"{table.replace('.','_')}_clean.csv")
    logger(f"✅ Clean CSV saved → {url}\n\nMD5: `{md5}`")
