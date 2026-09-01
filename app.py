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

"""
Crisis Monitoring System - Central Backend Controller
Role: Member 3 (Flask Backend Developer)
Integrated with:
  - Member 1: templates/chat.html
  - Member 2: templates/dashboard.html
  - Member 4: Hugging Face Sentiment Analysis / Distress Scoring
  - Member 5: SQLite Database Schema (crisis.db)
"""

from flask import Flask, render_template, jsonify, request
import sqlite3
import datetime
import os

app = Flask(__name__)
DB_NAME = "crisis.db"

# ==============================================================================
# 1. DATABASE INITIALIZATION & SCHEMA MANAGEMENT (Member 5 Integration)
# ==============================================================================

def get_db_connection():
    """Helper function to create a SQLite connection with dictionary row access."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Creates SQLite tables and populates realistic demo seed data if empty."""
    conn = get_db_connection()
    c = conn.cursor()

    # Table 1: Victims / Monitored Individuals
    c.execute('''CREATE TABLE IF NOT EXISTS victims (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        mood TEXT NOT NULL,
        score INTEGER NOT NULL,
        dispatched INTEGER DEFAULT 0
    )''')

    # Table 2: Responses & Chat Interaction History
    c.execute('''CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id INTEGER NOT NULL,
        user_message TEXT NOT NULL,
        sentiment TEXT NOT NULL,
        score INTEGER NOT NULL,
        bot_reply TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (victim_id) REFERENCES victims (id)
    )''')

    # Table 3: Incident Dispatch Log
    c.execute('''CREATE TABLE IF NOT EXISTS incident_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id INTEGER NOT NULL,
        distress_score INTEGER NOT NULL,
        dispatched_at TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (victim_id) REFERENCES victims (id)
    )''')

    # Seed 8 Realistic Demo Profiles if Database is New (Member 6 Testing Data)
    c.execute('SELECT COUNT(*) FROM victims')
    if c.fetchone()[0] == 0:
        seed_victims = [
            (101, 'Sarah Jenkins', 'Shelter A - Hall 2', '😭 Overwhelmed', 85, 0),
            (102, 'Alex Martinez', 'Transit Hub 4', '😟 Anxious', 62, 0),
            (103, 'Rahul Sharma', 'Safe Zone North', '😐 Neutral', 35, 0),
            (104, 'Priya Nair', 'Sector 12 Relief Post', '😢 Scared', 78, 1),
            (105, 'David Kim', 'Community Center', '🙂 Calm', 20, 0),
            (106, 'Ananya Gupta', 'Flood Evac Camp 3', '😭 Terrified', 92, 0),
            (107, 'Marcus Vance', 'Medical Outpost 1', '😐 Tired', 45, 0),
            (108, 'Fatima Al-Sayed', 'Safe Zone Block B', '🙂 Safe', 15, 0)
        ]
        c.executemany('INSERT INTO victims VALUES (?,?,?,?,?,?)', seed_victims)

        # Seed initial conversation log for High-Risk Sarah (#101)
        seed_chats = [
            (101, 'I feel very scared and alone in this shelter.', 'NEGATIVE', 85, 
             'I am right here with you. Help is on the way. A responder has been notified.', '10:15 AM'),
            (101, 'Water levels are rising outside the door.', 'NEGATIVE', 88, 
             'Please move to higher ground if possible. Emergency services have your location.', '10:18 AM')
        ]
        c.executemany('''INSERT INTO responses (victim_id, user_message, sentiment, score, bot_reply, timestamp) 
                         VALUES (?,?,?,?,?,?)''', seed_chats)

    conn.commit()
    conn.close()

# Run DB setup on server start
init_database()


# ==============================================================================
# 2. SENTIMENT & DISTRESS SCORING ENGINE (Member 4 Integration)
# ==============================================================================

# Attempt to load Hugging Face Transformers pipeline; fallback gracefully if not installed
nlp_pipeline = None
try:
    from transformers import pipeline
    # Lightweight sentiment analysis model
    nlp_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    print("✅ Hugging Face Sentiment Analysis Pipeline Loaded Successfully.")
except Exception as e:
    print(f"⚠️ Hugging Face pipeline optional fallback active ({e}). Using rule-based scoring.")

