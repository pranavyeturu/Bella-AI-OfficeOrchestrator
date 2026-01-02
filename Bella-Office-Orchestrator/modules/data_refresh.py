import streamlit as st
import os
import pandas as pd
import json
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from hubspot import HubSpot
from jira import JIRA

class DataRefresh:
    def __init__(self):
        self.hubspot_api_key = os.getenv('HUBSPOT_API_KEY')
        self.jira_api_token = os.getenv('JIRA_API_TOKEN')
        self.jira_email = os.getenv('JIRA_EMAIL')
        self.jira_domain = os.getenv('JIRA_DOMAIN')
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_channel = os.getenv('SLACK_CHANNEL_ID')
        

        self.hubspot_client = None
        if self.hubspot_api_key:
            self.hubspot_client = HubSpot(access_token=self.hubspot_api_key)
        
        self.jira_client = None
        if self.jira_api_token and self.jira_email and self.jira_domain:
            self.jira_client = JIRA(
                server=f'https://{self.jira_domain}',
                basic_auth=(self.jira_email, self.jira_api_token)
            )
        
        self.slack_client = None
        if self.slack_token:
            self.slack_client = WebClient(token=self.slack_token)
       
        self.hubspot_data_file = 'data/hubspot_data.json'
        self.jira_data_file = 'data/jira_data.json'
        self.refresh_log_file = 'data/refresh_log.json'
        self.refresh_history_file = 'data/refresh_history.json'
        self.dependencies_file = 'data/dependencies.json'
        
        self.hubspot_data = {'contacts': [], 'companies': [], 'last_refresh': None}
        self.jira_data = {'issues': [], 'last_refresh': None}
        self.refresh_history = {'data_refreshes': []}
        self.dependencies = {'hubspot': [], 'jira': []}
        
       
        os.makedirs('data', exist_ok=True)
        
        self.load_data()

    def load_data(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        if os.path.exists(self.refresh_history_file):
            with open(self.refresh_history_file, 'r') as f:
                self.refresh_history = json.load(f)
        else:
            self.refresh_history = {
                'data_refreshes': [
                    {
                        'timestamp': (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'success',
                        'records_count': 150,
                        'source': 'HubSpot'
                    }
                ],
                'dependency_checks': [
                    {
                        'timestamp': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                        'updates_found': True,
                        'vulnerabilities_found': False,
                        'updates': ['pandas 2.0.0 -> 2.1.0', 'requests 2.28.0 -> 2.31.0'],
                        'vulnerabilities': []
                    }
                ]
            }
            self.save_refresh_history()
 
        if os.path.exists(self.dependencies_file):
            with open(self.dependencies_file, 'r') as f:
                self.dependencies = json.load(f)
        else:
            self.dependencies = {
                'packages': [
                    {
                        'name': 'pandas',
                        'version': '2.0.0',
                        'latest_version': '2.1.0',
                        'has_vulnerability': False
                    },
                    {
                        'name': 'requests',
                        'version': '2.28.0',
                        'latest_version': '2.31.0',
                        'has_vulnerability': False
                    },
                    {
                        'name': 'numpy',
                        'version': '1.21.0',
                        'latest_version': '1.24.0',
                        'has_vulnerability': True,
                        'vulnerability': 'CVE-2023-1234'
                    }
                ]
            }
            self.save_dependencies()
    def save_hubspot_data(self):
        def default_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
            
        with open(self.hubspot_data_file, 'w') as f:
            json.dump(self.hubspot_data, f, indent=4, default=default_converter)





    def save_refresh_history(self):
        with open(self.refresh_history_file, 'w') as f:
            json.dump(self.refresh_history, f)
    def log_refresh(self, source, record_count):
        refresh_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'success',
            'records_count': record_count,
            'source': source.capitalize()
        }
        self.refresh_history['data_refreshes'].append(refresh_entry)
        self.save_refresh_history()


    def save_dependencies(self):
        with open(self.dependencies_file, 'w') as f:
            json.dump(self.dependencies, f)

    def display_interface(self):
        st.title("Data Refresh")
        if st.button("Send HubSpot Setup Instructions"):
            self.send_hubspot_setup_link()
        with st.expander("Data Refresh", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Refresh HubSpot Data"):
                    self.refresh_hubspot_data()
            with col2:
                if st.button("Check Last Refresh"):
                    self.display_last_refresh()

        with st.expander("Dependency Check", expanded=True):
            if st.button("Check Dependencies"):
                self.check_dependencies()

        with st.expander("History", expanded=True):
            self.display_history()

        with st.expander("Add Package", expanded=True):
            package_name = st.text_input("Package Name")
            package_version = st.text_input("Current Version")
            latest_version = st.text_input("Latest Version")
            has_vulnerability = st.checkbox("Has Vulnerability")
            vulnerability_id = st.text_input("Vulnerability ID (if any)")
            
            if st.button("Add Package"):
                if package_name and package_version:
                    new_package = {
                        'name': package_name,
                        'version': package_version,
                        'latest_version': latest_version or package_version,
                        'has_vulnerability': has_vulnerability,
                        'vulnerability': vulnerability_id if has_vulnerability else None
                    }
                    self.dependencies['packages'].append(new_package)
                    self.save_dependencies()
                    st.success("Package added successfully!")
                    st.rerun()
                else:
                    st.error("Please provide package name and version")

    def refresh_hubspot_data(self):
        """Refresh HubSpot data"""
        try:
            if not self.hubspot_client:
                error_msg = "HubSpot API key not configured"
                self.notify_refresh_failure(error_msg)
                return False

            # Fetch contacts
            contacts = self.hubspot_client.crm.contacts.basic_api.get_page()
            
            # Fetch companies
            companies = self.hubspot_client.crm.companies.basic_api.get_page()
            
            # Update local data
            self.hubspot_data = {
                'contacts': [contact.to_dict() for contact in contacts.results],
                'companies': [company.to_dict() for company in companies.results],
                'last_refresh': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
            self.save_hubspot_data()
          
            self.log_refresh('hubspot', len(contacts.results) + len(companies.results))
            self.notify_refresh_success('HubSpot', len(contacts.results) + len(companies.results))
            
            return True
        except Exception as e:
            error_msg = f"Failed to refresh HubSpot data: {str(e)}"
            self.notify_refresh_failure(error_msg)
            return False

    def refresh_jira_data(self):
        """Refresh Jira data"""
        try:
            if not self.jira_client:
                error_msg = "Jira credentials not configured"
                self.notify_refresh_failure(error_msg)
                return False

            issues = self.jira_client.search_issues('project=PROJ', maxResults=1000)
            
          
            self.jira_data = {
                'issues': [issue.raw for issue in issues],
                'last_refresh': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
          
            self.save_jira_data()
            self.log_refresh('jira', len(issues))
            
            self.notify_refresh_success('Jira', len(issues))
            
            return True
        except Exception as e:
            error_msg = f"Failed to refresh Jira data: {str(e)}"
            self.notify_refresh_failure(error_msg)
            return False

    def fetch_hubspot_leads(self):
        return [
            {'id': i, 'email': f'test{i}@example.com', 'created_at': datetime.now().isoformat()}
            for i in range(1, 101)
        ]
    
    

    def check_dependencies(self):
        try:
            updates = []
            vulnerabilities = []
            
            for package in self.dependencies['packages']:
                if package['version'] != package['latest_version']:
                    updates.append(f"{package['name']} {package['version']} -> {package['latest_version']}")
                if package['has_vulnerability']:
                    vulnerabilities.append(f"{package['name']}: {package['vulnerability']}")
    
            check_record = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'updates_found': bool(updates),
                'vulnerabilities_found': bool(vulnerabilities),
                'updates': updates,
                'vulnerabilities': vulnerabilities
            }
            self.refresh_history['dependency_checks'].append(check_record)
            self.save_refresh_history()
            
            if updates or vulnerabilities:
                self.notify_dependency_issues(updates, vulnerabilities)
                st.warning("Dependency issues found. Check Slack for details.")
            else:
                st.success("All dependencies are up to date and secure")
            
        except Exception as e:
            st.error(f"Dependency check failed: {str(e)}")

    def display_last_refresh(self):
        if self.refresh_history['data_refreshes']:
            last_refresh = self.refresh_history['data_refreshes'][-1]
            st.write(f"Last refresh: {last_refresh['timestamp']}")
            st.write(f"Records processed: {last_refresh['records_count']}")
            st.write(f"Status: {last_refresh['status']}")
            st.write(f"Source: {last_refresh['source']}")
        else:
            st.write("No refresh history available")

    def display_history(self):
        st.subheader("Data Refresh History")
        if self.refresh_history['data_refreshes']:
            for refresh in reversed(self.refresh_history['data_refreshes'][-5:]):
                st.write(f"Time: {refresh['timestamp']}")
                st.write(f"Records: {refresh['records_count']}")
                st.write(f"Status: {refresh['status']}")
                st.write(f"Source: {refresh['source']}")
                st.markdown("---")
        
        st.subheader("Dependency Check History")
        if self.refresh_history['dependency_checks']:
            for check in reversed(self.refresh_history['dependency_checks'][-5:]):
                st.write(f"Time: {check['timestamp']}")
                st.write(f"Updates found: {check['updates_found']}")
                st.write(f"Vulnerabilities found: {check['vulnerabilities_found']}")
                if check['updates']:
                    st.write("Updates:")
                    for update in check['updates']:
                        st.write(f"- {update}")
                if check['vulnerabilities']:
                    st.write("Vulnerabilities:")
                    for vuln in check['vulnerabilities']:
                        st.write(f"- {vuln}")
                st.markdown("---")

    def _split_long_text(self, text, max_length=2900):
        lines = text.split('\n')
        blocks = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > max_length:
                blocks.append(current)
                current = ""
            current += line + "\n"
        if current:
            blocks.append(current)
        return blocks

    def notify_refresh_failure(self, error_msg):
        """Send notification about refresh failure to Slack, splitting long messages."""
        try:
            if not self.slack_client or not self.slack_channel:
                st.warning("Slack credentials not configured. Skipping notification.")
                return

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⚠️ Data Refresh Failed",
                        "emoji": True
                    }
                }
            ]
            for chunk in self._split_long_text(error_msg):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error Message:*\n{chunk.strip()}"
                    }
                })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Timestamp:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            })

            self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                blocks=blocks
            )
            st.error(f"Refresh failed: {error_msg}")
        except Exception as e:
            st.error(f"Failed to send Slack notification: {str(e)}")

    def notify_refresh_success(self, data_type, record_count, summary=None):
        """Send notification about successful refresh to Slack, splitting long summaries."""
        try:
            if not self.slack_client or not self.slack_channel:
                st.warning("Slack credentials not configured. Skipping notification.")
                return

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"✅ {data_type} Data Refresh Successful",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Records Updated:*\n{record_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Timestamp:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
            if summary:
                for chunk in self._split_long_text(summary):
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Summary:*\n{chunk.strip()}"
                        }
                    })

            self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                blocks=blocks
            )
            st.success(f"Successfully refreshed {data_type} data: {record_count} records updated")
        except Exception as e:
            st.error(f"Failed to send Slack notification: {str(e)}")

    def notify_dependency_issues(self, updates, vulnerabilities):
        message = "🔍 *Dependency Check Results*\n"
        if updates:
            message += "\nUpdates Available:\n" + "\n".join(updates)
        if vulnerabilities:
            message += "\nVulnerabilities Found:\n" + "\n".join(vulnerabilities)
        
        try:
            self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                text=message
            )
            st.info("Slack notification sent")
        except SlackApiError as e:
            st.error(f"Failed to send Slack notification: {str(e)}")

    def send_hubspot_setup_link(self):
        """Send HubSpot API setup instructions to Slack"""
        try:
            if not self.slack_client:
                st.warning("Slack credentials not configured. Skipping notification.")
                return

            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔑 HubSpot API Setup Required",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "To set up HubSpot API access, follow these steps:"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "1. Go to <https://developers.hubspot.com/docs/api/overview|HubSpot Developer Portal>\n2. Log in to your HubSpot account\n3. Navigate to Settings > Account Setup > Integrations > API Key\n4. Generate a new API key or copy your existing one\n5. Add the API key to your `.env` file as `HUBSPOT_API_KEY=your_key_here`"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "📝 *Note:* After adding the API key, restart the application for the changes to take effect."
                        }
                    }
                ]
            }

            self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                blocks=message["blocks"],
                text="HubSpot API Setup Instructions"
            )
            st.success("HubSpot setup instructions sent to Slack channel")
        except Exception as e:
            st.error(f"Failed to send HubSpot setup instructions: {str(e)}")
            st.error(f"Failed to send Slack notification: {str(e)}")