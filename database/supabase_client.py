import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client, Client
from config.config import SUPABASE_URL, SUPABASE_KEY
from utils.logger import log_info, log_error

# Initialize Supabase client with minimal options
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_report(user_id: str, language: str, crime_type: str, details: str):
    try:
        data = {
            "user_id": user_id,
            "language": language,
            "crime_type": crime_type,
            "details": details
        }
        response = supabase.table("reports").insert(data).execute()
        log_info(f"Report inserted for user {user_id}: {crime_type}")
        return response.data
    except Exception as e:
        log_error(f"Failed to insert report: {str(e)}")
        return None

if __name__ == "__main__":
    test_report = insert_report("test_user", "en", "phishing", "I received a phishing email")
    print(test_report)