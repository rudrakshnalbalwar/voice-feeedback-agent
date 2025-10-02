"""
Voice AI Feedback Agent for Automobile Servicing
Uses LiveKit framework with STT → LLM → TTS pipeline
Converses in Hinglish (Hindi + English mix)
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional
import pytz

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    voice,
)
from livekit.plugins import openai, deepgram, elevenlabs
from dotenv import load_dotenv

# Import ChatContext and ChatMessage from llm module
ChatContext = llm.ChatContext
ChatMessage = llm.ChatMessage
# Import VoiceAgent from voice module
VoiceAgent = voice.Agent

# Load environment variables
load_dotenv()

# =============================================================================
# CONVERSATION STATE MANAGEMENT
# =============================================================================

class ConversationState:
    """Manages the conversation flow and tracks answers"""
    
    # Questions to ask in order
    QUESTIONS = [
        {
            "id": "q1_overall_rating_1to5",
            "text": "Pehle mujhe batayiye, overall service ka rating kya denge aap? 1 se 5 mein.",
            "type": "rating_1_5"
        },
        {
            "id": "q2_washing_yesno",
            "text": "Theek hai. Vehicle washing satisfactory thi? Haan ya nahi?",
            "type": "yes_no"
        },
        {
            "id": "q3_advisor_behavior_1to5",
            "text": "Achha. Service advisor ka behavior kaisa tha? 1 se 5 rating dijiye.",
            "type": "rating_1_5"
        },
        {
            "id": "q4_promised_time_yesno",
            "text": "Samajh gayi. Kya vehicle promised time pe deliver hui thi? Haan ya nahi?",
            "type": "yes_no"
        },
        {
            "id": "q5_additional_comments_text",
            "text": "Bilkul theek. Koi additional comments ya suggestions hain aapke paas?",
            "type": "free_text"
        }
    ]
    
    def __init__(self):
        self.call_id = str(uuid.uuid4())
        self.current_question_index = -1  # Start before first question (greeting)
        self.answers = {
            "q1_overall_rating_1to5": 0,
            "q2_washing_yesno": "unknown",
            "q3_advisor_behavior_1to5": 0,
            "q4_promised_time_yesno": "unknown",
            "q5_additional_comments_text": ""
        }
        self.transcript = []
        self.conversation_complete = False
        
    def get_greeting(self) -> str:
        """Initial greeting message"""
        return "Namaste! Main TVS service center se Riya bol rahi hoon. Aaj main aapka feedback lena chahti hoon. Kya aap 2 minute de sakte hain?"
    
    def get_current_question(self) -> Optional[str]:
        """Get the current question text"""
        if self.current_question_index < 0 or self.current_question_index >= len(self.QUESTIONS):
            return None
        return self.QUESTIONS[self.current_question_index]["text"]
    
    def move_to_next_question(self) -> bool:
        """Move to next question. Returns True if more questions exist."""
        self.current_question_index += 1
        if self.current_question_index >= len(self.QUESTIONS):
            self.conversation_complete = True
            return False
        return True
    
    def get_current_question_id(self) -> Optional[str]:
        """Get current question ID for storing answer"""
        if self.current_question_index < 0 or self.current_question_index >= len(self.QUESTIONS):
            return None
        return self.QUESTIONS[self.current_question_index]["id"]
    
    def get_current_question_type(self) -> Optional[str]:
        """Get current question type for parsing"""
        if self.current_question_index < 0 or self.current_question_index >= len(self.QUESTIONS):
            return None
        return self.QUESTIONS[self.current_question_index]["type"]
    
    def store_answer(self, answer):
        """Store the answer for current question"""
        question_id = self.get_current_question_id()
        if question_id:
            self.answers[question_id] = answer
    
    def add_to_transcript(self, speaker: str, text: str):
        """Add message to transcript"""
        self.transcript.append(f"{speaker}: {text}")


# =============================================================================
# ANSWER EXTRACTION UTILITIES
# =============================================================================

class AnswerExtractor:
    """Extracts structured answers from user responses"""
    
    @staticmethod
    def extract_rating(text: str, llm_context=None) -> int:
        """Extract rating (1-5) from user response"""
        # Enhanced pattern matching for Hinglish numbers (both Devanagari and romanized)
        number_mapping = {
            # English
            '5': 5, 'five': 5, 'fiv': 5,
            '4': 4, 'four': 4, 'for': 4,
            '3': 3, 'three': 3, 'tree': 3,
            '2': 2, 'two': 2, 'too': 2, 'tu': 2,
            '1': 1, 'one': 1, 'won': 1,
            # Hinglish with phonetic variations (romanized)
            'paanch': 5, 'panch': 5, 'paanj': 5, 'punch': 5,
            'chaar': 4, 'char': 4, 'caar': 4,
            'teen': 3, 'tin': 3, 'tean': 3, 'tina': 3,
            'do': 2, 'dho': 2,
            'ek': 1, 'aek': 1, 'eak': 1,
            # Devanagari
            'पांच': 5, 'पाँच': 5,
            'चार': 4,
            'तीन': 3,
            'दो': 2,
            'एक': 1
        }
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Check each word and its variations
        for word in words:
            # Direct match
            if word in number_mapping:
                return number_mapping[word]
            
            # Fuzzy matching for phonetic variations
            for num_word, value in number_mapping.items():
                # Check if the word contains the number word (handles typos/variations)
                if len(num_word) > 1 and num_word in word:
                    return value
                # Check similarity for very short words (edit distance = 1)
                if len(word) <= 4 and len(num_word) <= 4:
                    if sum(c1 != c2 for c1, c2 in zip(word, num_word)) <= 1:
                        return value
        
        return 0
    
    @staticmethod
    def extract_yes_no(text: str) -> str:
        """Extract yes/no from user response"""
        text_lower = text.lower()
        
        # Expanded Hinglish yes indicators (both Devanagari and romanized)
        yes_words = [
            'yes', 'yeah', 'yep', 'yup',
            'haan', 'ha', 'han', 'hun', 'haa', 'haanji', 'hanji',
            'bilkul', 'bilkool',
            'ji', 'jee', 'ji han', 'ji haan',
            'theek', 'thik', 'teek', 'tick',
            'sahi', 'sahe', 'saahi',
            'okay', 'ok', 'sure', 'achha', 'acha', 'accha',
            'हां', 'हाँ', 'जी', 'बिल्कुल', 'ठीक', 'सही', 'अच्छा'  # Devanagari
        ]
        # Expanded Hinglish no indicators (both Devanagari and romanized)
        no_words = [
            'no', 'nope', 'nah', 'na',
            'nahi', 'nahin', 'nai', 'nay', 'nehi', 'nahe',
            'bilkul nahi', 'bilkool nahi',
            'नहीं', 'ना', 'नाही', 'बिलकुल नहीं'  # Devanagari
        ]
        
        # Split text into words for better matching
        words = text_lower.split()
        
        # Check for Hindi/Hinglish variations with word boundary checking
        for word in words:
            # Check exact word matches
            if word in yes_words:
                return "yes"
            if word in no_words:
                return "no"
            
            # Check partial matches for compound words
            for yes_word in yes_words:
                if yes_word in word and len(yes_word) > 2:  # Avoid matching very short words
                    return "yes"
            for no_word in no_words:
                if no_word in word and len(no_word) > 2:
                    return "no"
        
        return "unknown"
    
    @staticmethod
    def extract_free_text(text: str) -> str:
        """Extract free text response"""
        # Clean up the text
        text = text.strip()
        
        # Check for "no comment" type responses
        no_comment_phrases = ['nahi', 'nothing', 'kuch nahi', 'no comment', 'bas itna hi']
        for phrase in no_comment_phrases:
            if phrase in text.lower() and len(text) < 50:
                return "No additional comments"
        
        return text if text else "No response"


# =============================================================================
# FILE MANAGEMENT
# =============================================================================

class OutputManager:
    """Manages saving transcript and JSON output"""
    
    @staticmethod
    def save_transcript(call_id: str, transcript: list):
        """Save conversation transcript to file"""
        os.makedirs("out", exist_ok=True)
        filepath = f"./out/{call_id}.txt"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"TVS Service Center Feedback Call\n")
            f.write(f"Call ID: {call_id}\n")
            f.write(f"Timestamp: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            for line in transcript:
                f.write(line + "\n")
        
        return filepath
    
    @staticmethod
    def save_json(call_id: str, answers: dict, transcript_path: str):
        """Save structured JSON output"""
        os.makedirs("out", exist_ok=True)
        filepath = f"./out/{call_id}.json"
        
        output = {
            "call_id": call_id,
            "timestamp_ist": datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S'),
            "language": "hinglish",
            "answers": answers,
            "transcript_path": transcript_path
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return filepath


# =============================================================================
# CUSTOM VOICE AGENT CLASS
# =============================================================================

class FeedbackVoiceAgent(VoiceAgent):
    """Custom Voice Agent that handles feedback conversation flow"""
    
    def __init__(self, state: ConversationState, ctx: JobContext, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self.ctx = ctx
        self.greeting_sent = False
    
    def on_enter(self):
        """Called when agent enters/starts"""
        print("🎤 Agent is ready and listening...")
        
        # Schedule greeting to be sent
        if not self.greeting_sent:
            asyncio.create_task(self._send_greeting())
    
    async def _send_greeting(self):
        """Send the initial greeting"""
        await asyncio.sleep(0.5)
        greeting = self.state.get_greeting()
        self.state.add_to_transcript("Riya", greeting)
        # Use the session property from parent Agent class
        await self.session.say(greeting, allow_interruptions=True)
        print(f"Riya: {greeting}")
        self.greeting_sent = True
    
    def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage):
        """
        Called when user completes their turn (finishes speaking).
        This is where we process user responses and drive the conversation.
        """
        # Schedule async processing
        asyncio.create_task(self._process_user_response(new_message))
    
    async def _process_user_response(self, new_message: ChatMessage):
        """Process user response asynchronously"""
        # Extract user's text from the message (handle both string and list)
        if isinstance(new_message.content, list):
            # Content is a list of strings - join them
            user_text = ' '.join(str(item) for item in new_message.content)
        elif isinstance(new_message.content, str):
            user_text = new_message.content
        else:
            user_text = str(new_message.content)
        print(f"👤 User said: {user_text}")
        
        # Add to transcript
        self.state.add_to_transcript("User", user_text)
        
        # If greeting phase (waiting for user to agree to give feedback)
        if self.state.current_question_index == -1:
            # Check if user agrees (both Devanagari and romanized Hinglish)
            agree_words = [
                'haan', 'han', 'haa', 'yes', 'yeah', 'yep', 'yup',
                'bilkul', 'bilkool', 'sure', 'ok', 'okay',
                'theek', 'thik', 'ha', 'ji', 'jee',
                'हां', 'हाँ', 'जी', 'बिल्कुल', 'ठीक', 'अच्छा'  # Devanagari
            ]
            if any(word in user_text.lower() or word in user_text for word in agree_words):
                # Move to first question
                self.state.move_to_next_question()
                question = self.state.get_current_question()
                self.state.add_to_transcript("Riya", question)
                await self.session.say(question, allow_interruptions=True)
                print(f"🤖 Riya asked: {question}")
            else:
                # User declined
                farewell = "Koi baat nahi, phir kabhi. Dhanyavaad!"
                self.state.add_to_transcript("Riya", farewell)
                await self.session.say(farewell, allow_interruptions=False)
                await self._save_and_exit()
            return
        
        # Process answer based on question type
        question_type = self.state.get_current_question_type()
        
        if question_type == "rating_1_5":
            # Extract rating (1-5)
            rating = AnswerExtractor.extract_rating(user_text)
            self.state.store_answer(rating)
            print(f"⭐ Extracted rating: {rating}")
            
        elif question_type == "yes_no":
            # Extract yes/no
            yes_no = AnswerExtractor.extract_yes_no(user_text)
            self.state.store_answer(yes_no)
            print(f"✓/✗ Extracted yes/no: {yes_no}")
            
        elif question_type == "free_text":
            # Store as-is
            comment = AnswerExtractor.extract_free_text(user_text)
            self.state.store_answer(comment)
            print(f"💬 Extracted comment: {comment}")
        
        # Move to next question or finish
        has_more = self.state.move_to_next_question()
        
        if has_more:
            # Ask next question
            question = self.state.get_current_question()
            self.state.add_to_transcript("Riya", question)
            await self.session.say(question, allow_interruptions=True)
            print(f"🤖 Riya asked: {question}")
        else:
            # All questions done - Thank and save
            farewell = "Bahut bahut dhanyavaad aapka feedback dene ke liye! Aap ka din shubh rahe!"
            self.state.add_to_transcript("Riya", farewell)
            await self.session.say(farewell, allow_interruptions=False)
            print(f"🤖 Riya: {farewell}")
            
            # Save transcript and JSON, then auto-disconnect
            await self._save_and_exit(auto_disconnect=True)
    
    def on_exit(self):
        """Called when agent exits"""
        print("👋 Agent session ended")
    
    async def _save_and_exit(self, auto_disconnect=False):
        """Save transcript and JSON, then optionally disconnect"""
        print("\n" + "="*60)
        print("💾 SAVING OUTPUTS...")
        print("="*60)
        
        # Save transcript
        transcript_path = OutputManager.save_transcript(self.state.call_id, self.state.transcript)
        print(f"✅ Transcript saved: {transcript_path}")
        
        # Save JSON
        json_path = OutputManager.save_json(self.state.call_id, self.state.answers, transcript_path)
        print(f"✅ JSON saved: {json_path}")
        
        print("\n📊 FINAL ANSWERS:")
        for key, value in self.state.answers.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*60)
        print("✅ Conversation complete!")
        print("="*60)
        
        # Auto-disconnect if requested (after survey completion)
        if auto_disconnect:
            print("👋 Auto-disconnecting in 1 second...")
            await asyncio.sleep(1)  # Short delay to ensure final message is sent
            await self.session.aclose()
            print("🔌 Session closed")


# =============================================================================
# ENTRY POINT FUNCTION
# =============================================================================

async def entrypoint(ctx: JobContext):
    """Main entry point for LiveKit agent"""
    
    # Connect to the room
    await ctx.connect()
    print(f"✅ Connected to room: {ctx.room.name}")
    
    # Initialize conversation state
    state = ConversationState()
    print(f"📞 Call ID: {state.call_id}")
    
    # Configure LLM (OpenAI GPT-4)
    llm_model = openai.LLM(
        model="gpt-4",
        temperature=0.7,
    )
    
    # Configure STT (Deepgram with Hindi language for better Hinglish recognition)
    # Using "hi" (Hindi) model which better transcribes Hindi words like "haan", "nahi", "paanch"
    # It will also handle English words reasonably well in mixed speech
    stt = deepgram.STT(
        model="nova-2-general",
        language="hi",  # Hindi language - better for Hinglish (Hindi+English mix)
        smart_format=True,  # Better formatting
        punctuate=True,  # Add punctuation
        filler_words=True,  # Capture filler words
    )
    
    # Configure TTS (ElevenLabs with female voice - Bella for better punctuation)
    tts = elevenlabs.TTS(
        voice_id="EXAVITQu4vr4xnSDxMaL",  # Bella - Soft female voice with clear pronunciation
        model="eleven_turbo_v2_5",
    )
    
    # Create agent session with STT, LLM, TTS configuration
    session = voice.AgentSession(
        stt=stt,
        llm=llm_model,
        tts=tts,
        allow_interruptions=True,
    )
    
    # Create custom voice agent with instructions
    assistant = FeedbackVoiceAgent(
        state=state,
        ctx=ctx,
        instructions="""You are Riya, a friendly customer service agent from TVS service center.
You speak naturally in Hinglish (Hindi + English mix).
Keep responses very short and conversational.
You are collecting feedback. Just acknowledge what the user says naturally.
Examples: "Theek hai", "Samajh gayi", "Bilkul", "Achha", "Thank you"
IMPORTANT: Never ask questions yourself. Only give acknowledgments.""",
    )
    
    # Start the agent session with the room
    await session.start(assistant, room=ctx.room)


# =============================================================================
# WORKER INITIALIZATION
# =============================================================================

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
