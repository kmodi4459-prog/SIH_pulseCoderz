from transformers import pipeline
sentiment_analyzer=pipeline("sentiment-analysis")
emotion_analyzer = pipeline("text-classification", 
                              model="j-hartmann/emotion-english-distilroberta-base", 
                              top_k=None)


def generate_explanation(negative_confidence, fear_score, sadness_score):
    explanation = []
    
    if negative_confidence > 0.7:
        explanation.append(f"Strong negative sentiment detected ({round(negative_confidence*100)}% confidence)")
    
    if fear_score > 0.5:
        explanation.append(f"High fear detected ({round(fear_score*100)}%)")
    
    if sadness_score > 0.5:
        explanation.append(f"High sadness detected ({round(sadness_score*100)}%)")
    
    if not explanation:
        explanation.append("No significant distress indicators found")
    
    return explanation


def analyze_victim_response(text):
    sentiment_result = sentiment_analyzer(text)[0]
    emotion_result = emotion_analyzer(text)[0]
    emotion_scores = {e['label']: e['score'] for e in emotion_result}
    
    fear_score = emotion_scores.get('fear', 0)
    sadness_score = emotion_scores.get('sadness', 0)
    negative_confidence = sentiment_result['score'] if sentiment_result['label'] == 'NEGATIVE' else 0
    engagement_drop_factor = 0  # placeholder
    
    raw_score = (negative_confidence * 40) + (fear_score * 25) + (sadness_score * 20) + (engagement_drop_factor * 15)
    final_score = round(min(max(raw_score, 0), 100))
    
    if final_score >= 70:
        risk_level = "High"
    elif final_score >= 40:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    
    explanation = generate_explanation(negative_confidence, fear_score, sadness_score)
    
    return {
        "score": final_score,
        "risk_level": risk_level,
        "explanation": explanation
    }



result = analyze_victim_response("I feel very scared and alone since the incident")
print(result)


##day-2

from flask import Flask, request, jsonify
app = Flask(__name__)

# LOAD ONCE: This happens when the server starts
print("Loading AI Model... please wait.")
sentiment_pipeline = pipeline("sentiment-analysis")
print("Model loaded successfully!")

def calculate_distress_score(text):
    # Run the model
    result = sentiment_pipeline(text)[0]
    label = result['label']
    confidence = result['score'] # E.g., 0.95
    
    # Base scoring logic
    if label == 'NEGATIVE':
        # High confidence negative = high distress
        base_score = int(confidence * 100) 
    else:
        # High confidence positive = low distress (inverted)
        base_score = int((1.0 - confidence) * 100)
        
    # Optional: Keyword bump for high-risk words
    high_risk_words = ['scared', 'kill', 'hurt', 'threat', 'alone']
    if any(word in text.lower() for word in high_risk_words):
        base_score = min(100, base_score + 25) # Cap at 100
        
    return base_score

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.get_json()
    user_message = data.get('message', '')
    
    # 1. Calculate Score
    distress_score = calculate_distress_score(user_message)
    
    # 2. Determine if it's an Alert (Threshold logic for Member 5)
    is_alert = True if distress_score > 70 else False
    
    # 3. Simulate a basic bot reply (keep it static for the MVP)
    bot_reply = "I am listening. Please tell me more about what happened."
    
    # 4. Send JSON back to the frontend
    return jsonify({
        "reply": bot_reply,
        "distress_score": distress_score,
        "alert": is_alert
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)