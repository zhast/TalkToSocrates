import asyncio
import pyaudio
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

CHUNK = 1024
FORMAT = pyaudio.paFloat32  # Changed to float32
CHANNELS = 1
RATE = 44100

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

@app.get("/")
async def get():
    html_content = """
    <html>
        <head>
            <title>Audio Streaming</title>
        </head>
        <body>
            <h1>Audio Streaming</h1>
            <button id="startButton">Start Streaming</button>
            <script>
                let audioContext;
                let socket;

                document.getElementById('startButton').onclick = function() {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    socket = new WebSocket('ws://localhost:8000/ws');
                    socket.binaryType = 'arraybuffer';
                    
                    socket.onmessage = function(event) {
                        let floats = new Float32Array(event.data);
                        let audioBuffer = audioContext.createBuffer(1, floats.length, 44100);
                        audioBuffer.copyToChannel(floats, 0);
                        
                        let source = audioContext.createBufferSource();
                        source.buffer = audioBuffer;
                        source.connect(audioContext.destination);
                        source.start();
                    };
                };
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            float_data = np.frombuffer(data, dtype=np.float32)
            await websocket.send_bytes(float_data.tobytes())
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)