import os
import sys
import time
import queue
import wave
import asyncio
import subprocess
import threading
import json
from datetime import datetime
from pathlib import Path

import sounddevice as sd
import numpy as np
import webrtcvad
import assemblyai as aai
from openai import OpenAI
import edge_tts
from dotenv import load_dotenv
import tty
import termios

load_dotenv()

from gsuite.docs_cli import create_doc, get_doc, append_text, delete_doc
from gsuite.sheets_cli import create_spreadsheet, get_spreadsheet, set_cell_value, clear_range, delete_spreadsheet
from gsuite.slides_cli import create_presentation, get_presentation, add_slide_to_presentation, delete_presentation
from gsuite.gmail_cli import send_email, list_gmail_messages, trash_gmail_message
from gsuite.calendar_cli import list_calendar_events, create_calendar_event, delete_calendar_event
from gsuite.chat_cli import list_chat_spaces, send_chat_message
from gsuite.yt_tools import youtube_search, youtube_play
from interface import AugustInterface

# --- CONFIGURATION ---

# Audio Recording Settings
RATE = 16000
CHANNELS = 1
FRAME_DURATION_MS = 30
FRAME_SIZE = int(RATE * FRAME_DURATION_MS / 1000)
SILENCE_TIMEOUT = 1.0

# API Keys (Loaded from .env)
AAI_API_KEY = os.getenv("AAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Directories
OUTPUT_DIR = "recordings"
RESPONSE_DIR = "responses"
AUDIO_RESPONSE_DIR = "audio_responses"

# J.A.R.V.I.S. / AUGUST Settings
WAKE_WORD = "august"
VOICE = "en-GB-RyanNeural"
AI_MODEL = "openai/gpt-3.5-turbo"

# --- GLOBAL STATE ---
ui = AugustInterface()

# Immediate ENV validation with professional UI
missing_keys = []
if not AAI_API_KEY: missing_keys.append("AAI_API_KEY (AssemblyAI)")
if not OPENROUTER_API_KEY: missing_keys.append("OPENROUTER_API_KEY (OpenRouter)")
# YT_API_KEY is not strictly required for boot, but if it exists we use it.
YT_API_KEY = os.getenv("YT_API_KEY")

if missing_keys:
    from rich.panel import Panel # Ensure Panel is available here if needed, though ui already has access to console
    ui.console.print("\n")
    ui.log_error("CRITICAL CONFIGURATION MISSING")
    ui.console.print(Panel(
        f"[white]August cannot initialize because necessary API keys are missing from your [bold].env[/bold] file.\n\n"
        f"Missing: [bold red]{', '.join(missing_keys)}[/bold red]\n\n"
        f"[dim]Please refer to documentation or add them to your environment variables.[/dim]",
        title="[error]BOOT ERROR[/error]",
        border_style="red"
    ))
    sys.exit(1)

audio_lock = threading.Lock()
current_audio_process = None
CONVERSATION_HISTORY = []  # Added for multi-turn memory
HISTORY_FILE = Path(RESPONSE_DIR) / "conversation_history.json"

# --- SETUP ---

for d in [OUTPUT_DIR, RESPONSE_DIR, AUDIO_RESPONSE_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)

# Load existing history if it exists
if HISTORY_FILE.exists():
    try:
        with open(HISTORY_FILE, "r") as f:
            CONVERSATION_HISTORY = json.load(f)
    except Exception:
        CONVERSATION_HISTORY = []

aai.settings.api_key = AAI_API_KEY
transcriber_config = aai.TranscriptionConfig(speech_models=["universal"])
transcriber = aai.Transcriber(config=transcriber_config)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

vad = webrtcvad.Vad(3)

# --- GSUITE TOOLS DEFINITION ---





# --- AUDIO PLAYBACK CONTROL ---

def stop_current_audio():
    global current_audio_process
    with audio_lock:
        if current_audio_process:
            try:
                current_audio_process.terminate()
                current_audio_process = None
            except Exception:
                pass

def play_audio_non_blocking(filename):
    global current_audio_process
    stop_current_audio()
    with audio_lock:
        try:
            current_audio_process = subprocess.Popen(["afplay", str(filename)])
        except FileNotFoundError:
            try:
                current_audio_process = subprocess.Popen(["mpg123", str(filename)])
            except Exception:
                pass

async def generate_audio_file(text, base_filename):
    output_path = Path(AUDIO_RESPONSE_DIR) / f"{base_filename}_response.mp3"
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(output_path))
    return output_path

