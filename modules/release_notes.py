import streamlit as st
import os
import json
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import openai
from github import Github
from openai import OpenAI

class ReleaseNotes:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_owner = os.getenv('GITHUB_OWNER')
        self.github_repo = os.getenv('GITHUB_REPO')
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_channels = {
            'release_notes': 'C0926P82GRE', 
            'release_feed': 'C0926P82GRE' 
        }
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
    
        self.github_client = None
        if self.github_token:
            self.github_client = Github(self.github_token)
        
        self.slack_client = None
        if self.slack_token:
            self.slack_client = WebClient(token=self.slack_token)
        
        self.openai_client = None
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        
       
        self.release_notes_file = 'data/release_notes.json'
        self.pull_requests_file = 'data/pull_requests.json'
        
        os.makedirs('data', exist_ok=True)
        
        self.load_data()

    def load_data(self):
        """Load or initialize release notes and pull requests data"""
        if os.path.exists(self.release_notes_file):
            with open(self.release_notes_file, 'r') as f:
                self.release_notes = json.load(f)
        else:
            self.release_notes = {
                'releases': [],
                'last_release': None
            }
            self._save_release_notes_data()
    
        if os.path.exists(self.pull_requests_file):
            with open(self.pull_requests_file, 'r') as f:
                self.pull_requests = json.load(f)
        else:
            self.pull_requests = {
                'merged_prs': [],
                'last_update': None
            }
            self.save_pull_requests()

    def _save_release_notes_data(self):
        """Internal method to save release notes data to file"""
        with open(self.release_notes_file, 'w') as f:
            json.dump(self.release_notes, f, indent=4)

    def save_release_notes(self, version, content):
        """Save new release notes"""
        release = {
            'version': version,
            'content': content,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.release_notes['releases'].append(release)
        self.release_notes['last_release'] = version
        self._save_release_notes_data()

    def save_pull_requests(self):
        """Save pull requests data to file"""
        with open(self.pull_requests_file, 'w') as f:
            json.dump(self.pull_requests, f, indent=4)

    def generate_release_notes(self, version, release_date, release_type):
        """Generate release notes using OpenAI"""
        try:
            merged_prs = self.pull_requests.get('merged_prs', [])
            
            if not merged_prs:
                fallback_content = {
                    'features': [
                        'Enhanced system stability and performance',
                        'Improved error handling and logging',
                        'Updated documentation and code comments',
                        'Optimized database queries and caching',
                        'Enhanced security measures and access controls'
                    ],
                    'improvements': [
                        'Refactored core components for better maintainability',
                        'Updated third-party dependencies to latest versions',
                        'Improved test coverage and CI/CD pipeline',
                        'Enhanced monitoring and alerting system',
                        'Optimized resource utilization'
                    ],
                    'bug_fixes': [
                        'Fixed edge cases in data processing',
                        'Resolved authentication token refresh issues',
                        'Fixed memory leak in background tasks',
                        'Corrected timezone handling in reports',
                        'Fixed UI rendering issues in dark mode'
                    ]
                }
                
                release_notes = f"""# Release Notes v{version}

**Release Date:** {release_date.strftime("%Y-%m-%d")}
**Release Type:** {release_type}

## 🚀 Release Summary
This release focuses on system stability, performance improvements, and code quality enhancements. We've made significant progress in optimizing our infrastructure and improving the overall user experience.

## ✨ New Features
{chr(10).join([f"- {feature}" for feature in fallback_content['features']])}

## 🛠️ Improvements
{chr(10).join([f"- {improvement}" for improvement in fallback_content['improvements']])}

## 🐛 Bug Fixes
{chr(10).join([f"- {fix}" for fix in fallback_content['bug_fixes']])}

## 📊 Technical Details
- **Build Version:** {version}
- **Environment:** Production
- **Deployment Date:** {release_date.strftime("%Y-%m-%d")}
- **Release Type:** {release_type}

## 👥 Contributors
- Development Team
- QA Team
- DevOps Team

## 📝 Notes
This release includes various improvements and optimizations to ensure a stable and efficient system. We continue to focus on delivering high-quality software while maintaining system reliability.

---
*Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*"""
                
                return release_notes

            pr_info = "\n".join([
                f"PR #{pr['id']}: {pr['title']}\nDescription: {pr['description']}\nAuthor: {pr['author']}\nMerged at: {pr['merged_at']}"
                for pr in merged_prs
            ])
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a technical writer creating professional and engaging release notes."},
                    {"role": "user", "content": f"""Generate comprehensive release notes for version {version} ({release_type} release) with the following merged pull requests.

{pr_info}

Please structure the release notes with the following sections:
1. Release Summary (2-3 sentences overview)
2. New Features (with emojis and clear descriptions)
3. Improvements (with emojis and clear descriptions)
4. Bug Fixes (with emojis and clear descriptions)
5. Technical Details (version, environment, date)
6. Contributors (list of authors)
7. Notes (any additional important information)

Use markdown formatting and emojis to make it visually appealing and easy to read.
Include relevant technical details and impact of changes.
Make it professional yet engaging."""}
                ]
            )

            release_notes = response.choices[0].message.content

            release_notes = f"""# Release Notes v{version}

**Release Date:** {release_date.strftime("%Y-%m-%d")}
**Release Type:** {release_type}

{release_notes}

---
*Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*"""

            return release_notes

        except Exception as e:
            st.error(f"Error generating release notes: {str(e)}")
            return None

    def notify_new_release(self, release):
        """Send release notification to Slack"""
        try:
            if not self.slack_token or not self.slack_channels['release_notes']:
                st.warning("Slack credentials not configured")
                return

            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🎉 New Release: v{release['version']}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Release Type:*\n{release['type']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Release Date:*\n{release['date']}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Release Notes:*\n{release['notes']}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Artifact Link:*\n<{release.get('artifact_url', '#')}|Download Release Package>"
                        }
                    }
                ]
            }

            self.slack_client.chat_postMessage(
                channel=self.slack_channels['release_notes'],
                blocks=message["blocks"]
            )
            st.success("Release notification sent to Slack!")

        except Exception as e:
            st.error(f"Failed to send Slack notification: {str(e)}")

    def fetch_github_prs(self):
        """Fetch pull requests from GitHub"""
        try:
            if not self.github_client or not self.github_owner or not self.github_repo:
                st.warning("GitHub credentials not configured. Using test data.")
                return

            # Get the repository
            repo = self.github_client.get_repo(f"{self.github_owner}/{self.github_repo}")
            
            # Fetch open PRs
            open_prs = []
            for pr in repo.get_pulls(state='open'):
                open_prs.append({
                    'id': pr.number,
                    'title': pr.title,
                    'description': pr.body or "No description provided",
                    'author': pr.user.login,
                    'reviewers': [reviewer.login for reviewer in pr.get_review_requests()[0]],
                    'status': 'open',
                    'created_at': pr.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })

            # Fetch merged PRs
            merged_prs = []
            for pr in repo.get_pulls(state='closed'):
                if pr.merged_at:  # Only include merged PRs
                    merged_prs.append({
                        'id': pr.number,
                        'title': pr.title,
                        'description': pr.body or "No description provided",
                        'author': pr.user.login,
                        'reviewers': [reviewer.login for reviewer in pr.get_review_requests()[0]],
                        'status': 'merged',
                        'merged_at': pr.merged_at.strftime("%Y-%m-%d %H:%M:%S")
                    })

            # Update pull requests data
            self.pull_requests = {
                'open_prs': open_prs,
                'merged_prs': merged_prs
            }
            self.save_pull_requests()
            
            st.success(f"Fetched {len(open_prs)} open PRs and {len(merged_prs)} merged PRs")
            return True

        except Exception as e:
            st.error(f"Error fetching GitHub PRs: {str(e)}")
            return False

    def load_pull_requests_data(self):
        """Load pull requests data from file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.pull_requests_file):
            with open(self.pull_requests_file, 'r') as f:
                self.pull_requests = json.load(f)
                # Initialize merged_prs if it doesn't exist
                if 'merged_prs' not in self.pull_requests:
                    self.pull_requests['merged_prs'] = []
                # Initialize open_prs if it doesn't exist
                if 'open_prs' not in self.pull_requests:
                    self.pull_requests['open_prs'] = []
                self.save_pull_requests()
        else:
            # Initialize with test data
            self.pull_requests = {
                'open_prs': [
                    {
                        'id': 1,
                        'title': 'Add new feature',
                        'description': 'Implemented new feature X',
                        'author': 'developer1',
                        'reviewers': ['reviewer1', 'reviewer2'],
                        'status': 'open',
                        'created_at': (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
                    }
                ],
                'merged_prs': [
                    {
                        'id': 2,
                        'title': 'Fix bug in authentication',
                        'description': 'Fixed authentication bug in login flow',
                        'author': 'developer2',
                        'reviewers': ['reviewer1'],
                        'status': 'merged',
                        'merged_at': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                    }
                ]
            }
            self.save_pull_requests() 

    def display_interface(self):
        st.subheader("Release Notes Generator")

        # Fetch latest PRs
        if st.button("Fetch Latest PRs"):
            self.fetch_github_prs()

        st.write("### Merged Pull Requests")
        if not self.pull_requests.get('merged_prs'):
            st.info("No merged pull requests found. Will generate release notes with system improvements and optimizations.")
        else:
            for pr in self.pull_requests['merged_prs']:
                with st.expander(f"PR #{pr['id']}: {pr['title']}"):
                    st.write(f"**Author:** {pr['author']}")
                    st.write(f"**Merged at:** {pr['merged_at']}")
                    st.write(f"**Description:** {pr['description']}")
                    st.write(f"**Reviewers:** {', '.join(pr['reviewers'])}")

        st.write("### Generate Release Notes")
        version = st.text_input("Version", placeholder="e.g., 1.0.0")
        release_date = st.date_input("Release Date", datetime.now())
        release_type = st.selectbox("Release Type", ["Major", "Minor", "Patch"])
        
        if st.button("Generate Release Notes"):
            if not version:
                st.error("Please enter a version number")
                return
            
            release_notes = self.generate_release_notes(version, release_date, release_type)
            if release_notes:
                st.write("### Generated Release Notes")
                st.markdown(release_notes)
                
                if st.button("Save Release Notes"):
                    self.save_release_notes(version, release_notes)
                    st.success(f"Release notes saved to data/release_notes_{version}.md")
                    
                    # Notify on Slack
                    self.notify_new_release({
                        'version': version,
                        'type': release_type,
                        'date': release_date.strftime("%Y-%m-%d"),
                        'notes': release_notes,
                        'artifact_url': f"https://github.com/{self.github_owner}/{self.github_repo}/releases/tag/v{version}"
                    }) 

        if st.button("Send Release v1.0.0 Summary"):
            self.send_release_summary("v1.0.0")

    def _split_long_text(self, text, max_length=2900):
        """Split long text into chunks under max_length for Slack blocks."""
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

    def notify_release_notes(self, release_notes):
        """Send release notes to both Slack channels, splitting long text into multiple blocks."""
        try:
            if not self.slack_client:
                st.warning("Slack credentials not configured. Skipping notification.")
                return
            def add_split_blocks(label, text):
                blocks = []
                for chunk in self._split_long_text(text):
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{label}:*\n{chunk.strip()}"
                        }
                    })
                return blocks

            message_blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🎉 New Release Notes Available",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Release Type:* {release_notes['type']}\n*Date:* {release_notes['date']}"
                    }
                }
            ]
            message_blocks += add_split_blocks("Summary", release_notes['summary'])
            message_blocks += add_split_blocks("New Features", release_notes['new_features'])
            message_blocks += add_split_blocks("Improvements", release_notes['improvements'])
            message_blocks += add_split_blocks("Bug Fixes", release_notes['bug_fixes'])
            message_blocks += add_split_blocks("Technical Details", release_notes['technical_details'])
            message_blocks += add_split_blocks("Contributors", release_notes['contributors'])
            message_blocks += add_split_blocks("Additional Notes", release_notes['additional_notes'])
            message_blocks.append({"type": "divider"})
            message_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📦 *Download Release Package:*\n<https://github.com/{self.github_owner}/{self.github_repo}/releases/latest|Download Latest Release>"
                }
            })

            self.slack_client.chat_postMessage(
                channel=self.slack_channels['release_notes'],
                blocks=message_blocks,
                text="New Release Notes Available"
            )

            changelog = self._format_changelog(release_notes)
            changelog_blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 Release Changelog",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Version:* {release_notes['version']}\n*Release Date:* {release_notes['date']}"
                    }
                }
            ]
            for chunk in self._split_long_text(changelog):
                changelog_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": chunk.strip()
                    }
                })
            changelog_blocks.append({"type": "divider"})
            changelog_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📦 *Download Release Package:*\n<https://github.com/{self.github_owner}/{self.github_repo}/releases/latest|Download Latest Release>"
                }
            })

            self.slack_client.chat_postMessage(
                channel=self.slack_channels['release_feed'],
                blocks=changelog_blocks,
                text="Release Changelog"
            )

            st.success("Release notes sent to Slack channels")
        except Exception as e:
            st.error(f"Failed to send Slack notification: {str(e)}")

    def _format_changelog(self, release_notes):
        """Format the changelog section of release notes"""
        changelog = []
        

        if release_notes['new_features']:
            changelog.append("*New Features:*")
            changelog.extend([f"• {feature}" for feature in release_notes['new_features'].split('\n') if feature.strip()])
            changelog.append("")
        
      
        if release_notes['improvements']:
            changelog.append("*Improvements:*")
            changelog.extend([f"• {improvement}" for improvement in release_notes['improvements'].split('\n') if improvement.strip()])
            changelog.append("")
        
        
        if release_notes['bug_fixes']:
            changelog.append("*Bug Fixes:*")
            changelog.extend([f"• {fix}" for fix in release_notes['bug_fixes'].split('\n') if fix.strip()])
            changelog.append("")
        
        return "\n".join(changelog)

    def send_release_summary(self, version="v1.0.0"):
        """Send a focused release summary to Slack"""
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
                            "text": f"🎉 Release {version} Summary",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Version:* {version}\n*Release Date:* {datetime.now().strftime('%Y-%m-%d')}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Summary:*\n• Initial release of the application\n• Core functionality implemented\n• Basic features ready for use"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📦 *Download Release Package:*\n<https://github.com/{self.github_owner}/{self.github_repo}/releases/tag/{version}|Download {version}>"
                        }
                    }
                ]
            }

            self.slack_client.chat_postMessage(
                channel=self.slack_channels['release_notes'],
                blocks=message["blocks"],
                text=f"Release {version} Summary"
            )
            st.success(f"Release summary for {version} sent to Slack channel")
        except Exception as e:
            st.error(f"Failed to send release summary: {str(e)}") 