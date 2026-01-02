# scheduler/cron_tasks.py
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from slack_handlers.tasks import send_laggard_reminders
from report.report_generator import compile_and_send_weekly_report

def start_cron_jobs():
    sched = BackgroundScheduler()
    sched.add_job(lambda: asyncio.create_task(send_laggard_reminders()),
                  'cron', day_of_week='mon-fri', hour=16, minute=0)
    sched.add_job(compile_and_send_weekly_report,
                  'cron', day_of_week='fri',    hour=17, minute=0)
    sched.start()
