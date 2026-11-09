import socket
import winsound

def start_tts_server(host='0.0.0.0', port=5001):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Listening for TTS audio on port {port}...")

    while True:
        conn, addr = server_socket.accept()
        print(f"Receiving audio from {addr}...")
        
        audio_data = bytearray()
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            audio_data.extend(chunk)
            
        output_filename = "latest_tts_playback.wav"
        with open(output_filename, "wb") as f:
            f.write(audio_data)
            
        print("Playing audio...")
        # Play the WAV file using Windows' built-in sound library
        # SND_FILENAME tells it to read from the file, SND_NODEFAULT prevents system beeps on error
        winsound.PlaySound(output_filename, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        print("Playback complete. Ready for next message.\n")
        
        conn.close()

if __name__ == "__main__":
    start_tts_server()