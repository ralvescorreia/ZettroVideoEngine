import os
import subprocess
from flask import Flask, request, send_file, jsonify
from PIL import Image

app = Flask(__name__)

@app.route('/generate-video', methods=['POST'])
def generate_video():
    if 'audio_file' not in request.files:
        return jsonify({"error": "Falta o arquivo de áudio binário (audio_file)"}), 400
        
    audio_file = request.files['audio_file']
    audio_path = "temp_audio.mp3"
    output_video_path = "output_zettro.mp4"
    img_path = "temp_background.jpg"
    
    # 1. Salva o áudio
    audio_file.save(audio_path)

    try:
        # 2. Cria uma imagem sólida leve em disco (600x1066 para ficar bem leve)
        pil_img = Image.new('RGB', (600, 1066), color=(25, 25, 25))
        pil_img.save(img_path, "JPEG", quality=80)
        
        # 3. Remove arquivos antigos se existirem para não travar o FFmpeg
        if os.path.exists(output_video_path):
            os.remove(output_video_path)

        # 4. Comando FFmpeg: Lê a imagem em loop, junta o áudio e encoda em tempo real direto pro arquivo
        # Usamos ultrafast e bitrates baixos para a CPU do Render não sofrer
        comando = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', img_path,
            '-i', audio_path,
            '-c:v', 'libx264', '-tune', 'stillimage', '-preset', 'ultrafast',
            '-c:a', 'aac', '-b:a', '96k',
            '-pix_fmt', 'yuv420p', '-shortest',
            output_video_path
        ]
        
        # Executa o processo no sistema operacional
        subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Limpeza de temporários
        if os.path.exists(audio_path): os.remove(audio_path)
        if os.path.exists(img_path): os.remove(img_path)

        return send_file(output_video_path, mimetype='video/mp4')

    except subprocess.CalledProcessError as e:
        print(f"Erro crítico no FFmpeg: {e}")
        return jsonify({"error": "Falha na execução do FFmpeg de sistema"}), 500
    except Exception as e:
        print(f"Erro geral: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
