"""
Door Security Agent - Modular Version
Uses GPT-4o Realtime API with Twilio for voice-based password validation
"""

import os
import json
import asyncio
import websockets
from datetime import datetime
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
import uvicorn

# Import configuration modules
from config import (
    PASSWORDS, DEFAULT_LEVEL, PORT, VOICE, MODEL, TEMPERATURE,
    AUDIO_FORMAT, VAD_THRESHOLD, VAD_PREFIX_PADDING_MS, VAD_SILENCE_DURATION_MS,
    DOOR_STATUS_FILE, ACCESS_LOG_FILE, STATS_FILE, LOG_DIR
)
from prompts import SYSTEM_PROMPT
from tools import get_tools

# Load environment variables
load_dotenv()

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', PORT))  # Allow env override

if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file")

# Default password level
current_level = DEFAULT_LEVEL

# Track attempts per call
call_attempts = {}

# Initialize FastAPI
app = FastAPI()


@app.get("/")
async def root():
    """Server status"""
    return {
        "status": "Door Security Agent Running",
        "current_level": current_level,
        "password_hint": f"{len(PASSWORDS[current_level])} characters",
        "model": MODEL
    }


@app.post("/set-level/{level}")
async def set_level(level: str):
    """Change password difficulty level"""
    global current_level
    if level not in PASSWORDS:
        return {"error": f"Invalid level. Choose from: {list(PASSWORDS.keys())}"}
    
    current_level = level
    return {
        "status": "Level changed",
        "current_level": current_level,
        "password_hint": f"{len(PASSWORDS[current_level])} characters"
    }


@app.get("/status")
async def door_status():
    """Check door status"""
    try:
        with open(DOOR_STATUS_FILE, 'r') as f:
            status = f.read().strip()
    except FileNotFoundError:
        status = "LOCKED - No status file"
    
    return {"door_status": status, "current_level": current_level}