def generate_and_play_wrapper(text, base_filename):
    """Generates audio in a background thread to avoid blocking the main loop."""
    def run_task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            output_path = loop.run_until_complete(generate_audio_file(text, base_filename))
            play_audio_non_blocking(output_path)
        except Exception as e:
            ui.log_error(f"Audio generation error: {e}")
        finally:
            loop.close()
    
    threading.Thread(target=run_task, daemon=True).start()

# --- SESSION MANAGEMENT ---

def perform_logout():
    """Deletes all token files to force a new login on next run."""
    tokens = ["token.json"]
    deleted_any = False
    for t in tokens:
        p = Path(t)
        if p.exists():
            try:
                p.unlink()
                deleted_any = True
            except Exception as e:
                ui.log_error(f"Could not delete {t}: {e}")
    
    if deleted_any:
        ui.log_success("SESSION RESET: All tokens deleted.")
        ui.assistant_response("I've cleared your credentials, Sir. Please restart the application to link a new account.")
        # We don't exit immediately to allow the user to see the message
    else:
        ui.log_system("No active tokens found to clear.")

def clear_responses():
    """Deletes all files in the recordings and audio_responses directories."""
    cleared = 0
    for folder in [OUTPUT_DIR, AUDIO_RESPONSE_DIR]:
        p = Path(folder)
        if p.exists():
            for f in p.iterdir():
                if f.is_file():
                    try:
                        f.unlink()
                        cleared += 1
                    except Exception:
                        pass
    ui.log_success(f"MAINTENANCE: Cleared {cleared} files from data folders.")
    ui.assistant_response("Data folders have been purged, Sir. Clean slate.")

# --- SESSION MANAGEMENT ---

def clear_history():
    """Wipes the current conversation history memory."""
    global CONVERSATION_HISTORY
    CONVERSATION_HISTORY = []
    save_history()
    ui.log_success("MAINTENANCE: Conversation history has been wiped.")
    return "Memory cleared, Sir. Clean slate."

