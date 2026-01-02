import json
import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import sys
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Add tools directory to path to import slack_bot
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
#from tools import slack_bot
from tools.slack_bot import send_office_ops_report



def load_building_data(file_path: str = "/Users/harshadayiniakula/desktop/Auropro/workflows/building_data.json"):
    """Load the building analytics data from JSON file."""
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"❌ Error: {file_path} not found!")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {file_path}!")
        return None


def analyze_data_with_llm(data):
    """Use OpenAI to analyze and summarize the building data."""
    
    # System prompt for the LLM
    SYSTEM_PROMPT = """You are an expert office operations analyst. Analyze the provided building analytics data and generate comprehensive insights.

Your analysis should include:
1.⁠ ⁠Key visitor patterns and trends
2.⁠ ⁠Delivery logistics summary 
3.⁠ ⁠Occupancy insights and space utilization
4.⁠ ⁠Notable patterns or anomalies
5.⁠ ⁠Actionable recommendations for office management

Return your analysis as a JSON object with the following structure:
{
    "executive_summary": "Brief 2-3 sentence overview",
    "visitor_insights": {
        "total_visitors": number,
        "peak_time": "description",
        "key_patterns": "analysis"
    },
    "delivery_insights": {
        "total_deliveries": number,
        "breakdown": "analysis of delivery types and patterns",
        "recommendations": "logistics recommendations"
    },
    "occupancy_insights": {
        "average_occupancy": number,
        "peak_occupancy": "description",
        "space_utilization": "analysis"
    },
    "action_items": ["list", "of", "recommended", "actions"],
    "alerts": ["any", "concerning", "patterns", "or", "issues"]
}"""

    # Prepare the data for LLM analysis
    building_data_str = json.dumps(data, indent=2)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"BUILDING ANALYTICS DATA:\n{building_data_str}\n\nPlease analyze this data and provide comprehensive insights following the JSON format specified."}
    ]

    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(resp.choices[0].message.content)
        print("✅ LLM analysis completed successfully!")
        return analysis
        
    except Exception as e:
        print(f"❌ Error with OpenAI API: {str(e)}")
        # Fallback to basic analysis if LLM fails
        return fallback_analysis(data)


def fallback_analysis(data):
    """Fallback analysis method if OpenAI API fails."""
    building_info = data.get('building_analytics', {})
    
    # Basic visitor analysis
    visitor_data = building_info.get('visitor_data', [])
    total_visitors = sum(entry['visitor_count'] for entry in visitor_data)
    
    # Basic delivery analysis  
    delivery_data = building_info.get('delivery_data', [])
    total_deliveries = sum(entry['delivery_count'] for entry in delivery_data)
    
    # Basic occupancy analysis
    occupancy_data = building_info.get('occupancy_sensor_data', [])
    avg_occupancy = sum(entry['occupancy_percentage'] for entry in occupancy_data) / len(occupancy_data) if occupancy_data else 0
    
    return {
        "executive_summary": f"Daily operations processed {total_visitors} visitors and {total_deliveries} deliveries with {round(avg_occupancy, 1)}% average occupancy.",
        "visitor_insights": {
            "total_visitors": total_visitors,
            "peak_time": "Analysis unavailable - using fallback mode",
            "key_patterns": "Basic counting completed"
        },
        "delivery_insights": {
            "total_deliveries": total_deliveries,
            "breakdown": "Delivery types processed",
            "recommendations": "Review delivery scheduling"
        },
        "occupancy_insights": {
            "average_occupancy": round(avg_occupancy, 1),
            "peak_occupancy": "Peak analysis unavailable",
            "space_utilization": "Average utilization calculated"
        },
        "action_items": ["Review OpenAI API connection", "Check building data quality"],
        "alerts": ["LLM analysis failed - using basic fallback"]
    }


def generate_summary_text(analysis):
    """Generate a concise text summary for Slack using LLM analysis."""
    
    visitor_insights = analysis.get('visitor_insights', {})
    delivery_insights = analysis.get('delivery_insights', {})
    occupancy_insights = analysis.get('occupancy_insights', {})
    action_items = analysis.get('action_items', [])
    alerts = analysis.get('alerts', [])
    
    summary = f"""🏢 *Daily Office Snapshot - {datetime.now().strftime('%B %d, %Y')}*

📊 *Executive Summary:*
{analysis.get('executive_summary', 'Analysis completed')}

📈 *Key Metrics:*
•⁠  ⁠Total Visitors: {visitor_insights.get('total_visitors', 'N/A')}
•⁠  ⁠Total Deliveries: {delivery_insights.get('total_deliveries', 'N/A')}
•⁠  ⁠Average Occupancy: {occupancy_insights.get('average_occupancy', 'N/A')}%

🔍 *Key Insights:*
•⁠  ⁠Visitor Patterns: {visitor_insights.get('key_patterns', 'No patterns identified')}
•⁠  ⁠Delivery Analysis: {delivery_insights.get('breakdown', 'Standard operations')}
•⁠  ⁠Space Utilization: {occupancy_insights.get('space_utilization', 'Normal utilization')}"""

    if action_items:
        summary += f"\n\n✅ *Recommended Actions:*"
        for i, action in enumerate(action_items[:3], 1):  # Limit to top 3 actions
            summary += f"\n{i}. {action}"
    
    if alerts:
        summary += f"\n\n⚠️ *Alerts:*"
        for alert in alerts[:2]:  # Limit to top 2 alerts
            summary += f"\n• {alert}"
    
    return summary


