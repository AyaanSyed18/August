# 🤖 AUGUST: The AI G-Suite Command Center

Inspired by Stark's Jarvis, **AUGUST** is a premium, voice-controlled AI assistant that integrates directly with your Google Workspace. From sending emails to generating complex spreadsheets and scheduling meetings, AUGUST handles your digital chores using just your voice.

## ✨ Key Features
- **🎙️ Speech-to-Speech Interaction**: Fully hands-free workflow with the "August" wake word.
- **📁 Google Workspace Mastery**: Unified control over Docs, Sheets, Slides, Gmail, Calendar, and Chat.
- **⚡ Professional CLI**: A high-fidelity terminal interface with live status logging and beautiful panels.
- **🔒 Secure Authentication**: Robust OAuth 2.0 flow with a unified "one-time" login for all services.
- **🚀 High Performance**: Non-blocking audio architecture and batch-processed Gmail requests for zero lag.
- **🧠 Multi-Turn Memory**: Robust conversation history management that understands context.

## 🛠️ Tech Stack
- **Languages**: Python 3.10+
- **AI Brain**: OpenRouter (GPT-3.5/GPT-4 models)
- **STT**: AssemblyAI (Streaming Speech-to-Text)
- **TTS**: Microsoft Edge-TTS (Natural Voice)
- **VAD**: WebRTCVAD (Real-time Speech Detection)
- **API**: Google Discovery APIs (Workspace Integration)

## 📥 Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ayaansyed18/august.git
   cd august
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuration

### 1. API Keys
Create a `.env` file in the root directory and add your keys:
```env
AAI_API_KEY=your_assemblyai_key
OPENROUTER_API_KEY=your_openrouter_key
```
- **AssemblyAI**: Get your key at [assemblyai.com](https://www.assemblyai.com/).
- **OpenRouter**: Get your key at [openrouter.ai](https://openrouter.ai/).

### 2. Google Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the Docs, Sheets, Slides, Gmail, Calendar, and Chat APIs.
3. Configure your OAuth Consent Screen and create **OAuth 2.0 Client IDs**.
4. Download the JSON file, rename it to `credentials.json`, and place it in the project root.

## 🚀 Usage

Run the assistant:
```bash
python3 main.py
```

### Voice Commands
Start your sentence with the wake word **"August"**:
- *"August, create a new document called 'Project Plan' and add a list of goals."*
- *"August, list my last 5 emails and trash the most recent one."*
- *"August, schedule a meeting tomorrow at 10 AM regarding the website launch."*

### Keyboard Shortcuts
- **`L`** : **Logout** / Reset Session (Deletes tokens to switch Google accounts).
- **`H`** : **Housekeeping** (Clears the local recordings and audio cache).

## 📝 Example Flow
**User**: *"August, check my calendar for tomorrow."*  
**August**: *"Sir, you have 3 events tomorrow, including a 'Sync Meeting' at 11:00 AM. Would you like me to prepare a briefing document for that?"*  
**User**: *"Yes, create a doc for it and email it to my manager."*
