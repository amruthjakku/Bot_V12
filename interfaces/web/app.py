import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, render_template, request, jsonify, session
from config.config import GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
from utils.logger import log_info, log_error
import google.generativeai as genai
from supabase import create_client, Client
from langdetect import detect
from config.config import SUPPORTED_LANGUAGES

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # For session management

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cybercrime categories
CYBERCRIME_CATEGORIES = ["phishing", "hacking", "fraud", "cyberbullying", "unknown"]

@app.route('/')
def index():
    session.clear()  # Reset session for a new report
    session['report'] = {}
    log_info("Web interface loaded")
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        step = data.get('step', 'username')
        user_input = data.get('message', '').strip()
        user_id = session.get('user_id', 'web_anonymous_' + str(os.urandom(4).hex()))

        if 'report' not in session:
            session['report'] = {'user_id': user_id}

        report = session['report']

        if step == 'username':
            report['username'] = user_input
            log_info(f"User {user_id} provided username: {user_input}")
            return jsonify({'response': "Great! Now, please provide your phone number:", 'next_step': 'phone'})

        elif step == 'phone':
            if not user_input.isdigit() or len(user_input) < 7:
                return jsonify({'response': "Please enter a valid phone number (digits only):", 'next_step': 'phone'})
            report['phone'] = user_input
            log_info(f"User {user_id} provided phone: {user_input}")
            return jsonify({'response': "Thanks! Where do you reside (city/state)?", 'next_step': 'residence'})

        elif step == 'residence':
            report['residence'] = user_input
            log_info(f"User {user_id} provided residence: {user_input}")
            return jsonify({'response': "Got it! Please describe the cybercrime incident:", 'next_step': 'incident'})

        elif step == 'incident':
            report['incident'] = user_input
            lang = detect(user_input)
            report['language'] = lang if lang in SUPPORTED_LANGUAGES else "en"
            log_info(f"User {user_id} provided incident: {user_input}")
            followup_question = generate_followup(user_input, "Ask about the timing or method of the incident.")
            session['followup_question_1'] = followup_question
            return jsonify({'response': followup_question, 'next_step': 'followup_1'})

        elif step == 'followup_1':
            report['incident'] += f"\nDetails 1: {user_input}"
            log_info(f"User {user_id} provided followup_1: {user_input}")
            followup_question = generate_followup(report['incident'], "Ask about the impact or evidence of the incident.")
            session['followup_question_2'] = followup_question
            return jsonify({'response': followup_question, 'next_step': 'followup_2'})

        elif step == 'followup_2':
            report['incident'] += f"\nDetails 2: {user_input}"
            log_info(f"User {user_id} provided followup_2: {user_input}")
            crime_type = classify_incident(report['incident'])
            report['crime_type'] = crime_type
            summary = (
                f"Please confirm your report:\n"
                f"Name: {report['username']}\n"
                f"Phone: {report['phone']}\n"
                f"Residence: {report['residence']}\n"
                f"Incident: {report['incident']}\n"
                f"Type: {crime_type}\n\n"
                "Type 'yes' to submit or 'no' to cancel."
            )
            return jsonify({'response': summary, 'next_step': 'confirm'})

        elif step == 'confirm':
            if user_input.lower() == 'yes':
                response = generate_response(report['crime_type'], report['language'])
                if save_report(report):
                    result = (
                        f"Report submitted successfully!\n\n"
                        f"Summary:\n"
                        f"Name: {report['username']}\n"
                        f"Phone: {report['phone']}\n"
                        f"Residence: {report['residence']}\n"
                        f"Incident: {report['incident']}\n\n"
                        f"Response: {response}"
                    )
                    session.clear()
                    return jsonify({'response': result, 'next_step': 'done'})
                else:
                    return jsonify({'response': "Error saving report to Supabase.", 'next_step': 'error'})
            elif user_input.lower() == 'no':
                session.clear()
                return jsonify({'response': "Report canceled.", 'next_step': 'done'})
            else:
                return jsonify({'response': "Please type 'yes' or 'no'.", 'next_step': 'confirm'})

    except Exception as e:
        log_error(f"Web chat error: {str(e)}")
        return jsonify({'response': "Something went wrong. Please try again.", 'next_step': 'error'}), 500

