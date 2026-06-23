from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_file,
    session,
    redirect,
    url_for,
)
from flask_session import Session
import sqlite3
import os
import requests
from gtts import gTTS
import random
import hashlib
import nltk
from nltk.tokenize import word_tokenize
import speech_recognition as sr
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import logging
from jinja2.exceptions import TemplateNotFound
from backend.config.database import users_collection
from datetime import datetime, UTC


# Check and download NLTK resources


def ensure_nltk_resources():

    try:
        # Check for punkt_tab (used in NLTK 3.7+)
        punkt_tab_path = os.path.join(
            os.path.expanduser("~"), "nltk_data", "tokenizers", "punkt_tab"
        )
        punkt_path = os.path.join(
            os.path.expanduser("~"), "nltk_data", "tokenizers", "punkt"
        )

        # Check if either punkt_tab or punkt exists
        if not os.path.exists(punkt_tab_path) and not os.path.exists(punkt_path):
            print("Downloading NLTK punkt_tab package...")
            nltk.download("punkt_tab", quiet=True)
            print("Downloaded NLTK punkt_tab package")
        else:
            print("NLTK punkt or punkt_tab package is already installed")
    except Exception as e:
        logging.error(f"Failed to download NLTK resources: {str(e)}")
        print(
            f"Warning: Failed to download NLTK resources: {str(e)}. Tokenization may fail."
        )


# Run the NLTK resource check at startup
ensure_nltk_resources()

# Set up logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)
app.secret_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour session lifetime
Session(app)

# Ensure static/ directory exists
if not os.path.exists("static"):
    os.makedirs("static")
    logging.info("Created static/ directory")


# Function to check internet connectivity
def check_internet():
    try:
        requests.get("https://translate.google.com", timeout=5)
        return True
    except requests.ConnectionError as e:
        logging.error(f"Internet connectivity check failed: {str(e)}")
        return False


# Function to check if static/ directory is writable
def check_static_writable():
    test_file = os.path.join("static", "test_write.txt")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except Exception as e:
        logging.error(f"Static directory not writable: {str(e)}")
        return False


# Helper function to safely render templates
def safe_render_template(template_name, **kwargs):
    try:
        return render_template(template_name, **kwargs)
    except TemplateNotFound:
        logging.error(f"Template not found: {template_name}")
        return (
            f"Error: Template '{template_name}' not found. Please contact support.",
            500,
        )


# Database setup


