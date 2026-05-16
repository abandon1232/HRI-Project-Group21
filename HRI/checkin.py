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
import threading
import random

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
    "How do you feel you have balanced your study time and your personal life over the past few days?",
    "How has your social life or connection with friends been lately? Have you had time for a fika or a chat?",
    "With the dark winter days, how have you been relaxing or taking care of yourself?",
    "How would you describe your energy and rest this week?",
    "Finally, how would you rate your sleep quality over the past few nights?",
]

TRANSITIONS = [
    "Now, moving on to the next part.",
    "Let's move to the next question.",
    "Moving forward."
]

CLOSING = "Thank you so much for taking the time to complete this check-in. Your participation is highly appreciated. Remember that taking care of your mental well-being is just as important as your studies. I hope you have a wonderful and balanced week ahead. Goodbye!"

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

    def listen(self, condition="neutral"):
        if self.client:
            listening = [True]
            def backchannel():
                while listening[0]:
                    time.sleep(random.uniform(1.5, 3.0))
                    if listening[0] and condition == "empathetic":
                        try:
                            self.client.request_gesture_start(name="Smile")
                        except Exception:
                            pass
            
            if condition == "empathetic":
                t = threading.Thread(target=backchannel)
                t.start()
                
            try:
                text = self.client.request_listen_start() or ""
            finally:
                listening[0] = False
                if condition == "empathetic":
                    t.join(timeout=1.0)
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

POSITIVE_FEEDBACK_TEXTS = [
    "I am genuinely glad to hear that you are doing well. It is always encouraging to see positive moments during the week.",
    "That is wonderful to hear. Having those good experiences really makes a difference in your overall well-being.",
    "It is great to know things are going well for you. Keep focusing on whatever is bringing you that positive energy."
]
NEGATIVE_FEEDBACK_TEXTS = [
    "I completely understand. That sounds like a very challenging situation to navigate, and it is entirely normal to feel that way.",
    "I am truly sorry to hear you are feeling that way. Please remember to be kind to yourself during these difficult moments.",
    "That sounds really tough. It is completely valid to feel overwhelmed, so make sure you are taking some time just to breathe."
]
NEUTRAL_FEEDBACK_TEXTS = [
    "I see. Thank you for sharing that with me. It is always helpful to take a moment and reflect on where you stand.",
    "Got it. Thanks for telling me. Sometimes things just are the way they are, and that is perfectly alright.",
    "Okay, thank you for letting me know. I appreciate your honesty in taking the time to check in today."
]

POSITIVE_GESTURES = ["Smile", "BigSmile"]
NEGATIVE_GESTURES = ["BrowFrown", "ExpressSad"]
NEUTRAL_GESTURES = ["Nod"]

class CheckinStateMachine:
    def __init__(self, condition):
        self.condition = condition
        self.furhat = FurhatWrapper(FURHAT_HOST)
        self.furhat.configure_for_condition(condition)
        self.state = "GREETING"
        self.question_index = 0
        self.sentiment_counts = {
            "positive": 0,
            "negative": 0,
            "neutral": 0
        }
        self.session_log = {
            "condition": condition,
            "timestamp": datetime.datetime.now().isoformat(),
            "interactions": []
        }

    def log_interaction(self, speaker, text, gesture=None):
        entry = {"speaker": speaker, "text": text}
        # Only record gestures in the empathetic condition; the neutral
        # condition does not perform expressive gestures, so the log should
        # not list them either (keeps the session JSON faithful to what the
        # robot actually does).
        if gesture and self.condition == "empathetic":
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
                        
                        # Filler transition phrase (Deterministic to ensure strict experimental control)
                        if self.question_index in [2, 4, 6]:
                            time.sleep(1.0)
                            # Pick transition sequentially based on question index
                            transition_idx = [2, 4, 6].index(self.question_index)
                            transition = TRANSITIONS[transition_idx % len(TRANSITIONS)]
                            self.furhat.say(transition, self.condition)
                            self.log_interaction("Furhat", transition)
                            
                        # Just ask the question
                        self.furhat.say(question, self.condition)
                        self.log_interaction("Furhat", question)
                        
                        user_text = self.furhat.listen(self.condition)
                        self.log_interaction("User", user_text)
                        
                        if check_safety(user_text):
                            self.state = "EMERGENCY"
                            continue
                            
                        # Elaboration probe
                        if len(user_text.split()) < 3 and not check_safety(user_text):
                            probe = "I see. Could you tell me a little bit more about that?"
                            self.furhat.say(probe, self.condition)
                            self.log_interaction("Furhat", probe)
                            
                            user_text_2 = self.furhat.listen(self.condition)
                            self.log_interaction("User", user_text_2)
                            
                            user_text = user_text + " " + user_text_2
                            
                            if check_safety(user_text):
                                self.state = "EMERGENCY"
                                continue
                        
                        if user_text:
                            sentiment = analyze_sentiment(user_text)
                            idx = self.sentiment_counts[sentiment]
                            
                            if sentiment == "positive":
                                feedback_speech = POSITIVE_FEEDBACK_TEXTS[idx % len(POSITIVE_FEEDBACK_TEXTS)]
                                feedback_gesture = POSITIVE_GESTURES[idx % len(POSITIVE_GESTURES)]
                            elif sentiment == "negative":
                                feedback_speech = NEGATIVE_FEEDBACK_TEXTS[idx % len(NEGATIVE_FEEDBACK_TEXTS)]
                                feedback_gesture = NEGATIVE_GESTURES[idx % len(NEGATIVE_GESTURES)]
                            else:
                                feedback_speech = NEUTRAL_FEEDBACK_TEXTS[idx % len(NEUTRAL_FEEDBACK_TEXTS)]
                                feedback_gesture = NEUTRAL_GESTURES[idx % len(NEUTRAL_GESTURES)]
                                
                            self.sentiment_counts[sentiment] += 1
                                
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