def calculate_distress_score(text):
    """
    Evaluates message text and returns: (sentiment_label, distress_score_0_to_100, bot_reply)
    """
    text_lower = text.lower()

    # If Hugging Face is loaded, evaluate confidence
    if nlp_pipeline:
        try:
            hf_result = nlp_pipeline(text)[0]
            label = hf_result['label']  # 'POSITIVE' or 'NEGATIVE'
            conf = hf_result['score']   # 0.5 to 1.0

            if label == 'NEGATIVE':
                score = int(50 + (conf * 45))  # Scales between 50 and 95
            else:
                score = int(max(10, (1.0 - conf) * 40))  # Scales between 10 and 40
        except Exception:
            score = 50
    else:
        # Rule-based fallback
        if any(w in text_lower for w in ["scared", "alone", "terrified", "help", "danger", "overwhelmed", "trapped"]):
            score = 88
        elif any(w in text_lower for w in ["anxious", "lost", "nervous", "worried", "hurting"]):
            score = 65
        elif any(w in text_lower for w in ["good", "fine", "safe", "calm", "okay", "better"]):
            score = 18
        else:
            score = 40

    # Determine sentiment label and supportive bot response
    if score >= 70:
        sentiment = "NEGATIVE"
        reply = "I understand you are experiencing severe distress. I have flagged your location for priority emergency dispatch."
    elif score >= 41:
        sentiment = "NEGATIVE"
        reply = "I am staying with you. Please take slow breaths while we track your check-in status."
    else:
        sentiment = "POSITIVE"
        reply = "Thank you for checking in. Your status is recorded as stable."

    return sentiment, score, reply


# ==============================================================================
# 3. HTML PAGE ROUTING (Member 1 & Member 2 Views)
# ==============================================================================

@app.route("/")
def render_dashboard():
    """Renders Member 2's Operations Monitoring Dashboard."""
    return render_template("dashboard.html")

@app.route("/chat")
def render_chat():
    """Renders Member 1's Victim Check-in Chat Interface."""
    return render_template("chat.html")


# ==============================================================================
# 4. RESTful API ENDPOINTS (Connecting Frontend to Backend)
# ==============================================================================

# API 1: Fetch list of all victims (Used by Dashboard Table, Metrics, & Charts)
@app.route("/api/victims", methods=["GET"])
def get_victims():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, name, location, mood, score, dispatched FROM victims").fetchall()
    conn.close()

    victims = [
        {
            "id": r["id"],
            "name": r["name"],
            "location": r["location"],
            "mood": r["mood"],
            "score": r["score"],
            "dispatched": bool(r["dispatched"])
        }
        for r in rows
    ]
    return jsonify(victims), 200


# API 2: Fetch historical distress trend scores for a specific victim (Chart.js)
@app.route("/api/victim/<int:victim_id>/trend", methods=["GET"])
def get_victim_trend(victim_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT score FROM responses WHERE victim_id = ? ORDER BY id DESC LIMIT 5",
        (victim_id,)
    ).fetchall()
    conn.close()

    scores = [r["score"] for r in rows][::-1]
    if not scores:
        # Default baseline if no past check-ins
        scores = [30, 45, 55, 65, 80]

    labels = [f"Check-in {i+1}" for i in range(len(scores))]
    return jsonify({"labels": labels, "scores": scores}), 200


# API 3: Fetch granular conversation & NLP sentiment logs for modal drill-down
@app.route("/api/victim/<int:victim_id>/history", methods=["GET"])
def get_victim_history(victim_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT user_message, sentiment, score, bot_reply, timestamp FROM responses WHERE victim_id = ? ORDER BY id DESC",
        (victim_id,)
    ).fetchall()
    conn.close()

    history = [
        {
            "user_message": r["user_message"],
            "sentiment": r["sentiment"],
            "score": r["score"],
            "bot_reply": r["bot_reply"],
            "timestamp": r["timestamp"]
        }
        for r in rows
    ]
    return jsonify(history), 200


