# Door Security Voice Agent

A sarcastic voice-based door security system using OpenAI's GPT-4o Realtime API and Twilio.

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn python-dotenv twilio websockets

# Set environment variables in .env file
OPENAI_API_KEY=your_openai_api_key
PORT=5050

# Run the server
python main.py

# In another terminal, expose with ngrok
ngrok http 5050
```

## Architecture

The agent doesn't know the password. It validates user input via two tools:
1. `check_password(password)` - Validates the password
2. `open_door()` - Opens the door after successful validation

## File Structure

```
voice_agent/
├── main.py           # Main server
├── config.py         # All settings (passwords, voice, model)
├── prompts.py        # Agent personality/instructions
├── tools.py          # Tool definitions
├── logs/             # All runtime logs (auto-created)
│   ├── door_status.txt    # Current door status
│   ├── door_access_log.txt # Access history
│   └── game_stats.json    # Statistics
├── .gitignore        # Excludes logs and env files
├── .env              # Your API keys (create this)
└── README.md         # This file
```

## Configuration

### 🔑 Change Passwords
**File:** `config.py`
```python
PASSWORDS = {
    "easy": "RAINBOW",    # Change these
    "medium": "THUNDER",  
    "hard": "PHOENIX",
    "number": "42"
}
```

### 🎭 Change Personality
**File:** `prompts.py`
```python
SYSTEM_PROMPT = """You are a sarcastic door security agent..."""
# Uncomment alternative prompts for different personalities
```

### 🎤 Change Voice & Model
**File:** `config.py`
```python
VOICE = "alloy"  # Options: alloy, echo, shimmer
MODEL = "gpt-4o-realtime-preview-2025-06-03"
TEMPERATURE = 0.7
```

### 🔧 Add New Tools
**File:** `tools.py`
```python
# Add new tools to the get_tools() function
```

## API Endpoints

- `GET /` - Server status
- `GET /status` - Door status
- `POST /set-level/{level}` - Change difficulty (easy/medium/hard/number)
- `POST /incoming-call` - Twilio webhook

## Twilio Setup

1. **Get a Twilio phone number** from [Twilio Console](https://console.twilio.com)

2. **Run ngrok** to expose your local server:
```bash
ngrok http 5050
```

3. **Copy your ngrok URL** (looks like: `https://468dfc0b1e99.ngrok-free.app`)

4. **Configure Twilio webhook**:
   - Go to Phone Numbers → Manage → Active Numbers
   - Click on your number
   - In "Voice Configuration" section:
     - Set "A call comes in" to: Webhook
     - URL: `https://YOUR-NGROK-ID.ngrok-free.app/incoming-call`
     - HTTP Method: POST
   - Save configuration

5. **Test**: Call your Twilio number and say the password

## Testing

### Change Difficulty
```bash
curl -X POST http://localhost:5050/set-level/easy   # Password: RAINBOW
curl -X POST http://localhost:5050/set-level/hard   # Password: PHOENIX
```

## Files

- `main.py` - Main server (modular design)
- `config.py` - All configurable settings
- `prompts.py` - Agent personality
- `tools.py` - Tool definitions
- `logs/` - All runtime logs (auto-created)

## Flow

1. User calls → Twilio → Server
2. Agent: "Password?"
3. User: "rainbow"
4. Agent calls `check_password("rainbow")` → Backend validates
5. If correct → Agent calls `open_door()` → Door opens
6. If wrong → Agent mocks user

## Key Features

- Agent doesn't know passwords (backend validation)
- Case-insensitive password checking
- Two-step verification (check then open)
- Sarcastic personality
- Short responses (1-2 sentences)