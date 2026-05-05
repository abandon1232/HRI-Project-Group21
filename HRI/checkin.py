"""
Weekly Mental State Check-in - shared core (Realtime API).

Two conditions share an identical verbal script. The independent variable
is isolated to non-verbal channels: voice, gestures, face configuration.

Entry points:
  - condition1_empathetic.py  (run the empathetic condition)
  - condition2_neutral.py     (run the neutral condition)
"""

import time
import json
import datetime
import os

try:
    from furhat_realtime_api import FurhatClient
    FURHAT_AVAILABLE = True
except ImportError:
    FURHAT_AVAILABLE = False
    print("[Warn] furhat_realtime_api not installed. Running in terminal-only mode.")

# ============================================================
# CONFIGURATION (shared by both conditions)
# ============================================================
FORCE_TERMINAL_MODE = False  # True = skip Furhat connection, run dialogue in terminal only
FURHAT_HOST = "localhost"

# Face: pass a face_id string. Use furhat.request_face_status() to list options
# on your installation. Common values look like "Adult/Isabel", "Adult/Patricia".
FACE_ID = "Adult/Isabel"

# Voice config per condition. We pass the full voice_id (globally unique).
# Both voices are female / en-US / adult, so character identity is held constant;
# the difference is in expressiveness:
#   - "Joanna-Neural" : Polly's neural voice (expressive, supports lip sync)
#   - "Salli"             : legacy standard voice (flat, monotone, synthetic)
EMPATHETIC_VOICE_ID = "Joanna-Neural (en-US) - Amazon Polly"
NEUTRAL_VOICE_ID = "Salli (en-US) - Amazon Polly"



# ============================================================
# UNIFIED VERBAL SCRIPT (identical for both conditions)
# ============================================================
OPENING = "Hello, and welcome to your weekly check-in for Uppsala University students. I will ask you a few short questions."

QUESTIONS = [
    "How would you describe your general mood this past week here in Uppsala?",
    "Have you experienced any stress from your university studies or recent deadlines?",
    "With the dark winter days, how have you been relaxing or taking care of yourself recently?",
    "How would you describe your energy and rest this week?",
    "How has your social life or connection with friends been lately? Have you had time for a fika or a chat?",
    "Finally, how would you rate your sleep quality over the past few nights?",
]

CLOSING = "Thank you. The check-in is now complete. Have a good week."

# ============================================================
# NON-VERBAL CUES (only applied in empathetic condition)
# ============================================================
# Pre/post question cues have been removed as per requested.
# Feedback gestures: Smile (positive), Nod (neutral), BrowFrown (negative).

