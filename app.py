from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import random  # Used for generating mock data

app = Flask(__name__)
CORS(app)  
# Allows your Member 1 (Frontend) to connect from a different port
# ==========================================
# 🔌 INTEGRATION PLACEHOLDERS (MEMBERS 4 & 5)
# ==========================================

# TODO: Once Member 4 finishes their logic, uncomment and import it:
# from scoring_logic import calculate_threat_score

# TODO: Once Member 5 finishes the DB setup, uncomment and import it:
# from database import db_session, VictimModel, AlertModel

def mock_score_logic(text):
    """Temporary stand-in for Member 4's logic"""
    # Returns a deterministic risk score between 0 and 100 based on text length
    # just to provide predictable behavior during your initial route testing.
    return min(len(text) * 3, 100)


# ==========================================
# 🛑 CORE API ENDPOINTS (YOUR WORK)
# ==========================================

@app.route('/submit-response', methods=['POST'])
def submit_response():
    """
    Receives incoming victim chat text, runs it through the analyzer,
    and commits the results to the data layer.
    """
    try:
        data = request.get_json()
        
        # Validation
        if not data or 'victim_id' not in data or 'chat_input' not in data:
            return jsonify({"error": "Missing victim_id or chat_input in request body"}), 400
        
        victim_id = data['victim_id']
        chat_input = data['chat_input']
        
        # 1. Process via Member 4's engine
        # Real: threat_score = calculate_threat_score(chat_input)
        threat_score = mock_score_logic(chat_input)
        
        # 2. Save via Member 5's database layer
        # Real: 
        # new_entry = VictimModel(victim_id=victim_id, text=chat_input, score=threat_score, timestamp=datetime.utcnow())
        # db_session.add(new_entry)
        # if threat_score > 75:
        #     db_session.add(AlertModel(victim_id=victim_id, score=threat_score))
        # db_session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Response processed and saved successfully.",
            "data": {
                "victim_id": victim_id,
                "calculated_score": threat_score,
                "triggered_alert": threat_score > 75
            }
        }), 201

    except Exception as e:
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500


@app.route('/victims', methods=['GET'])
def get_victims():
    """
    Gathers a list of all unique victims and their overall current scores
    to populate Member 1's primary dashboard array.
    """
    try:
        # Real query (Member 5): Fetch the latest records grouped by victim_id
        # For now, we return a cleanly structured mock array matching frontend schemas:
        mock_victims_list = [
            {"victim_id": "V-101", "name": "Alex Rivera", "latest_score": 82, "status": "High Risk"},
            {"victim_id": "V-102", "name": "Jordan Lee", "latest_score": 45, "status": "Medium Risk"},
            {"victim_id": "V-103", "name": "Taylor Morgan", "latest_score": 19, "status": "Low Risk"}
        ]
        return jsonify(mock_victims_list), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/victim/<string:victim_id>/trend', methods=['GET'])
def get_victim_trend(victim_id):
    """
    Queries historical database records chronologically for a single victim id
    and formats them cleanly into timeline points for line-charting components.
    """
    try:
        # Real query (Member 5): 
        # records = db_session.query(VictimModel).filter_by(victim_id=victim_id).order_by(VictimModel.timestamp.asc()).all()
        
        # Quick check fallback validation
        if not victim_id:
            return jsonify({"error": "A valid victim ID must be specified in the URL path"}), 400

        # Generating mock chronological entries over the last 5 hours for the chart
        base_time = datetime.now()
        mock_trend_data = []
        current_score = random.randint(30, 60)
        
        for idx in range(5):
            timestamp = (base_time - timedelta(hours=5-idx)).strftime("%Y-%m-%d %H:%M:%S")
            current_score = max(0, min(100, current_score + random.randint(-15, 20)))
            mock_trend_data.append({
                "timestamp": timestamp,
                "score": current_score
            })
            
        return jsonify({
            "victim_id": victim_id,
            "trend": mock_trend_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Filters and aggregates real-time structural logs to pull out only high priority cases
    where critical scoring safety thresholds have been broken.
    """
    try:
        # Real query (Member 5): db_session.query(AlertModel).all()
        mock_alerts = [
            {
                "alert_id": "A-901",
                "victim_id": "V-101",
                "severity": "Critical",
                "score": 82,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        return jsonify(mock_alerts), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# 🚀 EXECUTION LAYER
# ==========================================
if __name__ == '__main__':
    # Runs the application locally on http://127.0.0.1:5000
    # debug=True allows automatic reloads whenever you save code changes
    app.run(debug=True, port=5000)