# Helper functions
def generate_followup(incident: str, instruction: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = f"Incident: '{incident}'. {instruction} Return a concise question."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        log_error(f"Gemini API failed: {str(e)}")
        return "Can you provide more details about what happened?"

def classify_incident(incident: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = f"""
        Classify this incident into one of: {', '.join(CYBERCRIME_CATEGORIES)}.
        Incident: "{incident}"
        Return only the category name.
        """
        response = model.generate_content(prompt)
        crime_type = response.text.strip()
        return crime_type if crime_type in CYBERCRIME_CATEGORIES else "unknown"
    except Exception as e:
        log_error(f"Classification failed: {str(e)}")
        return "unknown"

def generate_response(crime_type: str, language: str) -> str:
    RESPONSE_TEMPLATES = {
        "phishing": {
            "en": "This seems like phishing. Report it to cybercrime.gov.in. Legal: IT Act Section 66C.",
            "hi": "यह फ़िशिंग जैसा है। cybercrime.gov.in पर रिपोर्ट करें। कानूनी: आईटी अधिनियम धारा 66C।",
            "te": "ఇది ఫిషింగ్ లాగా ఉంది. cybercrime.gov.inకు రిపోర్ట్ చేయండి। చట్టం: ఐటీ చట్టం సెక్షన్ 66C."
        },
        "hacking": {
            "en": "This may be hacking. Report to cybercrime.gov.in. Legal: IT Act Section 66.",
            "hi": "यह हैकिंग हो सकती है। cybercrime.gov.in पर रिपोर्ट करें। कानूनी: आईटी अधिनियम धारा 66।",
            "te": "ఇది హ్యాకింగ్ కావచ్చు. cybercrime.gov.inకు రిపోర్ట్ చేయండి। చట్టం: ఐటీ చట్టం సెక్షన్ 66."
        },
        "fraud": {
            "en": "This looks like fraud. Report to cybercrime.gov.in or your bank. Legal: IT Act Section 66D.",
            "hi": "यह धोखाधड़ी जैसा है। cybercrime.gov.in या बैंक को रिपोर्ट करें। कानूनी: आईटी अधिनियम धारा 66D।",
            "te": "ఇది మోసం లాగా ఉంది. cybercrime.gov.in లేదా మీ బ్యాంకుకు రిపోర్ట్ చేయండి। చట్టం: ఐటీ చట్టం సెక్షన్ 66D."
        },
        "cyberbullying": {
            "en": "This is cyberbullying. Report to the platform and cybercrime.gov.in. Legal: IT Act Section 67.",
            "hi": "यह साइबरबुलिंग है। प्लेटफॉर्म और cybercrime.gov.in पर रिपोर्ट करें। कानूनी: आईटी अधिनियम धारा 67।",
            "te": "ఇది సైబర్‌బుల్లింగ్. ప్లాట్‌ఫారమ్ మరియు cybercrime.gov.inకు రిపోర్ట్ చేయండి। చట్టం: ఐటీ చట్టం సెక్షన్ 67."
        },
        "unknown": {
            "en": "Couldn’t classify this. Report to cybercrime.gov.in with more details.",
            "hi": "इसे वर्गीकृत नहीं कर सका। cybercrime.gov.in पर अधिक विवरण के साथ रिपोर्ट करें।",
            "te": "దీనిని వర్గీకరించలేకపోయాను. cybercrime.gov.inకు మరిన్ని వివరాలతో రిపోర్ట్ చేయండి."
        }
    }
    return RESPONSE_TEMPLATES.get(crime_type, {}).get(language, RESPONSE_TEMPLATES["unknown"]["en"])

def save_report(report: dict) -> bool:
    try:
        data = {
            "user_id": report['user_id'],
            "language": report['language'],
            "crime_type": report['crime_type'],
            "username": report['username'],
            "phone": report['phone'],
            "residence": report['residence'],
            "user_input": report['incident'],
            "created_at": "now()"
        }
        log_info(f"Attempting to save report: {data}")
        response = supabase.table("reports").insert(data).execute()
        log_info(f"Report saved successfully: {response.data}")
        return True
    except Exception as e:
        log_error(f"Failed to save report: {str(e)}")
        return False

if __name__ == "__main__":
    log_info("Starting Flask web server...")
    app.run(debug=True, host='0.0.0.0', port=5001)