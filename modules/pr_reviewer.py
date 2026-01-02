import streamlit as st
import os
import json
from datetime import datetime
from github import Github
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from openai import OpenAI

class PRReviewer:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_owner = os.getenv('GITHUB_OWNER')
        self.github_repo = os.getenv('GITHUB_REPO')
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_channel = os.getenv('SLACK_CHANNEL_ID')
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
      
        self.reviewers_file = 'data/reviewers.json'
        self.pull_requests_file = 'data/pull_requests.json'
        
       
        os.makedirs('data', exist_ok=True)

        self.load_data()

    def load_data(self):
        """Load or initialize reviewers and pull requests data"""
        try:
            default_reviewers = {
                'team_members': [],
                'last_reviewer': None,
                'review_counts': {}
            }
            
            if os.path.exists(self.reviewers_file) and os.path.getsize(self.reviewers_file) > 0:
                with open(self.reviewers_file, 'r') as f:
                    self.reviewers = json.load(f)
                    # Ensure required fields exist
                    if 'review_counts' not in self.reviewers:
                        self.reviewers['review_counts'] = {}
                    if 'last_reviewer' not in self.reviewers:
                        self.reviewers['last_reviewer'] = None
                    # Initialize review counts for existing team members
                    for member in self.reviewers.get('team_members', []):
                        if member not in self.reviewers['review_counts']:
                            self.reviewers['review_counts'][member] = 0
            else:
                self.reviewers = default_reviewers
                self.save_reviewers()
            
            default_prs = {
                'open_prs': []
            }
            
            if os.path.exists(self.pull_requests_file) and os.path.getsize(self.pull_requests_file) > 0:
                with open(self.pull_requests_file, 'r') as f:
                    self.pull_requests = json.load(f)
            else:
                self.pull_requests = default_prs
                self.save_pull_requests()
                
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            self.reviewers = default_reviewers
            self.pull_requests = default_prs
            self.save_reviewers()
            self.save_pull_requests()

    def save_reviewers(self):
        with open(self.reviewers_file, 'w') as f:
            json.dump(self.reviewers, f)

    def save_pull_requests(self):
        with open(self.pull_requests_file, 'w') as f:
            json.dump(self.pull_requests, f)

    def generate_pr_description(self, title, changes):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a technical writer helping to create detailed PR descriptions."},
                    {"role": "user", "content": f"Create a detailed PR description for title: {title}\nChanges: {changes}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to generate PR description: {str(e)}")
            return f"PR: {title}\nChanges: {changes}"

    def fetch_github_prs(self):
        try:
            if not self.github_token or not self.github_owner:
                st.warning("GitHub token or owner not configured. Please check your .env file.")
                return False

            repo = self.github_client.get_repo(f"{self.github_owner}/{self.github_repo}")
            prs = repo.get_pulls(state='open')
            
            self.pull_requests['open_prs'] = []
            
            for pr in prs:
                try:
                    pr_details = {
                        'id': pr.number,
                        'title': pr.title,
                        'author': pr.user.login,
                        'status': 'open',
                        'created_at': pr.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        'description': pr.body or "No description provided",
                        'reviewers': [reviewer.login for reviewer in pr.requested_reviewers],
                        'files_changed': [file.filename for file in pr.get_files()],
                        'additions': pr.additions,
                        'deletions': pr.deletions
                    }
                    self.pull_requests['open_prs'].append(pr_details)
                except Exception as e:
                    st.warning(f"Failed to process PR #{pr.number}: {str(e)}")
                    continue
            
            self.save_pull_requests()
            return True
        except Exception as e:
            st.error(f"Failed to fetch GitHub PRs: {str(e)}")
            return False

    def generate_review_guidelines(self, pr):
        try:
            pr_info = f"""
            PR Title: {pr['title']}
            Description: {pr['description']}
            Files Changed: {', '.join(pr['files_changed'])}
            Additions: {pr['additions']}
            Deletions: {pr['deletions']}
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior software engineer helping to generate specific and relevant PR review guidelines."},
                    {"role": "user", "content": f"""Based on the following PR information, generate specific and relevant review guidelines. 
                    Focus on the most important aspects to review given the type of changes.
                    Format the guidelines as a numbered list with clear, actionable items.
                    
                    PR Information:
                    {pr_info}
                    
                    Generate 5-7 specific review guidelines that are most relevant to this PR."""}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to generate review guidelines: {str(e)}")
            return """Review Guidelines:
