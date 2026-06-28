import os
import random
from flask import Flask, request, send_file, jsonify
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image
import numpy as np
import requests

app = Flask(__name__)

@app.route('/generate-video', methods=['POST'])
def generate_video():
    roteiro_texto = request.form.get('roteiro', '')
    
    if not roteiro_texto and request.is_json:
        data = request.get_json(silent=True) or {}
        roteiro_texto = data.get('roteiro', '')

    if 'audio_file' not in request.files:
        return jsonify({"error": "Falta o arquivo de áudio binário (audio_file)"}), 400
        
    audio_file = request.files['audio_file']
    audio_path = "temp_audio.mp3"
    output_video_path = "output_zettro.mp4"
    
    audio_file.save(audio_path)

    audio_clip = AudioFileClip(audio_path)
    video_duration = audio_clip.duration

    # Usando o Picsum Photos com IDs aleatórios estáveis para garantir imagens reais verticais e sem erro 404!
    urls = [
        "https://picsum.photos/id/1071/1080/1920", # Foto de rodovia/carro
        "https://picsum.photos/id/133/1080/1920",  # Carro clássico / estrada
        "https://picsum.photos/id/54/1080/1920",   # Paisagem urbana moderna
        "https://picsum.photos/id/76/1080/1920",   # Estrada/viagem
        "https://picsum.photos/id/435/1080/1920"   # Cidade/infraestrutura
    ]

    duration_per_slide = video_duration / len(urls)
    clips = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    for idx, url in enumerate(urls):
        try:
            img_name = f"img_{idx}.jpg"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                with open(img_name, 'wb') as handler:
                    handler.write(response.content)

                pil_img = Image.open(img_name).convert('RGB')
                img_array = np.array(pil_img)
                
                clip = ImageClip(img_array).set_duration(duration_per_slide)
                clips.append(clip)
            else:
                print(f"Aviso: Erro HTTP {response.status_code} na imagem {idx}. Usando fallback.")
                raise Exception("Fallback")
        except Exception:
            # SE TUDO FALHAR: Cria uma imagem sólida escura (Preto/Grafite elegante) para o vídeo nunca quebrar!
            pil_img = Image.new('RGB', (1080, 1920), color=(20, 20, 20))
            img_array = np.array(pil_img)
            clip = ImageClip(img_array).set_duration(duration_per_slide)
            clips.append(clip)

    if not clips:
        return jsonify({"error": "Nenhum slide pôde ser gerado"}), 500

    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_audio(audio_clip)

    final_video.write_videofile(
        output_video_path, 
        fps=20, 
        codec="libx264", 
        audio_codec="aac",
        bitrate="1500k",
        threads=1, 
        logger=None
    )

    audio_clip.close()
    final_video.close()

    return send_file(output_video_path, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