# ============================================================
# FURHAT WRAPPER (Realtime API)
# ============================================================
class FurhatWrapper:
    def __init__(self, host):
        self.client = None
        if FORCE_TERMINAL_MODE or not FURHAT_AVAILABLE:
            print("[Terminal-only mode: Furhat SDK not used.]")
            return
        print(f"Connecting to Furhat (Realtime API) at {host}...")
        try:
            self.client = FurhatClient(host)
            self.client.connect()
            self.client.request_listen_config(languages=["en-US"])
            print("Connected.")
        except Exception as e:
            print(f"[Could not reach Furhat Realtime API at {host} - falling back to terminal mode.]")
            print(f"  Reason: {type(e).__name__}: {e}")
            self.client = None

    def configure_for_condition(self, condition):
        if not self.client:
            return
        try:
            print(f"[Setup] face_config face_id={FACE_ID}")
            # Empathetic condition has microexpressions, Neutral has static face
            use_micro = (condition == "empathetic")
            self.client.request_face_config(face_id=FACE_ID, visibility=True, microexpressions=use_micro)
        except Exception as e:
            print(f"[Warn] face_config failed: {type(e).__name__}: {e}")

        voice_id = EMPATHETIC_VOICE_ID if condition == "empathetic" else NEUTRAL_VOICE_ID
        try:
            print(f"[Setup] voice_config voice_id={voice_id}")
            self.client.request_voice_config(voice_id=voice_id)
        except Exception as e:
            print(f"[Warn] voice_config failed: {type(e).__name__}: {e}")
        
        try:
            status = self.client.request_voice_status()
            active = status.get("voice_id") if isinstance(status, dict) else None
            print(f"[Verify] active voice_id = {active}")
        except Exception as e:
            print(f"[Warn] voice_status failed: {type(e).__name__}: {e}")

    def say(self, text, condition):
        spoken = text
        print(f"[Furhat]: {text}")
        if self.client:
            try:
                self.client.request_speak_text(text=spoken, wait=True, abort=True)
            except Exception as e:
                print(f"[Warn] speak failed: {type(e).__name__}: {e}")
        else:
            time.sleep(0.5)

    def gesture(self, name, condition):
        if condition != "empathetic":
            return  # neutral condition: no expressive gestures
        print(f"[Gesture]: {name}")
        if self.client:
            self.client.request_gesture_start(name=name)

    def listen(self):
        if self.client:
            text = self.client.request_listen_start() or ""
        else:
            text = input("You: ")
        print(f"[User]: {text}")
        return text

    def shutdown(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass


# ============================================================
# STATE MACHINE & RUN LOGIC
# ============================================================
RISK_KEYWORDS = ["suicide", "kill myself", "end it all", "harm myself", "hopeless", "die", "give up on life"]

POSITIVE_KEYWORDS = ["good", "great", "fine", "well", "happy", "ok", "okay", "nice", "awesome", "perfect", "relaxing", "rested", "excellent"]
NEGATIVE_KEYWORDS = ["bad", "stressed", "tired", "anxious", "sad", "terrible", "exhausted", "asshole", "fucking", "horrible", "awful", "hard", "difficult"]

def check_safety(user_text):
    text_lower = user_text.lower()
    for word in RISK_KEYWORDS:
        if word in text_lower:
            return True
    return False

def analyze_sentiment(user_text):
    text_lower = user_text.lower()
    for word in NEGATIVE_KEYWORDS:
        if word in text_lower:
            return "negative"
    for word in POSITIVE_KEYWORDS:
        if word in text_lower:
            return "positive"
    return "neutral"

class CheckinStateMachine:
    def __init__(self, condition):
        self.condition = condition
        self.furhat = FurhatWrapper(FURHAT_HOST)
        self.furhat.configure_for_condition(condition)
        self.state = "GREETING"
        self.question_index = 0
        self.session_log = {
            "condition": condition,
            "timestamp": datetime.datetime.now().isoformat(),
            "interactions": []
        }

    def log_interaction(self, speaker, text, gesture=None):
        entry = {"speaker": speaker, "text": text}
        if gesture:
            entry["gesture"] = gesture
        self.session_log["interactions"].append(entry)

    def save_log(self):
        os.makedirs("logs", exist_ok=True)
        filename = f"logs/session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.condition}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.session_log, f, indent=4)
        print(f"[Info] Session log saved to {filename}")

    def run(self):
        print(f"--- Weekly Check-in (condition = {self.condition}) ---")
        try:
            while self.state != "END":
                if self.state == "GREETING":
                    if self.condition == "empathetic":
                        self.furhat.gesture("Smile", self.condition)
                        time.sleep(1.0)
                    self.furhat.say(OPENING, self.condition)
                    self.log_interaction("Furhat", OPENING, "Smile")
                    self.state = "ASK_QUESTIONS"
                
                elif self.state == "ASK_QUESTIONS":
                    if self.question_index < len(QUESTIONS):
                        question = QUESTIONS[self.question_index]
                        
                        # Increased nodding frequency: show engagement before asking
                        if self.condition == "empathetic":
                            self.furhat.gesture("Nod", self.condition)
                            time.sleep(0.5)
                            
                        # Just ask the question
                        self.furhat.say(question, self.condition)
                        self.log_interaction("Furhat", question)
                        
                        user_text = self.furhat.listen()
                        self.log_interaction("User", user_text)
                        
                        if check_safety(user_text):
                            self.state = "EMERGENCY"
                            continue
                        
                        if user_text:
                            sentiment = analyze_sentiment(user_text)
                            if sentiment == "positive":
                                feedback_speech = "I am glad to hear that."
                                feedback_gesture = "Smile"
                            elif sentiment == "negative":
                                feedback_speech = "I understand. That sounds challenging."
                                feedback_gesture = "BrowFrown"
                            else:
                                feedback_speech = "I see. Thank you for sharing."
                                feedback_gesture = "Nod"
                                
                            # Do the gesture FIRST (only if empathetic)
                            if self.condition == "empathetic":
                                self.furhat.gesture(feedback_gesture, self.condition)
                                time.sleep(1.0) # Wait for the gesture to form before speaking
                                
                            # Then give the identical verbal feedback
                            self.furhat.say(feedback_speech, self.condition)
                            self.log_interaction("Furhat", feedback_speech, feedback_gesture)
                            
                            time.sleep(0.6)
                        
                        self.question_index += 1
                    else:
                        self.state = "CLOSING"
                        
                elif self.state == "EMERGENCY":
                    emergency_msg = "I am deeply concerned to hear that. Please know that you are not alone. I am halting this session. Please contact the Uppsala University Student Health Service hotline immediately at 018-471 69 00."
                    self.furhat.say(emergency_msg, self.condition)
                    self.log_interaction("Furhat", emergency_msg)
                    print("[!!! EMERGENCY PROTOCOL TRIGGERED !!!]")
                    self.state = "END"
                    
                elif self.state == "CLOSING":
                    self.furhat.gesture("Smile", self.condition)
                    self.furhat.say(CLOSING, self.condition)
                    self.log_interaction("Furhat", CLOSING, "Smile")
                    self.state = "END"
        finally:
            self.save_log()
            self.furhat.shutdown()
            print("--- Check-in complete ---")

def run_checkin(condition):
    """Run the full weekly check-in dialogue. condition is 'empathetic' or 'neutral'."""
    if condition not in ("empathetic", "neutral"):
        raise ValueError(f"condition must be 'empathetic' or 'neutral', got {condition!r}")
    
    sm = CheckinStateMachine(condition)
    sm.run()
