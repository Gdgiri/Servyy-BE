from flask import Flask, request, jsonify
from flask_cors import CORS
from chatbot import get_sales_ai_response
import logging
import uuid

# Initialize Flask app
app = Flask(__name__)
CORS(app)  


CORS(app, resources={r"/*": {"origins": "https://servyy-ai-fe.netlify.app"}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/chat', methods=['POST'])
def chat():
    """
    Single endpoint for Sales AI chat

    Expected JSON body:
    {
        "message": "Your sales question or request",
        "user_id": "optional - unique user identifier"
    }

    Returns:
    {
        "response": "AI response",
        "user_id": "unique_user_id_for_this_session",
        "status": "success"
    }
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field", "status": "error"}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty", "status": "error"}), 400

        # Auto-generate user_id if missing
        user_id = str(data.get('user_id') or uuid.uuid4())
        if 'user_id' not in data or not str(data['user_id']).strip():
            logger.info(f"Generated new user_id: {user_id}")
        else:
            user_id = str(data['user_id']).strip()

        # Get AI response (loads last 10 turns from single-row memory)
        logger.info(f"Processing message for user {user_id}: {user_message[:50]}...")
        ai_response = get_sales_ai_response(user_message, user_id)

        # Return response including user_id for frontend to keep
        return jsonify({
            "response": ai_response,
            "user_id": user_id,
            "status": "success"
        }), 200

    except Exception as e:
        logger.error(f"Error processing request for user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error occurred", "status": "error"}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found. Use POST /chat", "status": "error"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed. Use POST request", "status": "error"}), 405


if __name__ == '__main__':
    print("🚀 Starting Sales AI Flask Server...")
    print("📍 Available endpoint: POST /chat")
    print("📝 Expected JSON: {'message': 'your sales question', 'user_id': 'optional'}")
    print("🔗 Example: curl -X POST http://localhost:5000/chat -H 'Content-Type: application/json' -d '{\"message\":\"Help me write a cold email\"}'")
    print("-" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)

