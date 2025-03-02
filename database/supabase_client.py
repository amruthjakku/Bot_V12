import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client, Client
from config.config import SUPABASE_URL, SUPABASE_KEY
from utils.logger import log_info, log_error
from collections import Counter

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_report(user_id: str, language: str, crime_type: str, report_data: dict):
    try:
        data = {
            "user_id": user_id,
            "language": language,
            "crime_type": crime_type,
            "username": report_data.get("username", ""),
            "phone": report_data.get("phone", ""),
            "residence": report_data.get("residence", ""),
            "user_input": report_data.get("incident", ""),
            "created_at": "now()"
        }
        log_info(f"Inserting report data: {data}")  # Log the exact data being sent
        response = supabase.table("reports").insert(data).execute()
        log_info(f"Inserted report for user {user_id}: {crime_type}")
        return response
    except Exception as e:
        log_error(f"Failed to insert report: {str(e)}")
        return None

def analyze_threats(limit=100):
    try:
        response = supabase.table("reports").select("crime_type").order("created_at", desc=True).limit(limit).execute()
        reports = response.data
        log_info(f"Fetched {len(reports)} reports for threat analysis")

        if not reports:
            return "No recent reports available for analysis."

        crime_counts = Counter(report["crime_type"] for report in reports)
        total_reports = sum(crime_counts.values())
        top_threats = crime_counts.most_common(3)
        analysis = "Recent Cyber Threat Trends:\n"
        for crime_type, count in top_threats:
            percentage = (count / total_reports) * 100
            analysis += f"- {crime_type}: {count} reports ({percentage:.1f}%)\n"

        log_info("Threat analysis completed")
        return analysis
    except Exception as e:
        log_error(f"Threat analysis failed: {str(e)}")
        return "Error analyzing threats. Please try again later."

if __name__ == "__main__":
    result = analyze_threats()
    print(result)