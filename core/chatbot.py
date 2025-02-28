import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langdetect import detect
from config.config import SUPPORTED_LANGUAGES
from utils.logger import log_info, log_error
from core.classifier import classify_cybercrime
from core.response_generator import generate_response
from core.threat_analyzer import analyze_threats
from database.supabase_client import insert_report

class Chatbot:
    def __init__(self):
        self.language = "en"
        log_info("Chatbot initialized")

    def detect_language(self, text):
        try:
            lang = detect(text)
            if lang in SUPPORTED_LANGUAGES:
                self.language = lang
            else:
                self.language = "en"
            log_info(f"Detected language: {self.language}")
        except Exception as e:
            log_error(f"Language detection failed: {str(e)}")
            self.language = "en"

    def set_language(self, lang):
        if lang in SUPPORTED_LANGUAGES:
            self.language = lang
            log_info(f"Language manually set to: {self.language}")
        else:
            log_error(f"Unsupported language requested: {lang}")

    def process_input(self, user_input, user_id="anonymous"):
        self.detect_language(user_input)
        
        # Check for special command "trends"
        if user_input.lower().strip() == "trends":
            log_info(f"User {user_id} requested threat trends")
            return analyze_threats()

        # Normal cybercrime reporting
        crime_type = classify_cybercrime(user_input)
        log_info(f"Classified crime type: {crime_type}")
        
        insert_report(user_id, self.language, crime_type, user_input)
        response = generate_response(crime_type, self.language)
        return response

if __name__ == "__main__":
    bot = Chatbot()
    test_input = "I received a phishing email"
    response = bot.process_input(test_input)
    print(response)
    # Test trends
    trends_response = bot.process_input("trends")
    print(trends_response)