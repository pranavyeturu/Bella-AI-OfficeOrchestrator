from tools import okta_bot, slack_bot, jira_bot

DEPARTMENTS = ["IT", "Security", "Facilities", "HR"]

def run(email: str, log):
    """
    Off-boarding workflow, keyed only on email.
    log → callback (e.g. st.write) for streaming updates.
    """
    log(":hourglass: Starting off-boarding…")

    # 1) Deactivate in Okta
    uid = okta_bot.deactivate_user(email)
    log(f"✅ **Okta**: deactivated user `{uid}`")

    # 2) Announce exit in Slack
    ts = slack_bot.post_exit_message(email)
    log(f"✅ **Slack**: exit message posted (ts={ts})")

    # 3) De-provision tasks in Jira
    for dept in DEPARTMENTS:
        summary = f"{dept}: De-provision resources for {email}"
        issue = jira_bot.create_and_close_task(dept, summary)
        log(f"✅ **Jira** {issue} ({dept}) created → Done")

    log(":tada: **Off-boarding complete!**")
