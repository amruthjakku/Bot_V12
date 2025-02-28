import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client, Client
from config.config import SUPABASE_URL, SUPABASE_KEY
from utils.logger import log_info, log_error
from collections import Counter

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_threats(limit=100):
    try:
        # Fetch recent reports (last 100 entries as an example)
        response = supabase.table("reports").select("crime_type").order("created_at", desc=True).limit(limit).execute()
        reports = response.data
        log_info(f"Fetched {len(reports)} reports for threat analysis")

        if not reports:
            return "No recent reports available for analysis."

        # Count crime types
        crime_counts = Counter(report["crime_type"] for report in reports)
        total_reports = sum(crime_counts.values())

        # Identify top threats
        top_threats = crime_counts.most_common(3)  # Top 3 crime types
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