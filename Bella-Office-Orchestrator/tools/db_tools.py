import os, pandas as pd, psycopg2
from dotenv import load_dotenv
load_dotenv()


PG_CONN = psycopg2.connect(                        
    host=os.getenv("PG_HOST"),
    dbname=os.getenv("PG_DB"),
    user=os.getenv("PG_USER"),
    password=os.getenv("PG_PASSWORD"),
    port=os.getenv("PG_PORT", 5432),
)
def fetch_table_as_df(table: str, where: str | None = None) -> pd.DataFrame:
    qry = f"SELECT * FROM {table}"
    if where:
        qry += f" WHERE {where}"
    return pd.read_sql(qry, PG_CONN)

def get_table_catalog(limit: int = 200) -> str:
    """
    Return one CSV-style string listing up to <limit> tables with
    comma-separated column names & types – ideal LLM context.
    """
    sql = """
    SELECT table_schema||'.'||table_name   AS tbl,
           string_agg(column_name||' '||data_type, ', ' ORDER BY ordinal_position) AS cols
    FROM information_schema.columns
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    GROUP BY 1
    LIMIT %s;
    """
    return pd.read_sql(sql, PG_CONN, params=[limit]).to_string(index=False)