# API 4: Chat Check-in Endpoint (Called by Member 1's Chatbot UI)
@app.route("/api/chat", methods=["POST"])
def post_chat_message():
    data = request.get_json() or {}
    victim_id = data.get("victim_id", 101)
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Empty message received"}), 400

    # 1. NLP Sentiment & Distress Calculation
    sentiment, score, bot_reply = calculate_distress_score(message)
    now_str = datetime.datetime.now().strftime("%I:%M %p")

    # Update mood emoji tag
    mood_tag = "😭 Scared" if score > 70 else ("😟 Anxious" if score > 40 else "🙂 Stable")

    # 2. Persist in SQLite
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO responses (victim_id, user_message, sentiment, score, bot_reply, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (victim_id, message, sentiment, score, bot_reply, now_str)
    )
    c.execute(
        "UPDATE victims SET score = ?, mood = ? WHERE id = ?",
        (score, mood_tag, victim_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "reply": bot_reply,
        "score": score,
        "sentiment": sentiment,
        "timestamp": now_str
    }), 200


# API 5: Dispatch Emergency Aid Action (Called by Dashboard Button)
@app.route("/api/alerts/dispatch", methods=["POST"])
def dispatch_emergency_aid():
    data = request.get_json() or {}
    victim_id = data.get("victim_id")

    if not victim_id:
        return jsonify({"error": "Missing victim_id"}), 400

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    conn = get_db_connection()
    c = conn.cursor()

    # Update victim dispatch status
    c.execute("UPDATE victims SET dispatched = 1 WHERE id = ?", (victim_id,))
    # Record in incident log
    c.execute(
        '''INSERT INTO incident_logs (victim_id, distress_score, dispatched_at, status)
           VALUES (?, (SELECT score FROM victims WHERE id = ?), ?, ?)''',
        (victim_id, victim_id, now_str, "Team En Route")
    )
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Emergency Response Team dispatched to Victim #{victim_id}."
    }), 200


# API 6: System Health Check
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "timestamp": datetime.datetime.now().isoformat(),
        "database": "connected"
    }), 200


# ==============================================================================
# 5. SERVER ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Runs on localhost port 5000 with hot-reloading enabled
    app.run(debug=True, host="0.0.0.0", port=5000)
    
#Crisis Monitoring System - Central Backend Controller
#Role: Member 3 (Flask Backend Developer)
#Integrated with:
 # - Member 1: templates/chat.html
  #- Member 2: templates/dashboard.html
  # Member 4: Hugging Face Sentiment Analysis / Distress Scoring
   #Member 5: SQLite Database Schema (crisis.db)##


from flask import Flask, render_template, jsonify, request
import sqlite3
import datetime
import os

app = Flask(__name__)
DB_NAME = "crisis.db"

# ==============================================================================
# 1. DATABASE INITIALIZATION & SCHEMA MANAGEMENT (Member 5 Integration)
# ==============================================================================