def init_db():
    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER NOT NULL,
            weight REAL NOT NULL,
            height REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symptoms TEXT NOT NULL,
            result TEXT,
            language TEXT,
            duration TEXT,
            output_type TEXT,
            tablets TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id))""")
        conn.commit()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")
        raise
    finally:
        conn.close()


# Symptom-disease dataset (simulated)
symptom_data = {
    "fever,cough": "Common Cold",
    "fever,cough,sore throat": "Influenza",
    "headache,fatigue": "Tension Headache",
    "stomach pain,nausea,vomiting": "Gastroenteritis",
    "fever,rash,headache": "Measles",
    "chest pain,shortness of breath,cough": "Pneumonia",
    "fever,chills,sweating": "Malaria",
    "joint pain,fever,rash": "Dengue",
    "abdominal pain,diarrhea": "Food Poisoning",
}
X_train = list(symptom_data.keys())
y_train = list(symptom_data.values())
vectorizer = CountVectorizer()
X_train_vectorized = vectorizer.fit_transform(X_train)
classifier = MultinomialNB()
classifier.fit(X_train_vectorized, y_train)

# Medication and natural remedy suggestions
remedy_map = {
    "Common Cold": {
        "medicine": "Paracetamol 500mg (1 tablet every 6 hours as needed)",
        "natural": "Drink warm water with honey and lemon, rest, and inhale steam.",
        "medicine_cure": 85,
        "natural_cure": 70,
    },
    "Influenza": {
        "medicine": "Oseltamivir 75mg (1 capsule twice daily for 5 days, consult doctor)",
        "natural": "Rest, drink herbal tea (ginger), and keep warm.",
        "medicine_cure": 90,
        "natural_cure": 60,
    },
    "Tension Headache": {
        "medicine": "Ibuprofen 400mg (1 tablet every 8 hours as needed)",
        "natural": "Apply a warm compress to neck, practice deep breathing.",
        "medicine_cure": 80,
        "natural_cure": 65,
    },
    "Gastroenteritis": {
        "medicine": "Oral Rehydration Salts (1 packet in 1L water, sip throughout day)",
        "natural": "Sip clear fluids (water, rice water), eat bland foods (banana).",
        "medicine_cure": 95,
        "natural_cure": 80,
    },
    "Measles": {
        "medicine": "Vitamin A supplement (consult doctor for dosage)",
        "natural": "Rest, maintain hygiene, and avoid spreading.",
        "medicine_cure": 90,
        "natural_cure": 50,
    },
    "Pneumonia": {
        "medicine": "Amoxicillin 500mg (1 tablet every 8 hours for 7 days, consult doctor)",
        "natural": "Rest and chest physiotherapy (not a full cure without medicine).",
        "medicine_cure": 95,
        "natural_cure": 30,
    },
    "Malaria": {
        "medicine": "Artemether-Lumefantrine (consult doctor for dosage)",
        "natural": "Rest and hydration (not a cure without medicine).",
        "medicine_cure": 98,
        "natural_cure": 20,
    },
    "Dengue": {
        "medicine": "Paracetamol 500mg (1 tablet every 6 hours, avoid NSAIDs)",
        "natural": "Drink papaya leaf juice, rest, and hydrate.",
        "medicine_cure": 85,
        "natural_cure": 60,
    },
    "Food Poisoning": {
        "medicine": "Loperamide 2mg (1 tablet after loose stool, max 8mg/day)",
        "natural": "Drink water with lemon, eat probiotics (yogurt).",
        "medicine_cure": 90,
        "natural_cure": 75,
    },
}

# Hydration guidance
hydration_guidance = {
    "en": "To stay hydrated: Drink 8-10 glasses of water daily (2-3 liters), include electrolyte-rich drinks (coconut water, ORS), and avoid caffeine/alcohol. Precautions: Sip slowly if nauseous, monitor urine color (should be pale yellow).",
    "te": "హైడ్రేటెడ్ గా ఉండటానికి: రోజుకు 8-10 గ్లాసుల నీరు తాగండి (2-3 లీటర్లు), ఎలక్ట్రోలైట్ గల పానీయాలు (కొబ్బరి నీరు, ORS) తాగండి, కెఫిన్/ఆల్కహాల్ నివారించండి. జాగ్రత్తలు: వికారం ఉంటే నెమ్మదిగా తాగండి, మూత్రం రంగును పరిశీలించండి (పసుపు రంగులో ఉండాలి).",
    "hi": "हाइड्रेटेड रहने के लिए: रोजाना 8-10 गिलास पानी पिएं (2-3 लीटर), इलेक्ट्रोलाइट युक्त पेय (नारियल पानी, ORS) लें, और कैफीन/शराब से बचें। सावधानियां: मतली हो तो धीरे-धीरे पिएं, पेशाब का रंग देखें (हल्का पीला होना चाहिए)।",
    "ta": "நீரேற்றமாக இருக்க: தினமும் 8-10 கிளாஸ் தண்ணீர் குடிக்கவும் (2-3 லிட்டர்), எலக்ட்ரோலைட் நிறைந்த பானங்கள் (தேங்காய் நீர், ORS) குடிக்கவும், காஃபின்/மது தவிர்க்கவும். முன்னெச்சரிக்கைகள்: குமட்டல் இருந்தால் மெதுவாக குடிக்கவும், சிறுநீர் நிறத்தை பார்க்கவும் (வெளிர் மஞ்சள் இருக்க வேண்டும்).",
}

# Additional symptoms for questioning
additional_symptoms = [
    "sore throat",
    "rash",
    "chills",
    "sweating",
    "vomiting",
    "diarrhea",
    "joint pain",
]

# Language-specific templates
advice_templates = {
    "Common Cold": {
        "en": "Rest and stay hydrated.",
        "te": "విశ్రాంతి తీసుకోండి మరియు హైడ్రేటెడ్ గా ఉండండి.",
        "hi": "आराम करें और हाइड्रेटेड रहें।",
        "ta": "ஓய்வு எடுத்து நீரேற்றமாக இருங்கள்.",
    },
    "Influenza": {
        "en": "Rest and stay hydrated, consult a doctor if symptoms worsen.",
        "te": "విశ్రాంతి తీసుకోండి మరియు హైడ్రేటెడ్ గా ఉండండి, లక్షణాలు తీవ్రమైతే వైద్యుడిని సంప్రదించండి.",
        "hi": "आराम करें और हाइड्रेटेड रहें, लक्षण बिगड़ने पर डॉक्टर से परामर्श करें।",
        "ta": "ஓய்வு எடுத்து நீரேற்றமாக இருங்கள், அறிகுறிகள் மோசமடைந்தால் மருத்துவரை அணுகவும்.",
    },
}


def ask_yes_no_question(symptom, language):
    questions = {
        "en": f"Do you have {symptom}? (Yes/No)",
        "te": f"మీకు {symptom} ఉందా? (అవును/కాదు)",
        "hi": f"क्या आपको {symptom} है? (हाँ/नहीं)",
        "ta": f"உங்களுக்கு {symptom} உள்ளதா? (ஆம்/இல்லை)",
    }
    return questions.get(language, questions["en"])


def ask_medicine_question(language):
    questions = {
        "en": "Do you want to take medicine? (Yes/No)",
        "te": "మీరు ఔషధం తీసుకోవాలనుకుంటున్నారా? (అవును/కాదు)",
        "hi": "क्या आप दवा लेना चाहते हैं? (हाँ/नहीं)",
        "ta": "நீங்கள் மருந்து எடுக்க விரும்புகிறீர்களா? (ஆம்/இல்லை)",
    }
    return questions.get(language, questions["en"])


def analyze_symptoms(
    symptoms, duration, language, user_data, answered_symptoms=None, wants_medicine=None
):
    if not symptoms or not duration or not language:
        logging.error("Missing required fields in analyze_symptoms")
        return {"error": "All fields (symptoms, duration, language) are required."}

    symptoms = symptoms.lower().strip()
    duration_note = f" (Duration: {duration})" if duration else ""
    try:
        tokens = word_tokenize(symptoms)
    except LookupError as e:
        logging.error(f"Tokenization failed: {str(e)}")
        return {
            "error": "Tokenization failed. Please ensure NLTK resources are available."
        }

    symptom_key = ",".join(
        sorted([t for t in tokens if t not in ["and", "with", "a", "the"]])
    )
    X_test = vectorizer.transform([symptom_key])
    predicted_disease = classifier.predict(X_test)[0]
    probability = max(classifier.predict_proba(X_test)[0])

    # Track answered symptoms
    answered_symptoms = answered_symptoms or []

    # If confidence is low and there are still symptoms to ask about
    if probability < 0.75:
        for extra_symptom in additional_symptoms:
            if (
                extra_symptom not in symptom_key
                and extra_symptom not in answered_symptoms
            ):
                return {
                    "text": "More information needed.",
                    "next_question": ask_yes_no_question(extra_symptom, language),
                    "next_symptom": extra_symptom,
                }
        # If no more questions to ask, proceed with the current symptoms
        symptom_key = ",".join(
            sorted([t for t in tokens if t not in ["and", "with", "a", "the"]])
        )

    if wants_medicine is None:
        return {
            "text": "Diagnosis ready.",
            "medicine_question": ask_medicine_question(language),
        }

    # Adjust based on user data (BMI)
    bmi = user_data["weight"] / ((user_data["height"] / 100) ** 2)
    advice = advice_templates.get(predicted_disease, {"en": "Consult a doctor."}).get(
        language, "Consult a doctor."
    )
    if "stay hydrated" in advice.lower():
        advice += " " + hydration_guidance.get(language, hydration_guidance["en"])

    remedy = remedy_map.get(predicted_disease, {})
    if wants_medicine.lower() == "yes":
        tablets = remedy.get("medicine", "No specific medication, consult a doctor.")
        if bmi > 30 and "Paracetamol" in tablets:
            tablets += " (Adjust dose if obese, consult doctor)"
        cure_percentage = remedy.get("medicine_cure", 80)
    else:
        tablets = remedy.get(
            "natural", "Rest and consult a doctor if symptoms persist."
        )
        cure_percentage = remedy.get("natural_cure", 50)

    response_text = {
        "en": f"Akshara suggests: {predicted_disease} (Confidence: {probability:.2%}). {advice} {'Tablets' if wants_medicine.lower() == 'yes' else 'Natural Remedy'}: {tablets} Cure Chance: {cure_percentage}%{duration_note}",
        "te": f"అక్షర సూచిస్తుంది: {predicted_disease} (నమ్మకం: {probability:.2%}). {advice} {'టాబ్లెట్‌లు' if wants_medicine.lower() == 'yes' else 'సహజ చికిత్స'}: {tablets} నయం అవకాశం: {cure_percentage}%{duration_note}",
        "hi": f"अक्षरा सुझाव देती है: {predicted_disease} (विश्वास: {probability:.2%}). {advice} {'गोलियाँ' if wants_medicine.lower() == 'yes' else 'प्राकृतिक उपचार'}: {tablets} ठीक होने की संभावना: {cure_percentage}%{duration_note}",
        "ta": f"அக்ஷரா பரிந்துரைக்கிறது: {predicted_disease} (நம்பிக்கை: {probability:.2%}). {advice} {'மாத்திரைகள்' if wants_medicine.lower() == 'yes' else 'இயற்கை சிகிச்சை'}: {tablets} குணமாகும் வாய்ப்பு: {cure_percentage}%{duration_note}",
    }
    return {
        "text": response_text.get(language, response_text["en"]),
        "disease": predicted_disease,
        "tablets": tablets,
    }


# Routes
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE id = ?", (session["user_id"],))
        user = c.fetchone()
        if not user:
            session.pop("user_id", None)
            logging.warning(
                f"Invalid user_id {session['user_id']} in session, redirecting to login"
            )
            return redirect(url_for("login"))
        logging.info(f"User {session['user_id']} accessed index page")
        return safe_render_template("index.html")
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}")
        return safe_render_template(
            "index.html", error="An error occurred, please try again"
        )
    finally:
        conn.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        try:
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE id = ?", (session["user_id"],))
            user = c.fetchone()
            if user:
                logging.info(
                    f"User {session['user_id']} already logged in, redirecting to index"
                )
                return redirect(url_for("index"))
            else:
                session.pop("user_id", None)
        except Exception as e:
            logging.error(f"Error checking session in login route: {str(e)}")
            session.pop("user_id", None)
        finally:
            conn.close()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember_me = request.form.get("remember-me") == "on"

        if not username or not password:
            logging.error("Login attempt with missing credentials")
            return safe_render_template(
                "login.html", error="Username and password are required"
            )

        password = hashlib.sha256(password.encode()).hexdigest()
        try:
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute(
                "SELECT id FROM users WHERE username = ? AND password = ?",
                (username, password),
            )
            user = c.fetchone()
            if user:
                session["user_id"] = user[0]
                if remember_me:
                    app.config["PERMANENT_SESSION_LIFETIME"] = 2592000  # 30 days
                    session.permanent = True
                else:
                    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour
                    session.permanent = False
                logging.info(
                    f"User {username} logged in successfully (Remember Me: {remember_me})"
                )
                return redirect(url_for("index"))
            else:
                logging.warning(f"Failed login attempt for username: {username}")
                return safe_render_template("login.html", error="Invalid credentials")
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            return safe_render_template(
                "login.html", error="An error occurred, please try again"
            )
        finally:
            conn.close()
    return safe_render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not all([username, email, password, confirm_password]):
            logging.error("Signup attempt with missing fields")
            return safe_render_template("signup.html", error="All fields are required")

        if password != confirm_password:
            logging.warning("Signup failed: Passwords do not match")
            return safe_render_template("signup.html", error="Passwords do not match")

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            existing_user = users_collection.find_one({"$or": [{"username": username}, {"email": email}]})
            if existing_user:
                logging.warning("Signup failed: Username or email already exists")
                return safe_render_template("signup.html", error="Username or email already exists")
            user_data = {"username": username,
                         "email": email,
                         "password_hash": password_hash,
                         "profile_completed": False,
                         "is_active": True,
                         "created_at": datetime.now(UTC),
                         "last_login": None}
            users_collection.insert_one(user_data)
            logging.info(f"User created successfully: {username}")
            return redirect(url_for("login"))
        except Exception as e:
            logging.error(f"Error occurred while creating user: {e}")
            return safe_render_template("signup.html", error="An error occurred, please try again")
    return safe_render_template("signup.html")


@app.route("/logout")
def logout():
    user_id = session.get("user_id", "unknown")
    session.pop("user_id", None)
    logging.info(f"User {user_id} logged out")
    return redirect(url_for("login"))


@app.route("/contact")
def contact():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return safe_render_template("contact.html")


@app.route("/support")
def support():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return safe_render_template("support.html")


@app.route("/voice_input", methods=["POST"])
def voice_input():
    if "user_id" not in session:
        return jsonify({"error": "Please log in"}), 401
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening... Speak your symptoms.")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            symptoms = recognizer.recognize_google(audio)
            logging.info(f"Voice input recognized: {symptoms}")
            return jsonify({"symptoms": symptoms})
        except sr.UnknownValueError:
            logging.error("Voice input error: Could not understand audio")
            return (
                jsonify({"error": "Could not understand audio, please try again"}),
                400,
            )
        except sr.RequestError:
            logging.error("Voice input error: Voice recognition service unavailable")
            return (
                jsonify(
                    {
                        "error": "Voice recognition service unavailable, please try again later"
                    }
                ),
                503,
            )
        except sr.WaitTimeoutError:
            logging.error("Voice input error: No speech detected within timeout")
            return jsonify({"error": "No speech detected, please speak clearly"}), 400
        except Exception as e:
            logging.error(f"Voice input error: {str(e)}")
            return jsonify({"error": "An error occurred, please try again"}), 500


@app.route("/check_symptoms", methods=["POST"])
def check_symptoms():
    if "user_id" not in session:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json()
    if not data:
        logging.error("Check symptoms attempt with no JSON data")
        return jsonify({"error": "Invalid request, please provide data"}), 400

    symptoms = data.get("symptoms", "")
    language = data.get("language", "en")
    duration = data.get("duration", "")
    output_type = data.get("output_type", "text")
    answered_symptoms = data.get("answered_symptoms", [])
    additional_answers = data.get("additional_answers", {})
    wants_medicine = data.get("wants_medicine")

    if not symptoms or not duration or not language:
        logging.error("Check symptoms attempt with missing fields")
        return jsonify({"error": "Symptoms, duration, and language are required"}), 400

    # Update symptoms with additional answers
    if additional_answers:
        for symptom, answer in additional_answers.items():
            if answer.lower() == "yes" and symptom not in symptoms:
                symptoms += "," + symptom

    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute(
            "SELECT age, weight, height FROM users WHERE id = ?", (session["user_id"],)
        )
        user_data = c.fetchone()
        if not user_data:
            session.pop("user_id", None)
            logging.warning(
                f"User {session['user_id']} not found, redirecting to login"
            )
            return jsonify({"error": "User not found, please log in again"}), 401

        user_info = {
            "age": user_data[0],
            "weight": user_data[1],
            "height": user_data[2],
        }

        result = analyze_symptoms(
            symptoms, duration, language, user_info, answered_symptoms, wants_medicine
        )

        if "error" in result:
            return jsonify({"error": result["error"]}), 400
        if "next_question" in result:
            return jsonify(
                {
                    "text_result": result["text"],
                    "next_question": result["next_question"],
                    "next_symptom": result["next_symptom"],
                }
            )
        if "medicine_question" in result:
            return jsonify(
                {
                    "text_result": result["text"],
                    "medicine_question": result["medicine_question"],
                }
            )

        c.execute(
            "INSERT INTO history (user_id, symptoms, result, language, duration, output_type, tablets) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session["user_id"],
                symptoms,
                result["text"],
                language,
                duration,
                output_type,
                result["tablets"],
            ),
        )
        conn.commit()
        logging.info(f"History entry added for user {session['user_id']}")

        if output_type == "audio":
            # Check prerequisites for audio generation
            if not check_internet():
                error_msg = "Audio generation failed: No internet connection. Please connect to the internet and try again."
                logging.error(error_msg)
                return jsonify({"text_result": result["text"], "error": error_msg})

            if not check_static_writable():
                error_msg = "Audio generation failed: Cannot write to static/ directory. Please ensure the directory has write permissions."
                logging.error(error_msg)
                return jsonify({"text_result": result["text"], "error": error_msg})

            try:
                tts = gTTS(
                    text=result["text"],
                    lang=language if language in ["en", "hi", "ta"] else "en",
                    slow=False,
                )
                audio_file = f"static/output_{random.randint(1, 1000)}.mp3"
                tts.save(audio_file)
                logging.info(f"Audio file generated: {audio_file}")
                return jsonify(
                    {"text_result": result["text"], "audio_url": f"/{audio_file}"}
                )
            except Exception as e:
                error_msg = (
                    f"Audio generation failed: {str(e)}. Displaying text instead."
                )
                logging.error(
                    f"Error generating audio: {str(e)}. Text: {result['text']}, Language: {language}"
                )
                return jsonify({"text_result": result["text"], "error": error_msg})
        return jsonify({"text_result": result["text"]})
    except Exception as e:
        logging.error(f"Error in check_symptoms: {str(e)}")
        return jsonify({"error": "An error occurred, please try again"}), 500
    finally:
        conn.close()


@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute(
            "SELECT symptoms, result, language, duration, output_type, tablets, timestamp FROM history WHERE user_id = ? ORDER BY timestamp DESC",
            (session["user_id"],),
        )
        entries = c.fetchall()
        logging.info(f"History fetched for user {session['user_id']}")
        return safe_render_template("history.html", entries=entries)
    except Exception as e:
        logging.error(f"Error in history route: {str(e)}")
        return "Error: Unable to fetch history. Please try again later.", 500
    finally:
        conn.close()


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_file(os.path.join("static", filename))


if __name__ == "__main__":
    print("Starting Flask app...")
    init_db()
    print("Database initialized")

    port = int(os.environ.get("PORT", 5000))

    print(f"Running Flask server on port {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True,
        use_reloader=False
    )
