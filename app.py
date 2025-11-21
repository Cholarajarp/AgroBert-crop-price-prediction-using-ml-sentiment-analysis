import os
import random
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

# --- Load Environment Variables ---
load_dotenv()

# --- GEMINI SETUP START ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found. Please set it in your .env file. AI chat will be disabled.")
    GEMINI_ENABLED = False
else:
    try:
        genai.configure(api_key=api_key)
        generation_config = {"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        gemini_model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        GEMINI_ENABLED = True
        print("Gemini API initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gemini API: {e}. AI chat functionality will be disabled.")
        GEMINI_ENABLED = False
# --- GEMINI SETUP END ---

try:
    from twilio.rest import Client
except ImportError:
    Client = None

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app)

# --- Configure JWT for Secure Sessions ---
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "default-fallback-secret-key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(app)

# --- Twilio Configuration ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = None
if Client and TWILIO_ACCOUNT_SID and "AC" in TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and "your_auth_token" not in TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("Twilio client configured successfully.")
    except Exception as e:
        print(f"Twilio configuration error: {e}")
else:
    print("Twilio credentials not fully configured. OTPs will be printed to the terminal.")

# --- DATABASE CONFIGURATION ---
DATABASE_FILE = 'users.db'

def get_db_conn():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initializes the database and creates the users table if it doesn't exist."""
    print("Initializing database...")
    conn = get_db_conn()
    if not conn:
        print("Failed to initialize database")
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT UNIQUE NOT NULL
        )
        ''')
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, email, mobile) VALUES (?, ?, ?, ?, ?)",
                ('farmer', generate_password_hash('farmer123'), 'farmer', 'farmer@example.com', '+919876543210')
            )
        except sqlite3.IntegrityError:
            print("ℹUser 'farmer' already exists.")
            
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, email, mobile) VALUES (?, ?, ?, ?, ?)",
                ('analyst', generate_password_hash('analyst123'), 'analyst', 'analyst@example.com', '+919876543211')
            )
        except sqlite3.IntegrityError:
            print("ℹUser 'analyst' already exists.")
            
        conn.commit()
        print("Database initialized.")
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

otp_store = {}

# --- Multilingual Chatbot & News Data ---
chat_responses = {
    "en": {"price": "The predicted price is showing an upward trend due to market demand.", "weather": "The current weather forecast is favorable for this crop.", "recommend": "Based on your conditions, Wheat is a good option.", "greeting": "Hello! How can I assist you with AgroBert today?", "default": "I can help with price predictions, weather impact, and crop recommendations.", "price_detail": "The current simulated price for {commodity} in {market} is around ₹{price}/quintal. The trend is positive."},
    "hi": {"price": "बाजार की मांग के कारण अनुमानित कीमत में तेजी का रुख दिख रहा है।", "weather": "वर्तमान मौसम का पूर्वानुमान इस फसल के लिए अनुकूल है।", "recommend": "आपकी परिस्थितियों के आधार पर, गेहूं एक अच्छा विकल्प है।", "greeting": "नमस्ते! मैं आज एग्रोबर्ट में आपकी कैसे सहायता कर सकता हूँ?", "default": "मैं मूल्य भविष्यवाणी, मौसम के प्रभाव और फसल की सिफारिशों में मदद कर सकता हूँ।", "price_detail": "{market} में {commodity} का वर्तमान सिम्युलेटेड मूल्य लगभग ₹{price}/क्विंटल है। प्रवृत्ति सकारात्मक है।"},
    "kn": {"price": "ಮಾರುಕಟ್ಟೆಯ ಬೇಡಿಕೆಯಿಂದಾಗಿ ಊಹಿಸಲಾದ ಬೆಲೆಯು ಏರುಮುಖವಾಗಿದೆ.", "weather": "ಪ್ರಸ್ತುತ ಹವಾಮಾನ ಮುನ್ಸೂಚನೆಯು ಈ ಬೆಳೆಗೆ ಅನುಕೂಲಕರವಾಗಿದೆ.", "recommend": "ನಿಮ್ಮ ಪರಿಸ್ಥಿತಿಗಳ ಆಧಾರದ ಮೇಲೆ, ಗೋಧಿ ಉತ್ತಮ ಆಯ್ಕೆಯಾಗಿದೆ.", "greeting": "ನಮಸ್ಕಾರ! ಇಂದು ನಾನು ನಿಮಗೆ ಆಗ್ರೋಬರ್ಟ್‌ನಲ್ಲಿ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?", "default": "ನಾನು ಬೆಲೆ ಮುನ್ಸೂಚನೆಗಳು, ಹವಾಮಾನದ ಪ್ರಭಾವ ಮತ್ತು ಬೆಳೆ ಶಿಫಾರಸುಗಳೊಂದಿಗೆ ಸಹಾಯ ಮಾಡಬಹುದು.", "price_detail": "{market} ನಲ್ಲಿ {commodity} ಗಾಗಿ ಪ್ರಸ್ತುತ ಸಿಮ್ಯುಲೇಟೆಡ್ ಬೆಲೆ ಸುಮಾರು ₹{price}/ಕ್ವಿಂಟಾಲ್ ಆಗಿದೆ. ಪ್ರವೃತ್ತಿ ಧನಾತ್ಮಕವಾಗಿದೆ."}
}
news_data = {
    "en": ["Government announces new MSP for Kharif crops.", "Monsoon forecast predicts above-average rainfall.", "Global wheat prices surge due to supply chain disruptions."],
    "hi": ["सरकार ने खरीफ फसलों के लिए नए एमएसपी की घोषणा की।", "मानसून के पूर्वानुमान में औसत से अधिक बारिश की भविष्यवाणी की गई है।", "आपूर्ति श्रृंखला में व्यवधान के कारण वैश्विक गेहूं की कीमतों में वृद्धि हुई है।"],
    "kn": ["ಸರ್ಕಾರವು ಖಾರಿಫ್ ಬೆಳೆಗಳಿಗೆ ಹೊಸ ಎಂಎಸ್‌ಪಿ ಘೋಷಿಸಿದೆ.", "ಮಾನ್ಸೂನ್ ಮುನ್ಸೂಚನೆಯು ಸರಾಸರಿಗಿಂತ ಹೆಚ್ಚಿನ ಮಳೆಯನ್ನು ಊಹಿಸುತ್ತದೆ.", "ಪೂರೈಕೆ ಸರಪಳಿಯಲ್ಲಿನ ಅಡೆತಡೆಗಳಿಂದಾಗಿ ಜಾಗತಿಕ ಗೋಧಿ ಬೆಲೆಗಳು ಏರಿಕೆಯಾಗಿವೆ."]
}
commodity_keywords = {
    'wheat': ['wheat', 'गेहूं', 'ಗೋಧಿ'],
    'rice': ['rice', 'चावल', 'ಅಕ್ಕಿ'],
    'cotton': ['cotton', 'कपास', 'ಹತ್ತಿ'],
    'onion': ['onion', 'प्याज', 'ಈರುಳ್ಳಿ'],
    'potato': ['potato', 'आलू', 'ಆಲೂಗಡ್ಡೆ'],
    'tomato': ['tomato', 'टमाटर', 'ಟೊಮೆಟೊ']
}
MARKET_KEYWORDS = [
    "delhi", "mumbai", "bengaluru", "kolkata", "chennai", "pune", "jaipur","davanagere",
    "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal", "patna","shivamogga",
    "ludhiana", "agra", "nashik", "vadodara", "meerut", "rajkot", "varanasi","hubali",
    "amritsar", "allahabad", "jodhpur", "kochi", "mysuru", "hyderabad", "bhubaneswar"
]

# --- Helper Functions ---
def get_price_prediction(commodity, market, days_ahead):
    """Simulates a price prediction model."""
    base_prices = {'wheat': 2200, 'rice': 3000, 'cotton': 6000, 'onion': 1700, 'potato': 1500, 'maize': 1800, 'tomato': 1200, 'banana': 1800}
    base_price = base_prices.get(commodity.lower(), 2500)
    
    avg_price = base_price + (days_ahead * (random.uniform(-5, 10)))
    avg_price *= 1.05 if market.lower() in ['mumbai', 'delhi'] else 1.01
    avg_price = round(avg_price)

    low_price = round(avg_price * (1 - random.uniform(0.05, 0.15))) 
    high_price = round(avg_price * (1 + random.uniform(0.05, 0.15)))
    
    return {
        "average_price": avg_price,
        "low_price": low_price,
        "high_price": high_price
    }

def get_sentiment_analysis(text):
    """Simulates a sentiment analysis model."""
    score = random.uniform(-1, 1)
    if score > 0.3: sentiment = "Positive"
    elif score < -0.3: sentiment = "Negative"
    else: sentiment = "Neutral"
    return {'sentiment': sentiment, 'score': score}

def get_historical_data(predicted_price, days_ahead):
    """Generates fake historical data for charts."""
    dates, prices = [], []
    today = datetime.now()
    base = predicted_price / (1 + (random.uniform(-0.02, 0.05)))
    for i in range(30, 0, -1):
        d = today - timedelta(days=i)
        dates.append(d.strftime('%Y-%m-%d'))
        price = base + (i**0.5 * random.uniform(-15, 20)) + random.uniform(-25, 25)
        prices.append(round(price))
    
    dates.append(today.strftime('%Y-%m-%d'))
    prices.append(prices[-1] if prices else base)
    
    future_date = today + timedelta(days=days_ahead)
    dates.append(future_date.strftime('%Y-%m-%d'))
    prices.append(predicted_price)
    
    return {'dates': dates, 'prices': prices}

def get_xai_insights():
    """Simulates Explainable AI (XAI) insights WITH IMPORTANCE."""
    factors = [
        {'factor': 'Recent rainfall', 'impact': random.choice(['Positive', 'Negative']), 'reason': 'Influences soil moisture.', 'importance': random.uniform(0.1, 0.5)},
        {'factor': 'Mandi arrivals', 'impact': 'Negative', 'reason': 'Higher supply typically lowers prices.', 'importance': random.uniform(0.3, 0.8)},
        {'factor': 'News sentiment', 'impact': 'Positive', 'reason': 'Positive news boosts market confidence.', 'importance': random.uniform(0.2, 0.6)},
        {'factor': 'Global market trends', 'impact': 'Negative', 'reason': 'International prices affect domestic rates.', 'importance': random.uniform(0.4, 0.9)},
        {'factor': 'Fuel prices', 'impact': 'Negative', 'reason': 'Increases transportation costs.', 'importance': random.uniform(0.1, 0.4)}
    ]
    random.shuffle(factors)
    top_factors = sorted(factors[:3], key=lambda x: x['importance'], reverse=True) 
    return top_factors

def get_weather_data(market, lat=None, lon=None):
    """Provides simulated weather data."""
    display_market = market
    if lat and lon:
        display_market = "Your Location"

    conditions = ['Sunny', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Humid', 'Rainy']
    temps = {'Delhi': (28, 42), 'Mumbai': (25, 34), 'Bengaluru': (20, 32), 'Kolkata': (26, 36)}
    temp_range = temps.get(market, (24, 38))
    temp = random.randint(temp_range[0], temp_range[1])
    condition = random.choice(conditions)
    impact = "Conditions are stable. No immediate significant impact on crops expected."
    if "Rain" in condition:
        impact = "Rain is favorable for sowing, potentially stabilizing prices."
    elif "Sunny" in condition and temp > 38:
        impact = "High temperatures may stress crops, potentially leading to a slight price increase."
    return {'market': display_market, 'temp': temp, 'condition': condition, 'impact': impact}

def get_crop_recommendation(soil, rainfall, ph, temp):
    """Simulates a crop recommendation engine based on simple rules."""
    try:
        rainfall, temp, ph = float(rainfall), float(temp), float(ph)
    except (TypeError, ValueError):
        return {'crop': 'Unknown', 'reason': 'Invalid input data.'}
    if soil.lower() in ['black', 'काली', 'ಕಪ್ಪು'] and rainfall > 1000:
        return {'crop': 'Cotton', 'reason': 'Black soil and high rainfall are ideal for cotton.'}
    if soil.lower() in ['alluvial', 'जलोढ़', 'ಮೆಕ್ಕಲು'] and rainfall > 1500:
        return {'crop': 'Rice', 'reason': 'Alluvial soil with abundant water is perfect for rice.'}
    if temp > 28 and rainfall < 800:
        return {'crop': 'Bajra', 'reason': 'This crop is resilient to high temperatures and lower rainfall.'}
    return {'crop': 'Wheat', 'reason': 'Conditions are generally suitable for wheat cultivation.'}

def get_multilingual_news(lang):
    """Returns simulated news snippets based on selected language."""
    return news_data.get(lang, news_data['en'])

# --- ROOT ENDPOINT ---
@app.route("/")
def index():
    """Serves the frontend HTML file."""
    return render_template('index.html')

# --- AUTHENTICATION ENDPOINTS ---
@app.route("/api/login", methods=["POST"])
def login():
    """Handles user login."""
    data = request.get_json()
    username = data.get("username", None)
    password = data.get("password", None)
    
    conn = get_db_conn()
    if not conn:
        return jsonify({"msg": "Database connection error"}), 500
    
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"msg": "Bad username or password"}), 401
            
        additional_claims = {"role": user["role"]}
        access_token = create_access_token(identity=username, additional_claims=additional_claims)
        return jsonify(access_token=access_token)
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"msg": "Login failed"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/register", methods=["POST"])
def register():
    """Handles new user registration."""
    data = request.get_json()
    username, password, email, mobile = data.get("username"), data.get("password"), data.get("email"), data.get("mobile")

    if not all([username, password, email, mobile]):
        return jsonify({"msg": "Missing required fields"}), 400
    
    if not (mobile.startswith('+') and len(mobile) > 10):
        return jsonify({"msg": "Please provide mobile number in international format (e.g., +919876543210)"}), 400

    hashed_password = generate_password_hash(password)
    
    conn = get_db_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, email, mobile) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_password, 'farmer', email, mobile)
        )
        conn.commit()
        return jsonify({"msg": "User created successfully"}), 201
    except sqlite3.IntegrityError as e:
        error_msg = str(e).lower()
        if "unique constraint failed: users.username" in error_msg:
            return jsonify({"msg": "Username already exists"}), 409
        if "unique constraint failed: users.email" in error_msg:
            return jsonify({"msg": "Email already exists"}), 409
        if "unique constraint failed: users.mobile" in error_msg:
            return jsonify({"msg": "Mobile number already exists"}), 409
        return jsonify({"msg": "A database error occurred."}), 500
    except Exception as e:
        print(f"❌ Unexpected error in register: {e}")
        return jsonify({"msg": "An unexpected error occurred"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    """Handles sending an OTP for password reset."""
    identifier = request.json.get("identifier")
    
    conn = get_db_conn()
    if not conn:
        return jsonify({"msg": "Database connection error"}), 500
    
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? OR mobile = ?",
            (identifier, identifier, identifier)
        ).fetchone()
                
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        found_username = user['username']
        found_mobile = user['mobile']

        otp = str(random.randint(100000, 999999))
        otp_store[found_username] = otp 
        
        if twilio_client:
            try:
                message = twilio_client.messages.create(
                    body=f"Your AgroBERT OTP is: {otp}",
                    from_=TWILIO_PHONE_NUMBER,
                    to=found_mobile
                )
                print(f"OTP SMS sent to {found_mobile} via Twilio. SID: {message.sid}")
                return jsonify({"msg": "OTP sent successfully to your mobile."}), 200
            except Exception as e:
                print(f"❌ TWILIO SMS FAILED: {e}")
                print(f"--- OTP for {found_username} (FALLBACK): {otp} ---")
                # --- THIS IS THE FIX: Send 200 so the frontend proceeds ---
                return jsonify({"msg": "Could not send SMS. For development, please check server console for OTP."}), 200
        else:
            print("\n" + "="*50)
            print("--- DEVELOPMENT MODE: TWILIO NOT CONFIGURED ---")
            print(f"--- OTP for user '{found_username}': {otp} ---")
            print("="*50 + "\n")
            return jsonify({"msg": "OTP generated. For development, please check server console."}), 200
    except Exception as e:
        print(f"Send OTP error: {e}")
        return jsonify({"msg": "Failed to send OTP"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    """Resets the user's password after validating the OTP."""
    data = request.get_json()
    identifier, otp, new_password = data.get("username"), data.get("otp"), data.get("new_password")

    conn = get_db_conn()
    if not conn:
        return jsonify({"msg": "Database connection error"}), 500
    
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ? OR mobile = ?",
            (identifier, identifier, identifier)
        ).fetchone()
        
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        user_to_reset = user['username']

        if user_to_reset not in otp_store or otp_store.get(user_to_reset) != otp:
            return jsonify({"msg": "Invalid or expired OTP"}), 400

        new_hashed_password = generate_password_hash(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hashed_password, user_to_reset)
        )
        conn.commit()
        
        if user_to_reset in otp_store:
            del otp_store[user_to_reset]
            
        return jsonify({"msg": "Password updated successfully"}), 200
    except Exception as e:
        print(f"❌ Reset password error: {e}")
        return jsonify({"msg": "Failed to reset password"}), 500
    finally:
        if conn:
            conn.close()

# --- PROTECTED API ENDPOINTS ---
@app.route('/api/predict', methods=['POST'])
@jwt_required()
def handle_predict():
    """Handles the main price prediction request."""
    data = request.json
    days = int(data.get('daysAhead', 7))
    market = data.get('market')
    commodity = data.get('commodity')
    
    price_prediction_report = get_price_prediction(commodity, market, days)
    
    response = {
        'prediction_report': price_prediction_report, 
        'prediction': {'predicted_modal_price_INR': price_prediction_report['average_price']}, 
        'chartData': get_historical_data(price_prediction_report['average_price'], days),
        'xai': get_xai_insights()
    }
    return jsonify(response)

@app.route('/api/analyze-sentiment', methods=['POST'])
@jwt_required()
def handle_sentiment():
    """Handles the news sentiment analysis request."""
    return jsonify(get_sentiment_analysis(request.json.get('text', '')))

@app.route('/api/weather', methods=['GET'])
@jwt_required()
def handle_weather():
    """Handles the weather data request."""
    market, lat, lon = request.args.get('market', 'Delhi'), request.args.get('lat'), request.args.get('lon')
    return jsonify(get_weather_data(market, lat, lon))

@app.route('/api/recommend-crop', methods=['POST'])
@jwt_required()
def handle_crop_recommendation():
    """Handles the crop recommendation request."""
    data = request.json
    return jsonify(get_crop_recommendation(data.get('soil'), data.get('rainfall'), data.get('ph'), data.get('temp')))

@app.route('/api/news', methods=['GET'])
@jwt_required()
def handle_news():
    """Handles the multilingual news request for the PDF report."""
    lang = request.args.get('lang', 'en')
    return jsonify(get_multilingual_news(lang))

@app.route('/api/chat', methods=['POST'])
@jwt_required()
def handle_chat():
    """Handles the chatbot query."""
    data = request.json
    user_query, lang = data.get("query", "").lower(), data.get("lang", "en")
    responses = chat_responses.get(lang, chat_responses['en'])
    response_text = responses['default']
    rule_matched = False

    if any(k in user_query for k in ["hello", "hi", "ನಮಸ್ಕಾರ", "नमस्ते"]):
        response_text = responses['greeting']
        rule_matched = True
    
    if not rule_matched:
        found_commodity = None
        found_market = "Delhi"
        
        for commodity_en, keywords in commodity_keywords.items():
            if any(keyword in user_query for keyword in keywords):
                found_commodity = commodity_en
                break
                
        for market in MARKET_KEYWORDS:
            if market in user_query:
                found_market = market.capitalize()
                break
                
        if found_commodity:
            # --- THIS IS THE FIX ---
            price_report = get_price_prediction(found_commodity, found_market, 7)
            price = price_report["average_price"] 
            # --- END OF FIX ---

            lang_commodity_index = -1
            if lang == 'hi': lang_commodity_index = 1
            if lang == 'kn': lang_commodity_index = 2
            
            display_commodity = found_commodity.capitalize()
            if lang_commodity_index != -1 and len(commodity_keywords[found_commodity]) > lang_commodity_index:
                display_commodity = commodity_keywords[found_commodity][lang_commodity_index].capitalize()

            response_text = responses['price_detail'].format(commodity=display_commodity, market=found_market, price=f"{price:,.2f}")
            rule_matched = True

        elif any(k in user_query for k in ["price", "ಬೆಲೆ", "दाम"]):
            response_text = responses['price']
            rule_matched = True
        elif any(k in user_query for k in ["weather", "ಹವಾಮಾನ", "मौसम"]):
            response_text = responses['weather']
            rule_matched = True
        elif any(k in user_query for k in ["recommend", "ಶಿಫಾರಸು", "सुझाव"]):
            response_text = responses['recommend']
            rule_matched = True
            
    # --- GEMINI API CALL (if no rules matched) ---
    if not rule_matched and GEMINI_ENABLED:
        try:
            system_prompt = f"You are AgriBERT, a helpful agricultural assistant. Answer questions related to farming, crop prices, weather, and market analysis in India. Please respond in this language: {lang}. Be concise and helpful."

            chat_session = gemini_model.start_chat(history=[
                {"role": "user", "parts": [system_prompt]},
                {"role": "model", "parts": [responses['greeting']]} 
            ])
            
            gemini_response = chat_session.send_message(user_query)
            response_text = gemini_response.text

        except Exception as e:
            print(f"Gemini API Error: {e}")
            pass 

    return jsonify({"response": response_text})

@app.route('/api/sentiment-distribution', methods=['GET'])
@jwt_required()
def handle_sentiment_distribution():
    """Simulates sentiment data for the analytics pie chart."""
    data = {
        "positive": random.randint(20, 50),
        "negative": random.randint(5, 25),
        "neutral": random.randint(10, 30)
    }
    return jsonify(data)

@app.route('/api/market-comparison', methods=['GET'])
@jwt_required()
def handle_market_comparison():
    """Simulates price data for the analytics bar chart."""
    commodity = request.args.get('commodity', 'unknown')
    price_report = get_price_prediction(commodity, "Davanagere", 0) 
    base_price = price_report["average_price"]
    labels = ['Delhi', 'Mumbai', 'Bengaluru', 'Kolkata', 'Chennai','Davanagere']
    prices = [round(base_price * random.uniform(0.9, 1.1)) for _ in labels]
    data = {
        "labels": labels,
        "prices": prices
    }
    return jsonify(data)

# --- THIS IS THE NEW ENDPOINT FOR FIX 3 ---
@app.route('/api/model-performance', methods=['GET'])
@jwt_required()
def handle_model_performance():
    """
    Simulates model performance metrics to show improvement.
    """
    # Simulate a baseline model's error (higher is worse)
    baseline_rmse = random.randint(190, 230)
    
    # Simulate our advanced model's error (lower is better)
    agrobert_rmse = random.randint(60, 85)
    
    # Calculate improvement
    improvement = ((baseline_rmse - agrobert_rmse) / baseline_rmse) * 100
    
    # Get the key features from our existing helper
    key_features = get_xai_insights()
    
    data = {
        "baseline_model_name": "ARIMA (Baseline)",
        "baseline_rmse": baseline_rmse,
        "agrobert_model_name": "AgroBERT (AI + Sentiment)",
        "agrobert_rmse": agrobert_rmse,
        "improvement_percent": round(improvement, 1),
        "key_features": key_features
    }
    return jsonify(data)
# --- END OF NEW ENDPOINT ---

@app.route('/api/heatmap-data', methods=['GET'])
@jwt_required()
def handle_heatmap_data():
    """
    Simulates price data for the regional heatmap.
    """
    commodity = request.args.get('commodity', 'unknown')
    # --- THIS IS THE FIX ---
    price_report = get_price_prediction(commodity, "Delhi", 0)
    base_price = price_report["average_price"]
    # --- END OF FIX ---
    
    states = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
        "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
        "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
        "West Bengal", "Jammu and Kashmir", "Ladakh", "Delhi", "Puducherry",
        "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu"
    ]
    
    data = {state: round(base_price * random.uniform(0.85, 1.15)) for state in states}
    return jsonify(data)

# --- INITIALIZE DATABASE GLOBALLY (FIXED) ---
# This ensures the DB is created even when using Gunicorn
init_db()

# --- Main Execution ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)