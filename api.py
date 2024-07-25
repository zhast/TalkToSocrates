from flask import Flask, Response
from flask_cors import CORS
import pyaudio
import threading
import queue
import pydub
import io

app = Flask(__name__)
CORS(app)

# Audio stream configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Initialize PyAudio
audio = pyaudio.PyAudio()
audio_stream = audio.open(format=FORMAT, channels=CHANNELS,
                          rate=RATE, input=True,
                          frames_per_buffer=CHUNK)

# Create a queue to hold audio data
audio_queue = queue.Queue(maxsize=100)

# Function to continuously read audio data
def audio_capture():
    while True:
        try:
            data = audio_stream.read(CHUNK, exception_on_overflow=False)
            audio_queue.put(data, block=False)
        except queue.Full:
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                pass
        except Exception as e:
            print(f"Error capturing audio: {e}")

# Start audio capture in a separate thread
threading.Thread(target=audio_capture, daemon=True).start()

@app.route('/stream')
def stream_audio():
    def generate():
        accumulated_data = b''
        while True:
            try:
                while len(accumulated_data) < RATE * 2:  # Accumulate ~1 second of audio
                    data = audio_queue.get(timeout=1)
                    accumulated_data += data
                
                # Convert to MP3
                audio_segment = pydub.AudioSegment(
                    accumulated_data,
                    frame_rate=RATE,
                    sample_width=2,
                    channels=CHANNELS
                )
                mp3_buffer = io.BytesIO()
                audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
                mp3_data = mp3_buffer.getvalue()
                
                yield mp3_data
                accumulated_data = b''
            except queue.Empty:
                yield b''

    return Response(generate(), mimetype="audio/mpeg")

@app.route('/')
def index():
    return """
    <html>
        <body>
            <audio controls>
                <source src="/stream" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)