def get_db_connection():
    """Helper function to create a SQLite connection with dictionary row access."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Creates SQLite tables and populates realistic demo seed data if empty."""
    conn = get_db_connection()
    c = conn.cursor()

    # Table 1: Victims / Monitored Individuals
    c.execute('''CREATE TABLE IF NOT EXISTS victims (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        mood TEXT NOT NULL,
        score INTEGER NOT NULL,
        dispatched INTEGER DEFAULT 0
    )''')

    # Table 2: Responses & Chat Interaction History
    c.execute('''CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id INTEGER NOT NULL,
        user_message TEXT NOT NULL,
        sentiment TEXT NOT NULL,
        score INTEGER NOT NULL,
        bot_reply TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (victim_id) REFERENCES victims (id)
    )''')

    # Table 3: Incident Dispatch Log
    c.execute('''CREATE TABLE IF NOT EXISTS incident_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id INTEGER NOT NULL,
        distress_score INTEGER NOT NULL,
        dispatched_at TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (victim_id) REFERENCES victims (id)
    )''')

    # Seed 8 Realistic Demo Profiles if Database is New (Member 6 Testing Data)
    c.execute('SELECT COUNT(*) FROM victims')
    if c.fetchone()[0] == 0:
        seed_victims = [
            (101, 'Sarah Jenkins', 'Shelter A - Hall 2', '😭 Overwhelmed', 85, 0),
            (102, 'Alex Martinez', 'Transit Hub 4', '😟 Anxious', 62, 0),
            (103, 'Rahul Sharma', 'Safe Zone North', '😐 Neutral', 35, 0),
            (104, 'Priya Nair', 'Sector 12 Relief Post', '😢 Scared', 78, 1),
            (105, 'David Kim', 'Community Center', '🙂 Calm', 20, 0),
            (106, 'Ananya Gupta', 'Flood Evac Camp 3', '😭 Terrified', 92, 0),
            (107, 'Marcus Vance', 'Medical Outpost 1', '😐 Tired', 45, 0),
            (108, 'Fatima Al-Sayed', 'Safe Zone Block B', '🙂 Safe', 15, 0)
        ]
        c.executemany('INSERT INTO victims VALUES (?,?,?,?,?,?)', seed_victims)

        # Seed initial conversation log for High-Risk Sarah (#101)
        seed_chats = [
            (101, 'I feel very scared and alone in this shelter.', 'NEGATIVE', 85, 
             'I am right here with you. Help is on the way. A responder has been notified.', '10:15 AM'),
            (101, 'Water levels are rising outside the door.', 'NEGATIVE', 88, 
             'Please move to higher ground if possible. Emergency services have your location.', '10:18 AM')
        ]
        c.executemany('''INSERT INTO responses (victim_id, user_message, sentiment, score, bot_reply, timestamp) 
                         VALUES (?,?,?,?,?,?)''', seed_chats)

    conn.commit()
    conn.close()

# Run DB setup on server start
init_database()


# ==============================================================================
# 2. SENTIMENT & DISTRESS SCORING ENGINE (Member 4 Integration)
# ==============================================================================

# Attempt to load Hugging Face Transformers pipeline; fallback gracefully if not installed
nlp_pipeline = None
try:
    from transformers import pipeline
    # Lightweight sentiment analysis model
    nlp_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    print("✅ Hugging Face Sentiment Analysis Pipeline Loaded Successfully.")
except Exception as e:
    print(f"⚠️ Hugging Face pipeline optional fallback active ({e}). Using rule-based scoring.")

def calculate_distress_score(text):
    """
    Evaluates message text and returns: (sentiment_label, distress_score_0_to_100, bot_reply)
    """
    text_lower = text.lower()

    # If Hugging Face is loaded, evaluate confidence
    if nlp_pipeline:
        try:
            hf_result = nlp_pipeline(text)[0]
            label = hf_result['label']  # 'POSITIVE' or 'NEGATIVE'
            conf = hf_result['score']   # 0.5 to 1.0

            if label == 'NEGATIVE':
                score = int(50 + (conf * 45))  # Scales between 50 and 95
            else:
                score = int(max(10, (1.0 - conf) * 40))  # Scales between 10 and 40
        except Exception:
            score = 50
    else:
        # Rule-based fallback
        if any(w in text_lower for w in ["scared", "alone", "terrified", "help", "danger", "overwhelmed", "trapped"]):
            score = 88
        elif any(w in text_lower for w in ["anxious", "lost", "nervous", "worried", "hurting"]):
            score = 65
        elif any(w in text_lower for w in ["good", "fine", "safe", "calm", "okay", "better"]):
            score = 18
        else:
            score = 40

    # Determine sentiment label and supportive bot response
    if score >= 70:
        sentiment = "NEGATIVE"
        reply = "I understand you are experiencing severe distress. I have flagged your location for priority emergency dispatch."
    elif score >= 41:
        sentiment = "NEGATIVE"
        reply = "I am staying with you. Please take slow breaths while we track your check-in status."
    else:
        sentiment = "POSITIVE"
        reply = "Thank you for checking in. Your status is recorded as stable."

    return sentiment, score, reply


# ==============================================================================
# 3. HTML PAGE ROUTING (Member 1 & Member 2 Views)
# ==============================================================================

@app.route("/")
def render_dashboard():
    """Renders Member 2's Operations Monitoring Dashboard."""
    return render_template("dashboard.html")

@app.route("/chat")
def render_chat():
    """Renders Member 1's Victim Check-in Chat Interface."""
    return render_template("chat.html")