def create_pdf_report(analysis, output_path="daily_office_report.pdf"):
    """Generate a detailed PDF report using LLM analysis."""
    doc = SimpleDocTemplate(output_path, pagesize=letter, 
                          rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkblue
    )
    
    story = []
    
    # Title
    title = Paragraph(f"Daily Office Operations Report<br/>{datetime.now().strftime('%B %d, %Y')}", title_style)
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", styles['Heading2']))
    exec_summary = analysis.get('executive_summary', 'Daily operations summary completed.')
    story.append(Paragraph(exec_summary, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Visitor Analytics
    visitor_insights = analysis.get('visitor_insights', {})
    story.append(Paragraph("Visitor Analytics", styles['Heading2']))
    
    visitor_text = f"""
    Total visitors processed: {visitor_insights.get('total_visitors', 'N/A')}
    Peak traffic period: {visitor_insights.get('peak_time', 'Analysis not available')}
    
    Key patterns observed: {visitor_insights.get('key_patterns', 'No significant patterns identified')}
    """
    story.append(Paragraph(visitor_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Delivery Analytics  
    delivery_insights = analysis.get('delivery_insights', {})
    story.append(Paragraph("Delivery Analytics", styles['Heading2']))
    
    delivery_text = f"""
    Total deliveries: {delivery_insights.get('total_deliveries', 'N/A')}
    
    Analysis: {delivery_insights.get('breakdown', 'Standard delivery operations observed')}
    
    Recommendations: {delivery_insights.get('recommendations', 'Continue current delivery processes')}
    """
    story.append(Paragraph(delivery_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Occupancy Analytics
    occupancy_insights = analysis.get('occupancy_insights', {})
    story.append(Paragraph("Occupancy Analytics", styles['Heading2']))
    
    occupancy_text = f"""
    Average occupancy: {occupancy_insights.get('average_occupancy', 'N/A')}%
    Peak occupancy: {occupancy_insights.get('peak_occupancy', 'Analysis not available')}
    
    Space utilization analysis: {occupancy_insights.get('space_utilization', 'Standard utilization patterns observed')}
    """
    story.append(Paragraph(occupancy_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Action Items
    action_items = analysis.get('action_items', [])
    if action_items:
        story.append(Paragraph("Recommended Actions", styles['Heading2']))
        action_text = ""
        for i, action in enumerate(action_items, 1):
            action_text += f"{i}. {action}\n"
        story.append(Paragraph(action_text, styles['Normal']))
        story.append(Spacer(1, 20))
    
    # Alerts
    alerts = analysis.get('alerts', [])
    if alerts:
        story.append(Paragraph("Alerts & Notifications", styles['Heading2']))
        alert_text = ""
        for alert in alerts:
            alert_text += f"• {alert}\n"
        story.append(Paragraph(alert_text, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    print(f"✅ PDF report generated: {output_path}")
    return output_path


def run_daily_summary(logger=print):
    """Main function to run the daily office operations summary."""
    logger("🏢 Starting End-of-Day Office Log Summary...")
    
    # Load data
    data = load_building_data()
    if not data:
        return False
    
    # Analyze data with LLM
    logger("🤖 Analyzing building data with OpenAI...")
    analysis = analyze_data_with_llm(data)
    
    # Generate summary text
    summary_text = generate_summary_text(analysis)
    logger("📝 LLM Summary generated:")
    logger(summary_text)
    
    # Create PDF report
    logger("📄 Generating PDF report...")
    pdf_path = create_pdf_report(analysis)
    
    # Send to Slack
    logger("📤 Sending report to Slack...")
    result = send_office_ops_report(pdf_path, summary_text)
    
    if result:
        logger("✅ Daily office summary completed successfully!")
        return True
    else:
        logger("❌ Failed to send report to Slack")
        return False


if __name__ == "__main__":
    # This can be triggered at 18:30 local time via a scheduler
    run_daily_summary()