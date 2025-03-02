import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ConversationHandler
)
from telegram import Update
from config.config import TELEGRAM_TOKEN, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
from utils.logger import log_info, log_error
import google.generativeai as genai
from supabase import create_client, Client
from langdetect import detect
from config.config import SUPPORTED_LANGUAGES

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define conversation states
USERNAME, PHONE, RESIDENCE, INCIDENT, FOLLOWUP_1, FOLLOWUP_2, CONFIRM = range(7)

# Cybercrime categories
CYBERCRIME_CATEGORIES = ["phishing", "hacking", "fraud", "cyberbullying", "unknown"]

async def start(update: Update, context):
    user_id = str(update.message.from_user.id)
    log_info(f"User {user_id} started the bot")
    await update.message.reply_text(
        "Welcome to the Cybercrime Reporting Bot!\n"
        "I’ll guide you to report an incident. Cancel anytime with /cancel.\n"
        "First, please provide your name (or a username):"
    )
    context.user_data['report'] = {'user_id': user_id}
    return USERNAME

async def get_username(update: Update, context):
    user_id = str(update.message.from_user.id)
    username = update.message.text.strip()
    context.user_data['report']['username'] = username
    log_info(f"User {user_id} provided username: {username}")
    await update.message.reply_text("Great! Now, please provide your phone number:")
    return PHONE

async def get_phone(update: Update, context):
    user_id = str(update.message.from_user.id)
    phone = update.message.text.strip()
    if not phone.isdigit() or len(phone) < 7:
        await update.message.reply_text("Please enter a valid phone number (digits only):")
        return PHONE
    context.user_data['report']['phone'] = phone
    log_info(f"User {user_id} provided phone: {phone}")
    await update.message.reply_text("Thanks! Where do you reside (city/state)?")
    return RESIDENCE

async def get_residence(update: Update, context):
    user_id = str(update.message.from_user.id)
    residence = update.message.text.strip()
    context.user_data['report']['residence'] = residence
    log_info(f"User {user_id} provided residence: {residence}")
    await update.message.reply_text("Got it! Please describe the cybercrime incident:")
    return INCIDENT

async def get_incident(update: Update, context):
    user_id = str(update.message.from_user.id)
    incident = update.message.text.strip()
    context.user_data['report']['incident'] = incident
    log_info(f"User {user_id} provided incident: {incident}")

    # Detect language
    lang = detect(incident)
    context.user_data['report']['language'] = lang if lang in SUPPORTED_LANGUAGES else "en"

    # AI follow-up question 1
    followup_question = await generate_followup(incident, "Ask about the timing or method of the incident.")
    context.user_data['followup_question_1'] = followup_question
    await update.message.reply_text(followup_question)
    return FOLLOWUP_1

async def get_followup_1(update: Update, context):
    user_id = str(update.message.from_user.id)
    followup_1 = update.message.text.strip()
    context.user_data['report']['incident'] += f"\nDetails 1: {followup_1}"
    log_info(f"User {user_id} provided followup_1: {followup_1}")

    # AI follow-up question 2
    followup_question = await generate_followup(context.user_data['report']['incident'], 
                                               "Ask about the impact or evidence of the incident.")
    context.user_data['followup_question_2'] = followup_question
    await update.message.reply_text(followup_question)
    return FOLLOWUP_2

async def get_followup_2(update: Update, context):
    user_id = str(update.message.from_user.id)
    followup_2 = update.message.text.strip()
    context.user_data['report']['incident'] += f"\nDetails 2: {followup_2}"
    log_info(f"User {user_id} provided followup_2: {followup_2}")

    # Classify the incident
    crime_type = classify_incident(context.user_data['report']['incident'])
    context.user_data['report']['crime_type'] = crime_type

    # Show summary for confirmation
    report = context.user_data['report']
    summary = (
        f"Please confirm your report:\n"
        f"Name: {report['username']}\n"
        f"Phone: {report['phone']}\n"
        f"Residence: {report['residence']}\n"
        f"Incident: {report['incident']}\n"
        f"Type: {crime_type}\n\n"
        "Reply 'yes' to submit or 'no' to cancel."
    )
    await update.message.reply_text(summary)
    return CONFIRM

async def confirm_report(update: Update, context):
    user_id = str(update.message.from_user.id)
    confirmation = update.message.text.lower().strip()
    
    if confirmation == "yes":
        report = context.user_data['report']
        response = generate_response(report['crime_type'], report['language'])
        success = await save_report(report)
        
        if success:
            await update.message.reply_text(
                f"Report submitted successfully!\n\n"
                f"Summary:\n"
                f"Name: {report['username']}\n"
                f"Phone: {report['phone']}\n"
                f"Residence: {report['residence']}\n"
                f"Incident: {report['incident']}\n\n"
                f"Response: {response}"
            )
        else:
            error_msg = "Error saving report to Supabase. Check credentials or table schema."
            log_error(error_msg)
            await update.message.reply_text(error_msg)
        context.user_data.clear()
        return ConversationHandler.END
    elif confirmation == "no":
        await update.message.reply_text("Report canceled.")
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Please reply 'yes' or 'no'.")
        return CONFIRM

async def cancel(update: Update, context):
    user_id = str(update.message.from_user.id)
    log_info(f"User {user_id} canceled the report")
    await update.message.reply_text("Report canceled. Use /start to begin again.")
    context.user_data.clear()
    return ConversationHandler.END

# Helper functions
async def generate_followup(incident: str, instruction: str) -> str:
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

async def save_report(report: dict) -> bool:
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

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            RESIDENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_residence)],
            INCIDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_incident)],
            FOLLOWUP_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_followup_1)],
            FOLLOWUP_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_followup_2)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_report)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    log_info("Telegram bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()