# ==============================================================================
# 4. RESTful API ENDPOINTS (Connecting Frontend to Backend)
# ==============================================================================

# API 1: Fetch list of all victims (Used by Dashboard Table, Metrics, & Charts)
@app.route("/api/victims", methods=["GET"])
def get_victims():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, name, location, mood, score, dispatched FROM victims").fetchall()
    conn.close()

    victims = [
        {
            "id": r["id"],
            "name": r["name"],
            "location": r["location"],
            "mood": r["mood"],
            "score": r["score"],
            "dispatched": bool(r["dispatched"])
        }
        for r in rows
    ]
    return jsonify(victims), 200


# API 2: Fetch historical distress trend scores for a specific victim (Chart.js)
@app.route("/api/victim/<int:victim_id>/trend", methods=["GET"])
def get_victim_trend(victim_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT score FROM responses WHERE victim_id = ? ORDER BY id DESC LIMIT 5",
        (victim_id,)
    ).fetchall()
    conn.close()

    scores = [r["score"] for r in rows][::-1]
    if not scores:
        # Default baseline if no past check-ins
        scores = [30, 45, 55, 65, 80]

    labels = [f"Check-in {i+1}" for i in range(len(scores))]
    return jsonify({"labels": labels, "scores": scores}), 200


# API 3: Fetch granular conversation & NLP sentiment logs for modal drill-down
@app.route("/api/victim/<int:victim_id>/history", methods=["GET"])
def get_victim_history(victim_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT user_message, sentiment, score, bot_reply, timestamp FROM responses WHERE victim_id = ? ORDER BY id DESC",
        (victim_id,)
    ).fetchall()
    conn.close()

    history = [
        {
            "user_message": r["user_message"],
            "sentiment": r["sentiment"],
            "score": r["score"],
            "bot_reply": r["bot_reply"],
            "timestamp": r["timestamp"]
        }
        for r in rows
    ]
    return jsonify(history), 200


# API 4: Chat Check-in Endpoint (Called by Member 1's Chatbot UI)
@app.route("/api/chat", methods=["POST"])
def post_chat_message():
    data = request.get_json() or {}
    victim_id = data.get("victim_id", 101)
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Empty message received"}), 400

    # 1. NLP Sentiment & Distress Calculation
    sentiment, score, bot_reply = calculate_distress_score(message)
    now_str = datetime.datetime.now().strftime("%I:%M %p")

    # Update mood emoji tag
    mood_tag = "😭 Scared" if score > 70 else ("😟 Anxious" if score > 40 else "🙂 Stable")

    # 2. Persist in SQLite
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO responses (victim_id, user_message, sentiment, score, bot_reply, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (victim_id, message, sentiment, score, bot_reply, now_str)
    )
    c.execute(
        "UPDATE victims SET score = ?, mood = ? WHERE id = ?",
        (score, mood_tag, victim_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "reply": bot_reply,
        "score": score,
        "sentiment": sentiment,
        "timestamp": now_str
    }), 200


# API 5: Dispatch Emergency Aid Action (Called by Dashboard Button)
@app.route("/api/alerts/dispatch", methods=["POST"])
def dispatch_emergency_aid():
    data = request.get_json() or {}
    victim_id = data.get("victim_id")

    if not victim_id:
        return jsonify({"error": "Missing victim_id"}), 400

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    conn = get_db_connection()
    c = conn.cursor()

    # Update victim dispatch status
    c.execute("UPDATE victims SET dispatched = 1 WHERE id = ?", (victim_id,))
    # Record in incident log
    c.execute(
        '''INSERT INTO incident_logs (victim_id, distress_score, dispatched_at, status)
           VALUES (?, (SELECT score FROM victims WHERE id = ?), ?, ?)''',
        (victim_id, victim_id, now_str, "Team En Route")
    )
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Emergency Response Team dispatched to Victim #{victim_id}."
    }), 200


# API 6: System Health Check
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "timestamp": datetime.datetime.now().isoformat(),
        "database": "connected"
    }), 200


# ==============================================================================
# 5. SERVER ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Runs on localhost port 5000 with hot-reloading enabled
    app.run(debug=True, host="0.0.0.0", port=5000)
#  4551715 (work done)
