import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, render_template, request, jsonify
from core.chatbot import Chatbot
from utils.logger import log_info, log_error

app = Flask(__name__)
chatbot = Chatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '')
        user_id = data.get('user_id', 'web_anonymous')
        log_info(f"Web request from {user_id}: {user_input}")
        
        response = chatbot.process_input(user_input, user_id)
        return jsonify({'response': response})
    except Exception as e:
        log_error(f"Web chat error: {str(e)}")
        return jsonify({'response': "Sorry, something went wrong."}), 500

if __name__ == "__main__":
    log_info("Starting Flask web server...")
    app.run(debug=True, host='0.0.0.0', port=5001)  # Changed to port 5001