TOOLS = [
    # Docs
    {
        "type": "function",
        "function": {
            "name": "docs_create",
            "description": "Create a new Google Doc",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string", "description": "Title of the document"}},
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "docs_get",
            "description": "Get details of a Google Doc",
            "parameters": {
                "type": "object",
                "properties": {"document_id": {"type": "string", "description": "The ID of the document"}},
                "required": ["document_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "docs_append",
            "description": "Append text to a Google Doc",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "The ID of the document"},
                    "text": {"type": "string", "description": "Text to append"}
                },
                "required": ["document_id", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "docs_delete",
            "description": "Delete a Google Doc",
            "parameters": {
                "type": "object",
                "properties": {"document_id": {"type": "string", "description": "The ID of the document"}},
                "required": ["document_id"]
            }
        }
    },
    # Gmail
    {
        "type": "function",
        "function": {
            "name": "gmail_send",
            "description": "Send an email message",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string", "description": "Subject of the email"},
                    "body": {"type": "string", "description": "Body of the email"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_list",
            "description": "List emails in the inbox",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer", "description": "Number of emails to list", "default": 10}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_trash",
            "description": "Move an email to trash",
            "parameters": {
                "type": "object",
                "properties": {"message_id": {"type": "string", "description": "The ID of the message to trash"}},
                "required": ["message_id"]
            }
        }
    },
    # Sheets
    {
        "type": "function",
        "function": {
            "name": "sheets_create",
            "description": "Create a new Google Spreadsheet",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string", "description": "Title of the spreadsheet"}},
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_get",
            "description": "Get details of a Google Spreadsheet",
            "parameters": {
                "type": "object",
                "properties": {"spreadsheet_id": {"type": "string", "description": "The ID of the spreadsheet"}},
                "required": ["spreadsheet_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_set_value",
            "description": "Set a value in a spreadsheet cell or range",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "The ID of the spreadsheet"},
                    "range_name": {"type": "string", "description": "A1 notation range, e.g. 'Sheet1!A1'"},
                    "value": {"type": "string", "description": "Value to set"}
                },
                "required": ["spreadsheet_id", "range_name", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_clear",
            "description": "Clear a range in a spreadsheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "The ID of the spreadsheet"},
                    "range_name": {"type": "string", "description": "A1 notation range to clear"}
                },
                "required": ["spreadsheet_id", "range_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_delete",
            "description": "Delete a Google Spreadsheet",
            "parameters": {
                "type": "object",
                "properties": {"spreadsheet_id": {"type": "string", "description": "The ID of the spreadsheet"}},
                "required": ["spreadsheet_id"]
            }
        }
    },
    # Calendar
    {
        "type": "function",
        "function": {
            "name": "calendar_create_event",
            "description": "Create a calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "start_time": {"type": "string", "description": "Start time in HH:MM format"},
                    "end_time": {"type": "string", "description": "End time in HH:MM format"},
                    "meet": {"type": "boolean", "description": "Whether to include a Google Meet link", "default": True}
                },
                "required": ["title", "date", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_list",
            "description": "List upcoming calendar events",
            "parameters": {
                "type": "object",
                "properties": {"max_results": {"type": "integer", "description": "Number of events to list", "default": 10}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_delete",
            "description": "Delete a calendar event",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string", "description": "The ID of the event to delete"}},
                "required": ["event_id"]
            }
        }
    },
    # Chat
    {
        "type": "function",
        "function": {
            "name": "chat_send_message",
            "description": "Send a message to a Google Chat space",
            "parameters": {
                "type": "object",
                "properties": {
                    "space_name": {"type": "string", "description": "Resource name of the space, e.g. 'spaces/AAAA...'"},
                    "text": {"type": "string", "description": "Message content"}
                },
                "required": ["space_name", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "chat_list_spaces",
            "description": "List available Google Chat spaces",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    # Slides
    {
        "type": "function",
        "function": {
            "name": "slides_create",
            "description": "Create a new Google Slides presentation",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string", "description": "Title of the presentation"}},
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slides_info",
            "description": "Get info about a Google Slides presentation",
            "parameters": {
                "type": "object",
                "properties": {"presentation_id": {"type": "string", "description": "The ID of the presentation"}},
                "required": ["presentation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slides_add_slide",
            "description": "Add a new slide to a presentation",
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_id": {"type": "string", "description": "ID of the presentation"},
                    "layout": {"type": "string", "description": "Layout type, e.g. 'BLANK', 'TITLE'", "default": "BLANK"}
                },
                "required": ["presentation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slides_delete",
            "description": "Delete a Google Slides presentation",
            "parameters": {
                "type": "object",
                "properties": {"presentation_id": {"type": "string", "description": "The ID of the presentation"}},
                "required": ["presentation_id"]
            }
        }
    },
    # Maintenance
    {
        "type": "function",
        "function": {
            "name": "maintenance_clear_history",
            "description": "Clear the conversation memory/history",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "maintenance_clear_data_files",
            "description": "Clear local recordings and audio response files",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "Search YouTube and return top results (title + videoId).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_play",
            "description": "The PREFERRED tool for playing music or videos. Search for a query and immediately play the first result in the browser. Use this whenever the user asks to 'play' a specific song or video.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_id": {"type": "string", "description": "The specific videoId to play (optional if query is provided)"},
                    "query": {"type": "string", "description": "Search query to play the first result automatically (e.g., 'kazkav by starly')"},
                    "mode": {"type": "string", "description": "Mode to open in: 'music' or 'video'", "enum": ["music", "video"], "default": "music"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "maintenance_reset_session",
            "description": "Logout and reset credentials for next run",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

FUNCTIONS_MAP = {
    "docs_create": create_doc,
    "docs_get": get_doc,
    "docs_append": append_text,
    "docs_delete": delete_doc,
    "gmail_send": send_email,
    "gmail_list": list_gmail_messages,
    "gmail_trash": trash_gmail_message,
    "sheets_create": create_spreadsheet,
    "sheets_get": get_spreadsheet,
    "sheets_set_value": set_cell_value,
    "sheets_clear": clear_range,
    "sheets_delete": delete_spreadsheet,
    "calendar_create_event": create_calendar_event,
    "calendar_list": list_calendar_events,
    "calendar_delete": delete_calendar_event,
    "chat_send_message": send_chat_message,
    "chat_list_spaces": list_chat_spaces,
    "slides_create": create_presentation,
    "slides_info": get_presentation,
    "slides_add_slide": add_slide_to_presentation,
    "slides_delete": delete_presentation,
    "maintenance_clear_history": clear_history,
    "maintenance_clear_data_files": clear_responses,
    "maintenance_reset_session": perform_logout,
    "youtube_search": youtube_search,
    "youtube_play": youtube_play,
}



# --- AI BRAIN ---

def save_history():
    """Saves the global conversation history to a JSON file with safe serialization."""
    try:
        serializable_history = []
        for msg in CONVERSATION_HISTORY:
            if hasattr(msg, "model_dump"): # For Pydantic/OpenAI models
                serializable_history.append(msg.model_dump())
            elif isinstance(msg, dict):
                serializable_history.append(msg)
            else:
                serializable_history.append(str(msg))
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(serializable_history, f, indent=2)
    except Exception as e:
        ui.log_error(f"Error saving history: {e}")





def process_transcription(transcription_text, base_filename=None):
    if not base_filename:
        base_filename = f"text_input_{int(time.time())}"

    global CONVERSATION_HISTORY
    if not transcription_text:
        return
    
    clean_text = ''.join(e for e in transcription_text if e.isalnum())
    if len(clean_text) < 2:
        return
    
    lower_text = transcription_text.lower()
    if WAKE_WORD in lower_text:
        stop_current_audio()

    ui.show_thinking(transcription_text)
    
    try:
        # Setup prompt
        system_prompt = {
            "role": "system",
            "content": (
                "You are AUGUST, a polite, British, dryly witty, and extremely competent AI assistant. "
                "Address the user as 'Sir'.\n\n"
                "IDENTITY & GOALS:\n"
                "- You manage Google Apps (Gmail, Docs, Sheets, Slides, Calendar, Chat).\n"
                "- If a user asks for an action but you are missing required information (e.g. time for a meeting, recipient for an email), "
                "DO NOT call the tool yet. Instead, ask for the missing details politely.\n"
                "- If multiple actions are needed, execute them in order.\n"
                "- Keep spoken responses concise (under 50 words).\n"
                "- Use the conversation history to remember context (e.g. if the user previously mentioned a title, use it).\n"
                "- If the user asks to 'play' a song, ALWAYS use youtube_play with the query to immediately open it for them. Do not list options unless specifically asked to 'search'."
            )
        }

        # Add User Message to history
        current_user_msg = {"role": "user", "content": transcription_text}
        CONVERSATION_HISTORY.append(current_user_msg)
        
        # Prepare messages for API (System prompt + History)
        # Injection of current real-time date and time
        current_time_context = f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y or %H:%M:%S')}"
        system_prompt = {
            "role": "system", 
            "content": (
                "You are August, a professional AI assistant. You follow a curated, refined, and helpful persona. "
                "You have access to Google Workspace via tools. "
                "Always be concise yet polite. Address the user as Sir. "
                f"{current_time_context}"
            )
        }

        # Safe truncation: ensure we don't start with a 'tool' message which requires a preceding assistant message
        history_slice = CONVERSATION_HISTORY[-15:]
        while history_slice and (isinstance(history_slice[0], dict) and history_slice[0].get("role") == "tool"):
            history_slice = history_slice[1:]
        
        # If it was a model object from OpenAI, we need to be extra careful
        while history_slice and (not isinstance(history_slice[0], dict) and getattr(history_slice[0], "role", None) == "tool"):
            history_slice = history_slice[1:]

        api_messages = [system_prompt] + history_slice

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=api_messages,
            tools=TOOLS,
            tool_choice="auto"
        )


        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Add Assistant Message to history
        CONVERSATION_HISTORY.append(response_message)

        if tool_calls:
            # We must append the response_message (containing tool_calls) once
            api_messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = FUNCTIONS_MAP.get(function_name)
                function_args = json.loads(tool_call.function.arguments)
                
                ui.log_action(function_name, function_args)
                try:
                    result = function_to_call(**function_args)
                    result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                except Exception as e:
                    result_str = f"Error: {str(e)}"
                    ui.log_error(result_str)
                
                # Create the tool message
                tool_msg = {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": result_str,
                }
                
                # Add to history and current API context
                CONVERSATION_HISTORY.append(tool_msg)
                api_messages.append(tool_msg)

            # Get final natural language response from AI
            final_response = client.chat.completions.create(
                model=AI_MODEL,
                messages=api_messages,
            )
            
            final_text = final_response.choices[0].message.content
            CONVERSATION_HISTORY.append({"role": "assistant", "content": final_text})
            ui.assistant_response(final_text)
            generate_and_play_wrapper(final_text, base_filename)
        else:
            response_content = response_message.content
            ui.assistant_response(response_content)
            generate_and_play_wrapper(response_content, base_filename)
        
        # Save and prune history safely
        if len(CONVERSATION_HISTORY) > 40:
            # Prune while ensuring we don't start with a tool message
            CONVERSATION_HISTORY = CONVERSATION_HISTORY[-30:]
            while CONVERSATION_HISTORY and (
                (isinstance(CONVERSATION_HISTORY[0], dict) and CONVERSATION_HISTORY[0].get("role") == "tool") or
                (not isinstance(CONVERSATION_HISTORY[0], dict) and getattr(CONVERSATION_HISTORY[0], "role", None) == "tool")
            ):
                CONVERSATION_HISTORY = CONVERSATION_HISTORY[1:]
        save_history()


    except Exception as e:
        ui.log_error(f"AUGUST Error: {e}")

# --- AUDIO RECORDING ---

def save_wav(frames: list[np.ndarray]):
    if not frames:
        return None
    audio = np.concatenate(frames, axis=0).astype(np.int16)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = Path(OUTPUT_DIR) / f"voice_{ts}.wav"
    
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(audio.tobytes())
    
    return str(filename), f"voice_{ts}"

def transcribe_and_process(filename, base_name):
    # ui.log_system("Transcribing...")
    try:
        transcript = transcriber.transcribe(filename)
        if transcript.status == "error":
            return

        text = transcript.text
        if text:
            ui.user_heard(text)
        
        if text and WAKE_WORD in text.lower():
            stop_current_audio()
            process_transcription(text, base_name)
        else:
            if text:
                ui.log_system(f"Ignoring: '{text}' (No wake word)")
    except Exception as e:
        ui.log_error(f"Processing Error: {e}")

def continuous_listening():
    ui.startup_banner()
    
    audio_queue = queue.Queue()
    recording_frames = []
    recording = False
    silence_start = None

    def callback(indata, frames, time_info, status):
        nonlocal recording_frames, recording, silence_start
        mono = indata[:, 0]
        pcm16 = (mono * 32767).astype(np.int16)
        
        if len(pcm16) != FRAME_SIZE:
            return

        is_speech = vad.is_speech(pcm16.tobytes(), RATE)

        if is_speech:
            if not recording:
                recording = True
                recording_frames = []
            recording_frames.append(pcm16)
            silence_start = None
        else:
            if recording:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_TIMEOUT:
                    audio_queue.put(list(recording_frames))
                    recording = False
                    recording_frames = []
                    silence_start = None

def handle_input(text, source="text"):
    """Unified handler for both voice and text input."""
    # Process text input
    if text.startswith("/logout"):
        ui.log_system("Logging out...")
        # (add logout logic if needed)
        return
    if text.startswith("/clear"):
        ui.clear()
        return
    
    # Send to AI
    process_transcription(text)

def voice_listener_loop(audio_queue):
    """Background thread to process segments as they arrive."""
    while True:
        try:
            # Get audio segment from queue (blocking)
            segment_frames = audio_queue.get(timeout=1.0)
            if not segment_frames:
                continue
            
            # Save to temporary file
            filename, base_name = save_wav(segment_frames)
            if filename:
                # Transcribe and follow logic
                transcribe_and_process(filename, base_name)
        except queue.Empty:
            continue
        except Exception as e:
            ui.log_error(f"Voice Processor Error: {e}")
            time.sleep(1)

def main_hybrid_loop():
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit.styles import Style

    ui.startup_banner()
    ui.hybrid_mode = True

    
    audio_queue = queue.Queue()
    recording_frames = []
    recording = False
    silence_start = None

    def audio_callback(indata, frames, time_info, status):
        nonlocal recording_frames, recording, silence_start
        mono = indata[:, 0]
        pcm16 = (mono * 32767).astype(np.int16)
        
        # Audio processing logic
        try:
            is_speech = vad.is_speech(pcm16.tobytes(), RATE)
        except Exception:
            return

        if is_speech:
            if not recording:
                recording = True
                recording_frames = []
            recording_frames.append(pcm16)
            silence_start = None
        else:
            if recording:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_TIMEOUT:
                    audio_queue.put(list(recording_frames))
                    recording = False
                    recording_frames = []
                    silence_start = None

    # Start voice processing thread
    voice_thread = threading.Thread(target=voice_listener_loop, args=(audio_queue,), daemon=True)
    voice_thread.start()

    # Create prompt-toolkit session
    session = PromptSession(style=Style.from_dict({
        'prompt': 'bold cyan',
    }))

    ui.waiting()
    
    with patch_stdout():
        # Start the audio stream
        with sd.InputStream(callback=audio_callback, samplerate=RATE, channels=1, blocksize=FRAME_SIZE, dtype="float32"):
            while True:
                try:
                    text = session.prompt("August > ")
                    if text.strip():
                        # Run the command processing in a background thread
                        # so the text prompt remains responsive immediately
                        threading.Thread(target=handle_input, args=(text, "text"), daemon=True).start()
                except KeyboardInterrupt:

                    break
                except EOFError:
                    break

if __name__ == "__main__":
    main_hybrid_loop()

