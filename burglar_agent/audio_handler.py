"""
Audio handling for voice interaction with door agent
Handles microphone input, speaker output, and audio processing
"""

import pyaudio
import wave
import threading
import queue
import time
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import io
import os
from typing import Callable, Optional
import logging

class AudioHandler:
    def __init__(self, 
                 sample_rate: int = 44100,
                 chunk_size: int = 1024,
                 channels: int = 1,
                 format: int = pyaudio.paInt16):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = format
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Recording state
        self.is_recording = False
        self.recording_thread = None
        self.audio_queue = queue.Queue()
        self.frames = []
        
        # Playback state
        self.is_playing = False
        
        # Callbacks
        self.speech_detected_callback: Optional[Callable] = None
        self.speech_ended_callback: Optional[Callable] = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Calibrate microphone for ambient noise
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        try:
            with self.microphone as source:
                self.logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.logger.info("Microphone calibrated")
        except Exception as e:
            self.logger.error(f"Failed to calibrate microphone: {e}")
    
    def set_speech_callbacks(self, 
                           speech_detected: Optional[Callable] = None,
                           speech_ended: Optional[Callable] = None):
        """Set callbacks for speech detection events"""
        self.speech_detected_callback = speech_detected
        self.speech_ended_callback = speech_ended
    
    def start_listening(self) -> bool:
        """Start continuous listening for speech"""
        if self.is_recording:
            self.logger.warning("Already recording")
            return False
            
        try:
            self.is_recording = True
            self.recording_thread = threading.Thread(target=self._listen_continuously)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            self.logger.info("Started continuous listening")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start listening: {e}")
            self.is_recording = False
            return False
    
    def stop_listening(self):
        """Stop continuous listening"""
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
        self.logger.info("Stopped listening")
    
    def _listen_continuously(self):
        """Continuously listen for speech in background thread"""
        while self.is_recording:
            try:
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=10)
                    
                    if self.speech_detected_callback:
                        self.speech_detected_callback()
                    
                    # Put audio in queue for processing
                    self.audio_queue.put(audio)
                    
            except sr.WaitTimeoutError:
                # Normal timeout, continue listening
                pass
            except Exception as e:
                self.logger.error(f"Error in continuous listening: {e}")
                time.sleep(0.1)  # Brief pause before retrying
    
    def get_speech_text(self, timeout: float = 1.0) -> Optional[str]:
        """Get transcribed speech text from queue"""
        try:
            audio = self.audio_queue.get(timeout=timeout)
            text = self.recognizer.recognize_google(audio)
            self.logger.info(f"Recognized speech: {text}")
            
            if self.speech_ended_callback:
                self.speech_ended_callback(text)
                
            return text
        except queue.Empty:
            return None
        except sr.UnknownValueError:
            self.logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            self.logger.error(f"Speech recognition error: {e}")
            return None
    
    def record_audio(self, duration: float) -> bytes:
        """Record audio for specified duration"""
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            frames = []
            for _ in range(int(self.sample_rate / self.chunk_size * duration)):
                data = stream.read(self.chunk_size)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Convert to bytes
            audio_data = b''.join(frames)
            self.logger.info(f"Recorded {duration}s of audio")
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Failed to record audio: {e}")
            return b''
    
    def play_audio_data(self, audio_data: bytes, sample_rate: int = None):
        """Play raw audio data"""
        if sample_rate is None:
            sample_rate = self.sample_rate
            
        try:
            self.is_playing = True
            
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )
            
            # Play audio in chunks
            chunk_size = self.chunk_size * 2  # bytes per chunk
            for i in range(0, len(audio_data), chunk_size):
                if not self.is_playing:  # Allow interruption
                    break
                chunk = audio_data[i:i + chunk_size]
                stream.write(chunk)
            
            stream.stop_stream()
            stream.close()
            self.is_playing = False
            self.logger.info("Finished playing audio")
            
        except Exception as e:
            self.logger.error(f"Failed to play audio: {e}")
            self.is_playing = False
    
    def play_audio_file(self, file_path: str):
        """Play audio from file"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Audio file not found: {file_path}")
                return
                
            # Load and play using pydub
            audio = AudioSegment.from_file(file_path)
            self.is_playing = True
            play(audio)
            self.is_playing = False
            self.logger.info(f"Played audio file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to play audio file: {e}")
            self.is_playing = False
    
    def save_audio(self, audio_data: bytes, filename: str):
        """Save audio data to WAV file"""
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data)
            self.logger.info(f"Saved audio to: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save audio: {e}")
    
    def stop_playback(self):
        """Stop current audio playback"""
        self.is_playing = False
    
    def test_audio_devices(self):
        """Test and list available audio devices"""
        self.logger.info("Available audio devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            self.logger.info(f"Device {i}: {info['name']} - "
                           f"Inputs: {info['maxInputChannels']}, "
                           f"Outputs: {info['maxOutputChannels']}")
    
    def get_microphone_level(self) -> float:
        """Get current microphone input level (0.0 - 1.0)"""
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            stream.stop_stream()
            stream.close()
            
            # Calculate RMS level
            import numpy as np
            audio_array = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array**2))
            level = min(rms / 32767.0, 1.0)  # Normalize to 0-1
            
            return level
        except Exception as e:
            self.logger.error(f"Failed to get microphone level: {e}")
            return 0.0
    
    def cleanup(self):
        """Clean up audio resources"""
        self.stop_listening()
        self.stop_playback()
        if hasattr(self, 'audio'):
            self.audio.terminate()
        self.logger.info("Audio handler cleaned up")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()


class VoiceActivityDetector:
    """Simple voice activity detection"""
    
    def __init__(self, threshold: float = 0.01, min_duration: float = 0.3):
        self.threshold = threshold
        self.min_duration = min_duration
        self.is_speaking = False
        self.speech_start_time = None
        
    def update(self, audio_level: float) -> tuple[bool, bool]:
        """
        Update with current audio level
        Returns: (speech_detected, speech_ended)
        """
        current_time = time.time()
        
        if audio_level > self.threshold:
            if not self.is_speaking:
                self.speech_start_time = current_time
                self.is_speaking = True
                return True, False  # Speech started
        else:
            if self.is_speaking:
                # Check if we've been speaking long enough
                if current_time - self.speech_start_time > self.min_duration:
                    self.is_speaking = False
                    return False, True  # Speech ended
                
        return False, False  # No change