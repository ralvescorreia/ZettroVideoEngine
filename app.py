import os
from flask import Flask, request, send_file, jsonify
from moviepy.editor import ImageClip, AudioFileClip
from PIL import Image
import numpy as np

app = Flask(__name__)

@app.route('/generate-video', methods=['POST'])
def generate_video():
    roteiro_texto = request.form.get('roteiro', '')
    
    if 'audio_file' not in request.files:
        return jsonify({"error": "Falta o arquivo de áudio binário (audio_file)"}), 400
        
    audio_file = request.files['audio_file']
    audio_path = "temp_audio.mp3"
    output_video_path = "output_zettro.mp4"
    
    # Salva o áudio do n8n
    audio_file.save(audio_path)

    # Carrega o áudio para saber a duração exata
    audio_clip = AudioFileClip(audio_path)
    video_duration = audio_clip.duration

    try:
        # Em vez de carregar várias fotos, criamos uma única imagem de fundo sólida e elegante (grafite escuro)
        # Isso reduz o uso de RAM para quase zero e acelera o processamento no Render
        pil_img = Image.new('RGB', (1080, 1920), color=(25, 25, 25))
        img_array = np.array(pil_img)
        
        # Cria o clipe com a duração exata do áudio
        video_clip = ImageClip(img_array).set_duration(video_duration)
        video_clip = video_clip.set_audio(audio_clip)

        # Renderiza com configurações ultra-rápidas (preset='ultrafast') para evitar o timeout do Render
        video_clip.write_videofile(
            output_video_path, 
            fps=15, # Reduzido para fluidez básica
            codec="libx264", 
            audio_codec="aac",
            bitrate="800k", # Bitrate mais leve
            preset="ultrafast", # O segredo para renderizar em segundos
            threads=1,
            logger=None
        )

        audio_clip.close()
        video_clip.close()

        return send_file(output_video_path, mimetype='video/mp4')

    except Exception as e:
        print(f"Erro na renderização rápida: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
