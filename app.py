import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline

# Initialize Flask App and Enable CORS
app = Flask(__name__)
CORS(app) # Crucial: Allows the frontend HTML files to talk to this backend

# ---------------------------------------------------------
# 1. AI INITIALIZATION (Loads only once at startup)
# ---------------------------------------------------------
print("Loading AI Sentiment Model... please wait.")
sentiment_pipeline = pipeline("sentiment-analysis")
print("AI Model loaded successfully!")

# ---------------------------------------------------------
# 2. DATABASE INITIALIZATION (Safety check)
# ---------------------------------------------------------
def init_db():
    """Creates the database and tables if they don't exist yet."""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            victim_id INTEGER,
            message TEXT,
            score INTEGER,
            is_alert INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("Database verified/initialized.")

init_db()

# ---------------------------------------------------------
# 3. AI SCORING LOGIC
# ---------------------------------------------------------
def calculate_distress_score(text):
    """Generates a 0-100 distress score based on sentiment and keywords."""
    result = sentiment_pipeline(text)[0]
    confidence = result['score']
    
    # Base mapping
    if result['label'] == 'NEGATIVE':
        base_score = int(confidence * 100)
    else:
        base_score = int((1.0 - confidence) * 100)
        
    # Keyword bump for severe distress
    high_risk_words = ['scared', 'kill', 'hurt', 'threat', 'alone', 'terrified', 'die']
    if any(word in text.lower() for word in high_risk_words):
        base_score = min(100, base_score + 25) # Cap at 100
        
    return base_score

# ---------------------------------------------------------
# 4. FLASK API ROUTES
# ---------------------------------------------------------

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """Receives chat message, scores it, saves to DB, and returns data."""
    data = request.get_json()
    
    # Error handling if frontend sends empty data
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
        
    user_message = data.get('message', '')
    victim_id = data.get('victim_id', 1) # Defaulting to victim #1 for MVP
    
    # Process through AI
    distress_score = calculate_distress_score(user_message)
    is_alert = 1 if distress_score > 70 else 0
    
    # Save to SQLite
    try:
        conn = sqlite3.connect('database.db') 
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO responses (victim_id, message, score, is_alert)
            VALUES (?, ?, ?, ?)
        ''', (victim_id, user_message, distress_score, is_alert))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database write failed"}), 500

    # Return success payload to Frontend Chat UI
    return jsonify({
        "reply": "I am listening. Please tell me more.",
        "distress_score": distress_score,
        "alert": bool(is_alert)
    })

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    """Provides the latest 15 interactions for the Dashboard UI."""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Fetch data newest-first
        cursor.execute("SELECT id, victim_id, message, score, is_alert, timestamp FROM responses ORDER BY id DESC LIMIT 15")
        rows = cursor.fetchall()
        conn.close()
        
        # Format as a list of JSON objects
        data = [{
            "id": row[0], 
            "victim_id": row[1],
            "message": row[2], 
            "score": row[3], 
            "alert": bool(row[4]),
            "timestamp": row[5]
        } for row in rows]
        
        return jsonify(data)
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database read failed"}), 500

# ---------------------------------------------------------
# 5. SERVER RUN
# ---------------------------------------------------------
if __name__ == '__main__':
    # debug=True auto-reloads the server when you save code changes
    app.run(debug=True, port=5000)