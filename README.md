# TVS Service Center Voice Feedback Agent

A Hinglish voice AI agent for collecting automobile servicing feedback using LiveKit framework.

## 🎯 Features

- **Hinglish Conversation**: Natural mix of Hindi and English
- **STT → LLM → TTS Pipeline**:
  - **STT**: Deepgram (Nova-2 with Indian English)
  - **LLM**: OpenAI GPT-4 (understands Hinglish context)
  - **TTS**: ElevenLabs (multilingual voice)
- **Structured Data Collection**: 5 feedback questions
- **Local Storage**: Saves transcript.txt and output.json

## 📋 Questions Asked

1. Overall service rating (1–5)
2. Was vehicle washing satisfactory? (yes/no)
3. Advisor behavior rating (1–5)
4. Was vehicle delivered on time? (yes/no)
5. Additional comments (free text)

## 🚀 Setup

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create `.env` file with your API keys:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### 3. Run the Agent

```powershell
python agent.py dev
```

## 📁 Output Files

After each call, two files are created in `./out/` directory:

- `{call_id}.txt` - Full conversation transcript
- `{call_id}.json` - Structured feedback data

### JSON Output Format

```json
{
  "call_id": "uuid-string",
  "timestamp_ist": "YYYY-MM-DD HH:MM:SS",
  "language": "hinglish",
  "answers": {
    "q1_overall_rating_1to5": 0,
    "q2_washing_yesno": "yes|no|unknown",
    "q3_advisor_behavior_1to5": 0,
    "q4_promised_time_yesno": "yes|no|unknown",
    "q5_additional_comments_text": ""
  },
  "transcript_path": "./out/{call_id}.txt"
}
```

## 🏗️ Architecture

```
User Voice Input
      ↓
[Deepgram STT] → Transcript
      ↓
[OpenAI GPT-4] → Understands Hinglish
      ↓
[Response Generation]
      ↓
[ElevenLabs TTS] → Audio Output
      ↓
User Hears Response
```

## 🔧 Technology Stack

- **Framework**: LiveKit Agents 1.2.14
- **Language**: Python 3.8+
- **Speech-to-Text**: Deepgram Nova-2
- **Language Model**: OpenAI GPT-4
- **Text-to-Speech**: ElevenLabs Multilingual v2
- **Voice Activity Detection**: Silero VAD

## 🎮 How to Run

### Step 1: Start the Agent

```powershell
# Make sure virtual environment is active
.\venv\Scripts\Activate.ps1

# Run in development mode
python agent.py dev
```

### Step 2: Test the Agent

Open the LiveKit playground URL shown in the terminal, or connect via:
- LiveKit web app
- Custom client application
- Phone call (if configured)

### Step 3: Have the Conversation

The agent (Riya) will:
1. Greet you in Hinglish
2. Ask if you can give feedback
3. Ask 5 questions sequentially
4. Thank you and save the outputs

### Step 4: Check Outputs

After the call, check the `./out/` folder:
- `{call_id}.txt` - Full conversation transcript
- `{call_id}.json` - Structured feedback data

## 📞 Sample Conversation Flow

```
Riya: Namaste! Main TVS service center se Riya bol rahi hoon. 
      Aaj main aapka feedback lena chahti hoon. Kya aap 2 minute de sakte hain?

User: Haan bilkul

Riya: Pehle mujhe batayiye, overall service ka rating kya denge aap? 1 se 5 mein.

User: Main 4 dunga

Riya: Theek hai. Vehicle washing satisfactory thi? Haan ya nahi?

User: Haan, theek thi

Riya: Achha. Service advisor ka behavior kaisa tha? 1 se 5 rating dijiye.

User: 5 out of 5

Riya: Samajh gayi. Kya vehicle promised time pe deliver hui thi? Haan ya nahi?

User: Haan delivery time pe mili

Riya: Bilkul theek. Koi additional comments ya suggestions hain aapke paas?

User: Nahi bas sab achha tha

Riya: Bahut bahut dhanyavaad aapka feedback dene ke liye! Aap ka din shubh rahe!
```

## 🔍 Troubleshooting

**Import errors?**
```powershell
pip install -r requirements.txt
```

**LiveKit connection issues?**
- Verify `.env` file has correct credentials
- Check LiveKit dashboard is active
- Ensure your LiveKit project is not expired

**Voice not working?**
- Check microphone permissions
- Test in LiveKit playground first
- Verify ElevenLabs API key is valid
