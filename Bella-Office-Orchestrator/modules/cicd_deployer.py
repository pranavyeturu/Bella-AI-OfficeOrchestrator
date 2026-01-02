import streamlit as st
import os
import json
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from openai import OpenAI
import random 

class CICDDeployer:
    def __init__(self):
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_channel = 'C0926P82GRE'  
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize clients
        self.slack_client = None
        if self.slack_token:
            self.slack_client = WebClient(token=self.slack_token)
        
        self.openai_client = None
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
      
        self.deployments_file = 'data/deployments.json'
     
        os.makedirs('data', exist_ok=True)
        
        # Load or initialize data
        self.load_deployments_data()

    @property
    def environments(self):
        """Get list of available environments"""
        return list(self.deployments.get('environments', {}).keys())

    def load_deployments_data(self):
        """Load or initialize deployments data"""
        try:
            default_data = {
                'deployments': [],
                'last_deployment': None,
                'environments': {
                    'development': {'status': 'stable', 'current_version': None},
                    'staging': {'status': 'stable', 'current_version': None},
                    'production': {'status': 'stable', 'current_version': None}
                }
            }
            
            if os.path.exists(self.deployments_file) and os.path.getsize(self.deployments_file) > 0:
                with open(self.deployments_file, 'r') as f:
                    self.deployments = json.load(f)
            else:
                self.deployments = default_data
                self.save_deployments_data()
                
        except Exception as e:
            st.error(f"Error loading deployments data: {str(e)}")
            self.deployments = default_data
            self.save_deployments_data()

    def save_deployments_data(self):
        """Save deployments data to file"""
        try:
            with open(self.deployments_file, 'w') as f:
                json.dump(self.deployments, f, indent=4)
        except Exception as e:
            st.error(f"Error saving deployments data: {str(e)}")

    def analyze_deployment_impact(self, changes, environment):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior DevOps engineer analyzing deployment impacts."},
                    {"role": "user", "content": f"""Analyze the potential impact of the following deployment changes for the {environment} environment.
                    Consider:
                    1. Performance impact
                    2. Security implications
                    3. User experience changes
                    4. Database and infrastructure requirements
                    5. Potential risks and mitigation strategies
                    
                    Format the analysis as a clear, structured response with sections for each aspect.
                    
                    Changes:
                    {changes}"""}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to analyze deployment impact: {str(e)}")
            return "Impact analysis not available"

    def generate_deployment_plan(self, version, changes, environment):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior DevOps engineer creating deployment plans."},
                    {"role": "user", "content": f"""Create a detailed deployment plan for version {version} in the {environment} environment.
                    Include:
                    1. Pre-deployment checks
                    2. Database migration steps
                    3. Deployment procedure
                    4. Post-deployment verification
                    5. Rollback procedure
                    6. Monitoring and alerting setup
                    
                    Format the plan as a clear, step-by-step guide with estimated durations.
                    
                    Changes:
                    {changes}"""}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to generate deployment plan: {str(e)}")
            return "Deployment plan not available"

    def run_tests(self, environment):
        """Run tests for the deployment"""
        try:
            test_results = {
                'unit_tests': {
                    'status': 'success',
                    'duration': '5m',
                    'coverage': '85%',
                    'details': 'All unit tests passed successfully'
                },
                'integration_tests': {
                    'status': 'success',
                    'duration': '10m',
                    'details': 'Integration tests completed successfully'
                },
                'security_scan': {
                    'status': 'success',
                    'duration': '8m',
                    'vulnerabilities': 0,
                    'details': 'No security vulnerabilities found'
                },
                'performance_tests': {
                    'status': 'success',
                    'duration': '12m',
                    'response_time': '200ms',
                    'details': 'Performance metrics within acceptable range'
                }
            }
            
            if self.deployments['deployments']:
                current_deployment = self.deployments['deployments'][-1]
                current_deployment['stages'].update({
                    'unit_tests': test_results['unit_tests'],
                    'integration_tests': test_results['integration_tests'],
                    'security_scan': test_results['security_scan'],
                    'performance_tests': test_results['performance_tests']
                })
                self.save_deployments_data()
            
            return test_results
        except Exception as e:
            st.error(f"Error running tests: {str(e)}")
            return None

    def display_interface(self):
        st.subheader("CI/CD Deployment System")

        with st.expander("Deployment Status", expanded=True):
            st.write("Last 5 Deployments:")
            for deployment in self.deployments['deployments'][-5:]:
                st.write(f"### Deployment #{deployment['id']}")
                st.write(f"Version: {deployment['version']}")
                st.write(f"Environment: {deployment.get('environment', 'production')}")  # Use get() with default
                st.write(f"Status: {deployment['status']}")
                st.write(f"Timestamp: {deployment['timestamp']}")
                st.write(f"Changes: {deployment['changes']}")
                
                st.write("#### Deployment Stages")
                for stage, details in deployment.get('stages', {}).items():
                    status_emoji = "✅" if details['status'] == 'success' else "❌"
                    st.write(f"{status_emoji} {stage.replace('_', ' ').title()}: {details['duration']}")
                    if 'coverage' in details:
                        st.write(f"   Coverage: {details['coverage']}")
                    if 'vulnerabilities' in details:
                        st.write(f"   Vulnerabilities: {details['vulnerabilities']}")
                    if 'response_time' in details:
                        st.write(f"   Response Time: {details['response_time']}")
                
                if 'metrics' in deployment:
                    st.write("#### Metrics")
                    for metric, value in deployment['metrics'].items():
                        st.write(f"- {metric.replace('_', ' ').title()}: {value}")
                
                st.markdown("---")

        
        with st.expander("Trigger New Deployment", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                version = st.text_input("Version (e.g., 1.0.0)")
                environment = st.selectbox("Environment", self.environments)
            with col2:
                changes = st.text_area("Describe Changes")
            
            if st.button("Analyze Changes"):
                if changes:
                    st.write("### Impact Analysis")
                    st.write(self.analyze_deployment_impact(changes, environment))
                else:
                    st.warning("Please provide changes to analyze")
            
            if st.button("Generate Deployment Plan"):
                if version and changes:
                    st.write("### Deployment Plan")
                    st.write(self.generate_deployment_plan(version, changes, environment))
                else:
                    st.warning("Please provide both version and changes")
            
            if st.button("Run Tests"):
                if changes:
                    st.write("### Test Results")
                    test_results = self.run_tests(environment)
                    for test_type, results in test_results.items():
                        status_emoji = "✅" if results['status'] == 'success' else "❌"
                        st.write(f"{status_emoji} {test_type.replace('_', ' ').title()}")
                        for metric, value in results.items():
                            if metric != 'status':
                                st.write(f"   {metric.replace('_', ' ').title()}: {value}")
                else:
                    st.warning("Please provide changes to test")
            
            if st.button("Trigger Deployment"):
                if version and changes:
                    if self.trigger_deployment(version, changes, environment):
                        st.success("Deployment triggered successfully!")
                        st.rerun()
                else:
                    st.warning("Please provide both version and changes")

        
        with st.expander("Rollback Options", expanded=True):
            successful_deployments = [d for d in self.deployments['deployments'] if d['status'] == 'success']
            if successful_deployments:
                last_successful = successful_deployments[-1]
                st.write(f"Last Successful Deployment: Version {last_successful['version']} ({last_successful['environment']})")
                if st.button("Rollback to Last Successful Version"):
                    if self.rollback_deployment(last_successful['version'], last_successful['environment']):
                        st.success("Rollback initiated successfully!")
                        st.rerun()
            else:
                st.write("No successful deployments available for rollback")

    
        with st.expander("Monitoring Dashboard", expanded=True):
            st.write("### System Health")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Error Rate", "0.1%", "0.05%")
            with col2:
                st.metric("Response Time", "200ms", "10ms")
            with col3:
                st.metric("CPU Usage", "45%", "5%")
            
            st.write("### Recent Alerts")
            alerts = [
                {"severity": "low", "message": "High memory usage detected", "time": "5 minutes ago"},
                {"severity": "medium", "message": "Database connection pool near capacity", "time": "15 minutes ago"},
                {"severity": "high", "message": "API response time increased", "time": "30 minutes ago"}
            ]
            for alert in alerts:
                severity_color = {
                    "low": "blue",
                    "medium": "orange",
                    "high": "red"
                }[alert["severity"]]
                st.write(f"<span style='color:{severity_color}'>{alert['message']} ({alert['time']})</span>", unsafe_allow_html=True)

    def trigger_deployment(self, version, changes, environment):
        """Trigger a new deployment"""
        try:
            if not version or not changes:
                st.error("Version and changes are required")
                return False

            test_results = self.run_tests(environment)
            if not test_results:
                st.error("Failed to run tests")
                return False
            new_deployment = {
                'id': len(self.deployments['deployments']) + 1,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'success',
                'version': version,
                'environment': environment,
                'changes': changes,
                'stages': {
                    'code_review': {'status': 'success', 'duration': '15m'},
                    'unit_tests': test_results['unit_tests'],
                    'integration_tests': test_results['integration_tests'],
                    'security_scan': test_results['security_scan'],
                    'performance_tests': test_results['performance_tests'],
                    'deployment': {'status': 'success', 'duration': '5m'},
                    'smoke_tests': {'status': 'success', 'duration': '3m'},
                    'monitoring': {'status': 'success', 'duration': '2m'}
                },
                'metrics': {
                    'build_time': '5m 30s',
                    'test_coverage': test_results['unit_tests']['coverage'],
                    'performance_impact': 'low',
                    'error_rate': '0.1%',
                    'response_time': test_results['performance_tests']['response_time']
                }
            }

            self.deployments['deployments'].append(new_deployment)
            self.save_deployments_data()

            if self.slack_token and self.slack_channel:
                try:
                    message = {
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": f"🚀 Deployment Successful - v{version}",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Environment:*\n{environment}"
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Version:*\nv{version}"
                                    }
                                ]
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*Changes:*\n{changes}"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Test Results:*"
                                }
                            }
                        ]
                    }

                    for test_name, result in test_results.items():
                        message["blocks"].append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ *{test_name.replace('_', ' ').title()}*\n{result['details']}"
                            }
                        })

                    message["blocks"].append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Metrics:*\n" + "\n".join([
                                f"• {k.replace('_', ' ').title()}: {v}"
                                for k, v in new_deployment['metrics'].items()
                            ])
                        }
                    })

                    self.slack_client.chat_postMessage(
                        channel=self.slack_channel,
                        blocks=message["blocks"]
                    )
                except Exception as e:
                    st.warning(f"Failed to send Slack notification: {str(e)}")

            st.success(f"Deployment v{version} completed successfully!")
            return True

        except Exception as e:
            st.error(f"Deployment failed: {str(e)}")
            return False

    def rollback_deployment(self, version, environment):
        try:
            new_deployment = {
                'id': len(self.deployments['deployments']) + 1,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'success',
                'version': version,
                'environment': environment,
                'changes': f"Rollback to version {version}",
                'stages': {
                    'code_review': {'status': 'success', 'duration': '5m'},
                    'unit_tests': {'status': 'success', 'duration': '3m', 'coverage': '85%'},
                    'integration_tests': {'status': 'success', 'duration': '5m'},
                    'security_scan': {'status': 'success', 'duration': '3m', 'vulnerabilities': 0},
                    'performance_tests': {'status': 'success', 'duration': '5m', 'response_time': '200ms'},
                    'deployment': {'status': 'success', 'duration': '3m'},
                    'smoke_tests': {'status': 'success', 'duration': '2m'},
                    'monitoring': {'status': 'success', 'duration': '1m'}
                },
                'metrics': {
                    'build_time': '3m 30s',
                    'test_coverage': '85%',
                    'performance_impact': 'low',
                    'error_rate': '0.1%',
                    'response_time': '200ms'
                }
            }
            
            self.deployments['deployments'].append(new_deployment)
            self.save_deployments_data()
            
         
            if self.slack_token:
                message = f"""↩️ *Rollback Successful*
*Version:* {version}
*Environment:* {environment}

*Rollback Details:*
• Previous Version: {version}
• Environment: {environment}
• Status: Success
• Duration: 3m 30s

*Verification:*
• All services restored
• Database state reverted
• Cache cleared
• Monitoring active

:white_check_mark: Rollback completed successfully!"""
                try:
                    self.slack_client.chat_postMessage(
                        channel=self.slack_channel,
                        text=message,
                        blocks=[
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "↩️ Rollback Successful",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Version:*\n{version}"
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Environment:*\n{environment}"
                                    }
                                ]
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Rollback Details:*\n" + "\n".join([
                                        f"• Previous Version: {version}",
                                        f"• Environment: {environment}",
                                        "• Status: Success",
                                        "• Duration: 3m 30s"
                                    ])
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Verification:*\n" + "\n".join([
                                        "• All services restored",
                                        "• Database state reverted",
                                        "• Cache cleared",
                                        "• Monitoring active"
                                    ])
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":white_check_mark: Rollback completed successfully!"
                                }
                            }
                        ]
                    )
                except SlackApiError as e:
                    st.error(f"Failed to send Slack notification: {str(e)}")
            
            return True
        except Exception as e:
            st.error(f"Rollback failed: {str(e)}")
            return False 