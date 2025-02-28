from config.languages import RESPONSE_TEMPLATES
from utils.logger import log_info, log_error

def generate_response(crime_type, language="en"):
    try:
        if language not in ["en", "hi", "te"]:
            language = "en"
            log_error(f"Unsupported language, defaulting to English")

        if crime_type in RESPONSE_TEMPLATES:
            response = RESPONSE_TEMPLATES[crime_type][language]
        else:
            response = RESPONSE_TEMPLATES["unknown"][language]

        log_info(f"Generated response for {crime_type} in {language}")
        return response

    except Exception as e:
        log_error(f"Response generation failed: {str(e)}")
        return "Sorry, something went wrong. Please try again."

if __name__ == "__main__":
    test_crime = "phishing"
    test_lang = "en"
    print(generate_response(test_crime, test_lang))