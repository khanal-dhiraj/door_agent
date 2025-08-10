"""
Configuration file for Door Security Agent
Modify these settings to customize the system
"""

# Password configuration - THE ONLY PLACE PASSWORDS ARE STORED
PASSWORDS = {
    "easy": "RAINBOW",
    "medium": "THUNDER",
    "hard": "PHOENIX",
    "number": "42"
}

# Default difficulty level
DEFAULT_LEVEL = "easy"

# Server configuration
PORT = 5050

# OpenAI configuration
VOICE = "alloy"  # Options: alloy, echo, shimmer
MODEL = "gpt-4o-realtime-preview-2025-06-03"
TEMPERATURE = 0.7

# Audio configuration
AUDIO_FORMAT = "g711_ulaw"

# Voice Activity Detection (VAD) settings
VAD_THRESHOLD = 0.5
VAD_PREFIX_PADDING_MS = 300
VAD_SILENCE_DURATION_MS = 500

# File paths - all logs go to logs/ directory
LOG_DIR = "logs"
DOOR_STATUS_FILE = f"{LOG_DIR}/door_status.txt"
ACCESS_LOG_FILE = f"{LOG_DIR}/door_access_log.txt"
STATS_FILE = f"{LOG_DIR}/game_stats.json"