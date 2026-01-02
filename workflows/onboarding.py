from tools import okta_bot, slack_bot, jira_bot


def run(first: str, last: str, email: str, st_write):
    """One-shot onboarding pipeline; logs to Streamlit."""
    st_write(":hourglass: Starting onboarding…")

    uid = okta_bot.create_user(email, first, last)
    st_write(f"✅ **Okta** user `{uid}` created")

    ts = slack_bot.post_welcome_message(email)
    st_write(f"✅ Slack: welcome message posted in #general (ts={ts})")
    
    for dept in ["IT", "Security", "Facilities", "HR"]:
        issue = jira_bot.create_and_close_task(
            dept, f"{dept}: Provision resources for {first} {last}"
        )
        st_write(f"✅ **Jira** {issue} ({dept}) created → Done")

    st_write(":tada: **Onboarding complete!**")