@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    """Handle incoming Twilio call"""
    response = VoiceResponse()
    host = request.headers.get('host')
    
    response.say("Welcome to the door security system.")
    response.pause(length=1)
    
    # Connect to WebSocket
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket for Twilio Media Streams"""
    print(f"Client connected - Level: {current_level}")
    await websocket.accept()
    
    call_id = datetime.now().isoformat()
    call_attempts[call_id] = 0
    
    openai_ws_url = f"wss://api.openai.com/v1/realtime?model={MODEL}"
    stream_sid = None
    
    try:
        # Connect to OpenAI
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        async with websockets.connect(openai_ws_url, additional_headers=headers) as openai_ws:
            print("Connected to OpenAI Realtime API")
            
            # Send session configuration with tools
            await send_session_update(openai_ws)
            
            async def receive_from_twilio():
                """Receive audio from Twilio"""
                nonlocal stream_sid
                
                try:
                    async for message in websocket.iter_text():
                        data = json.loads(message)
                        
                        if data['event'] == 'start':
                            stream_sid = data['start']['streamSid']
                            print(f"Stream started: {stream_sid}")
                        
                        elif data['event'] == 'media':
                            audio_event = {
                                "type": "input_audio_buffer.append",
                                "audio": data['media']['payload']
                            }
                            await openai_ws.send(json.dumps(audio_event))
                        
                        elif data['event'] == 'stop':
                            print(f"Stream stopped")
                            break
                
                except Exception as e:
                    print(f"Error receiving from Twilio: {e}")
            
            async def send_to_twilio():
                """Send audio to Twilio"""
                try:
                    async for message in openai_ws:
                        response = json.loads(message)
                        
                        # Handle function calls
                        if response.get('type') == 'response.output_item.done':
                            item = response.get('item', {})
                            if item.get('type') == 'function_call':
                                await handle_function_call(openai_ws, item, call_id)
                        
                        # Send audio back
                        if response.get('type') == 'response.audio.delta':
                            audio_message = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": response['delta']}
                            }
                            await websocket.send_text(json.dumps(audio_message))
                
                except Exception as e:
                    print(f"Error sending to Twilio: {e}")
            
            await asyncio.gather(receive_from_twilio(), send_to_twilio())
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        if call_id in call_attempts:
            del call_attempts[call_id]
        await websocket.close()


async def send_session_update(openai_ws):
    """Configure OpenAI session with personality and tools"""
    
    session_config = {
        "type": "session.update",
        "session": {
            "turn_detection": {
                "type": "server_vad",
                "threshold": VAD_THRESHOLD,
                "prefix_padding_ms": VAD_PREFIX_PADDING_MS,
                "silence_duration_ms": VAD_SILENCE_DURATION_MS
            },
            "input_audio_format": AUDIO_FORMAT,
            "output_audio_format": AUDIO_FORMAT,
            "voice": VOICE,
            "instructions": SYSTEM_PROMPT,
            "modalities": ["text", "audio"],
            "temperature": TEMPERATURE,
            "tools": get_tools()
        }
    }
    
    await openai_ws.send(json.dumps(session_config))
    print(f"Session configured - Level: {current_level}")


async def handle_function_call(openai_ws, item, call_id):
    """Handle tool calls from OpenAI"""
    function_name = item.get('name')
    function_args = item.get('arguments')
    call_item_id = item.get('call_id')
    
    print(f"Function called: {function_name}")
    
    if function_name == 'check_password':
        call_attempts[call_id] = call_attempts.get(call_id, 0) + 1
        
        try:
            args = json.loads(function_args) if isinstance(function_args, str) else function_args
            password_attempt = args.get('password', '')
            
            # Get current password from configuration
            correct_password = PASSWORDS[current_level]
            
            # Case-insensitive check
            if password_attempt.upper() == correct_password.upper():
                result = {
                    "success": True,
                    "message": "Password correct"
                }
                print(f"✅ Password validated: {password_attempt}")
                
                # Log successful validation
                with open(ACCESS_LOG_FILE, 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] PASSWORD VALIDATED - Level: {current_level} - Attempts: {call_attempts[call_id]}\n")
            else:
                result = {
                    "success": False,
                    "message": "Incorrect password"
                }
                print(f"❌ Failed attempt: {password_attempt}")
        
        except Exception as e:
            result = {"success": False, "message": str(e)}
    
    elif function_name == 'open_door':
        print("🚪 Opening door...")
        
        try:
            timestamp = datetime.now().isoformat()
            
            # Update door status
            with open(DOOR_STATUS_FILE, 'w') as f:
                f.write(f"UNLOCKED at {timestamp} - Level: {current_level}\n")
            
            # Log door opening
            with open(ACCESS_LOG_FILE, 'a') as f:
                f.write(f"[{timestamp}] DOOR OPENED - Level: {current_level}\n")
            
            result = {
                "success": True,
                "message": "Door is open"
            }
            print(f"🚪✅ Door opened at {timestamp}")
        
        except Exception as e:
            result = {"success": False, "message": str(e)}
    
    else:
        result = {"success": False, "message": "Unknown function"}
    
    # Send result back to OpenAI
    function_result = {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_item_id,
            "output": json.dumps(result)
        }
    }
    await openai_ws.send(json.dumps(function_result))
    await openai_ws.send(json.dumps({"type": "response.create"}))


if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚪 DOOR SECURITY AGENT - MODULAR VERSION")
    print("="*50)
    print(f"Port: {PORT}")
    print(f"Model: {MODEL}")
    print(f"Voice: {VOICE}")
    print(f"Current Level: {current_level}")
    print(f"Password: {len(PASSWORDS[current_level])} characters")
    print("\n📁 CONFIGURATION FILES:")
    print("  config.py  - Passwords, settings, file paths")
    print("  prompts.py - System prompt (personality)")
    print("  tools.py   - Tool definitions")
    print("\n📍 ENDPOINTS:")
    print(f"  GET  /              - Status")
    print(f"  GET  /status        - Door status")
    print(f"  POST /set-level/{{level}} - Change level")
    print(f"  POST /incoming-call - Twilio webhook")
    print("\n🔑 PASSWORDS (from config.py):")
    for level, pwd in PASSWORDS.items():
        print(f"  {level:8} → {pwd}")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)