1. Check code quality and best practices
2. Verify test coverage
3. Review documentation updates
4. Check for security concerns
5. Ensure backward compatibility"""

    def display_interface(self):
        st.subheader("PR Reviewer Round-Robin System")

        with st.expander("Manage Team Members", expanded=True):
            st.write("Current Team Members:")
            for member in self.reviewers['team_members']:
                review_count = self.reviewers['review_counts'].get(member, 0)
                st.write(f"- {member} (Reviews: {review_count})")
            
            new_member = st.text_input("Add New Team Member")
            if st.button("Add Member"):
                if new_member and new_member not in self.reviewers['team_members']:
                    self.reviewers['team_members'].append(new_member)
                    self.reviewers['review_counts'][new_member] = 0
                    self.save_reviewers()
                    st.success(f"Added {new_member} to the team")
                    st.rerun()
            
            if self.reviewers['team_members']:
                member_to_remove = st.selectbox("Remove Team Member", self.reviewers['team_members'])
                if st.button("Remove Member"):
                    self.reviewers['team_members'].remove(member_to_remove)
                    if member_to_remove in self.reviewers['review_counts']:
                        del self.reviewers['review_counts'][member_to_remove]
                    if self.reviewers['last_reviewer'] == member_to_remove:
                        self.reviewers['last_reviewer'] = None
                    self.save_reviewers()
                    st.success(f"Removed {member_to_remove} from the team")
                    st.rerun()

        with st.expander("GitHub Integration", expanded=True):
            if not self.github_token or not self.github_owner:
                st.warning("GitHub token or owner not configured. Please check your .env file.")
            else:
                if st.button("Fetch Latest PRs from GitHub"):
                    if self.fetch_github_prs():
                        st.success("Successfully fetched latest PRs from GitHub")
                    else:
                        st.error("Failed to fetch PRs from GitHub")

        # Open Pull Requests
        with st.expander("Open Pull Requests", expanded=True):
            if not self.pull_requests.get('open_prs'):
                st.info("No open pull requests found")
            else:
                for pr in self.pull_requests['open_prs']:
                    st.markdown(f"### PR #{pr['id']}: {pr['title']}")
                    st.write(f"**Author:** {pr['author']}")
                    st.write(f"**Created at:** {pr['created_at']}")
                    st.write(f"**Description:** {pr['description']}")
                    
                    # Files Changed
                    st.write("**Files Changed:**")
                    for file in pr.get('files_changed', []):
                        st.write(f"- {file}")
                    
                    # Changes Summary
                    st.write(f"**Changes:** +{pr.get('additions', 0)} -{pr.get('deletions', 0)}")
                    
                    # Current Reviewers
                    st.write("**Current Reviewers:**")
                    if pr.get('reviewers'):
                        for reviewer in pr['reviewers']:
                            st.write(f"- {reviewer}")
                    else:
                        st.write("No reviewers assigned yet")
                    
                    # Assign Reviewers Button
                    if st.button("Assign Reviewers", key=f"assign_{pr['id']}"):
                        selected_reviewers = self.select_reviewers(pr['author'])
                        if selected_reviewers:
                            pr['reviewers'] = selected_reviewers
                            self.save_pull_requests()
                            self.notify_reviewers(pr, selected_reviewers)
                            st.success(f"Assigned reviewers: {', '.join(selected_reviewers)}")
                            st.rerun()
                        else:
                            st.warning("No available reviewers found")
                    
                    st.markdown("---")
        with st.expander("Create New PR", expanded=True):
            pr_title = st.text_input("PR Title")
            pr_changes = st.text_area("Describe Changes")
            
            if st.button("Generate PR Description"):
                if pr_title and pr_changes:
                    description = self.generate_pr_description(pr_title, pr_changes)
                    st.text_area("Generated Description", description, height=200)
                    
                    if st.button("Create PR"):
                        selected_reviewers = self.select_reviewers('current_user')
                        
                        new_pr = {
                            'id': len(self.pull_requests['open_prs']) + 1,
                            'title': pr_title,
                            'author': 'current_user',  # In production, get from GitHub
                            'status': 'open',
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'description': description,
                            'reviewers': selected_reviewers,
                            'files_changed': [],
                            'additions': 0,
                            'deletions': 0
                        }
                        self.pull_requests['open_prs'].append(new_pr)
                        self.save_pull_requests()
                        
                        self.notify_reviewers(new_pr, selected_reviewers)
                        st.success(f"PR created successfully! Assigned reviewers: {', '.join(selected_reviewers)}")
                        st.rerun()
                else:
                    st.error("Please provide both title and changes")

    def select_reviewers(self, author):
        """Select reviewers using round-robin scheduling"""
        available_reviewers = [r for r in self.reviewers['team_members'] if r != author]
        if not available_reviewers:
            return []
       
        for reviewer in available_reviewers:
            if reviewer not in self.reviewers['review_counts']:
                self.reviewers['review_counts'][reviewer] = 0
       
        sorted_reviewers = sorted(
            available_reviewers,
            key=lambda x: (
                self.reviewers['review_counts'].get(x, 0),
                1 if x == self.reviewers['last_reviewer'] else 0
            )
        )
        
        selected_reviewers = sorted_reviewers[:2]
        
        for reviewer in selected_reviewers:
            self.reviewers['review_counts'][reviewer] = self.reviewers['review_counts'].get(reviewer, 0) + 1
        self.reviewers['last_reviewer'] = selected_reviewers[-1]
        
        # Save updated reviewer data
        self.save_reviewers()
        
        return selected_reviewers

    def notify_reviewers(self, pr, reviewers):
        if not self.slack_token or not self.slack_channel:
            st.warning("Slack token or channel not configured. Please check your .env file.")
            return

        pr_url = f"https://github.com/{self.github_owner}/{self.github_repo}/pull/{pr['id']}"
        review_guidelines = self.generate_review_guidelines(pr)
        
        message = f"""🔍 *New PR Review Request*
PR #{pr['id']}: {pr['title']}
Author: {pr['author']}
Reviewers: {', '.join(reviewers)}
PR Link: {pr_url}

{review_guidelines}

Please review and provide feedback. You can accept the review request by clicking the button below."""

        try:
            self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                text=message,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Accept Review",
                                    "emoji": True
                                },
                                "style": "primary",
                                "value": f"accept_review_{pr['id']}"
                            }
                        ]
                    }
                ]
            )
            st.info("Slack notification sent")
        except SlackApiError as e:
            st.error(f"Failed to send Slack notification: {str(e)}") 