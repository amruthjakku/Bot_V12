import google.generativeai as genai
from config.config import GEMINI_API_KEY
from utils.logger import log_info, log_error

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Define cybercrime categories
CYBERCRIME_CATEGORIES = ["phishing", "hacking", "fraud", "cyberbullying", "unknown"]

def classify_cybercrime(user_input):
    try:
        log_info(f"Attempting to classify input: {user_input}")
        # Use a corrected model name (assuming gemini-1.5-pro is available)
        model = genai.GenerativeModel("gemini-1.5-pro")

        # Prompt for classification
        prompt = f"""
        Classify the following user input into one of these cybercrime categories: {', '.join(CYBERCRIME_CATEGORIES)}.
        If it doesn't fit, return 'unknown'.
        Input: "{user_input}"
        Return only the category name as plain text.
        """

        # Call Gemini API
        response = model.generate_content(prompt)
        crime_type = response.text.strip()

        if crime_type in CYBERCRIME_CATEGORIES:
            log_info(f"Classified input as: {crime_type}")
            return crime_type
        else:
            log_error(f"Invalid classification from API: {crime_type}")
            return "unknown"

    except Exception as e:
        log_error(f"Classification failed: {str(e)}")
        # Fallback: Keyword-based classification
        input_lower = user_input.lower()
        if "phishing" in input_lower or "email" in input_lower:
            return "phishing"
        elif "hack" in input_lower:
            return "hacking"
        elif "stole" in input_lower or "fraud" in input_lower:
            return "fraud"
        elif "bullying" in input_lower or "harass" in input_lower:
            return "cyberbullying"
        else:
            return "unknown"

if __name__ == "__main__":
    test_input = "Someone stole my credit card details online"
    result = classify_cybercrime(test_input)
    print(f"Crime type: {result}")