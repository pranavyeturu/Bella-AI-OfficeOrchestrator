import streamlit as st
from tools import db_admin

def run(logger, table_name: str = None):
    """
    DB refresh workflow.
    If table_name is None, the entire DB schema is wiped and reseeded.
    If table_name is provided, only that table is dropped and reseeded.
    """
    # 1) Snapshot
    snapshot_path, sha = db_admin.snapshot_db()
    logger(f"✅ Snapshot saved → {snapshot_path}\nSHA256: `{sha}`")

    # 2) Approval
    if table_name:
        prompt = f"⚠️ APPROVE wiping & restoring table `{table_name}`"
    else:
        prompt = "⚠️ APPROVE wiping & restoring the entire database"

    if not st.button(prompt):
        logger("Waiting for approval…")
        return

    # 3) Wipe
    if table_name:
        logger(f"🧨 Dropping table `{table_name}`…")
        db_admin.drop_table(table_name)
    else:
        logger("🧨 Dropping and recreating public schema…")
        db_admin.wipe_db()

    # 4) Restore
    if table_name:
        logger(f"📥 Restoring `{table_name}` from seed…")
        db_admin.restore_table_from_seed(table_name)
        action = f"refresh_table_{table_name}"
    else:
        logger("📥 Restoring full database from seed…")
        db_admin.restore_seed()
        action = "refresh_full_database"

    # 5) Audit
    db_admin.log_audit(action=action, sha=sha, approved_by="streamlit_user")
    logger(":tada: Refresh complete & audit logged.")
