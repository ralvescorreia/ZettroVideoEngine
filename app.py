import os
import random
from flask import Flask, request, send_file, jsonify
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image
import numpy as np
import requests

app = Flask(__name__)

def extrair_termo_busca(roteiro, termo_original):
    if termo_original and "undefined" not in termo_original.lower() and len(termo_original.strip()) > 2:
        return termo_original.strip()
    
    marcas = ['corolla', 'toyota', 'porsche', 'ferrari', 'bmw', 'audi', 'mercedes', 'mustang', 'honda', 'civic']
    texto_min = str(roteiro).lower()
    for marca in marcas:
        if marca in texto_min:
            if marca == 'corolla':
                return "toyota,corolla"
            return marca
            
    return "supercar"

@app.route('/generate-video', methods=['POST'])
def generate_video():
    roteiro_texto = request.form.get('roteiro', '')
    termo_recebido = request.form.get('search_term', '')

    if not roteiro_texto and request.is_json:
        data = request.get_json(silent=True) or {}
        roteiro_texto = data.get('roteiro', '')
        termo_recebido = data.get('search_term', '')

    if 'audio_file' not in request.files:
        return jsonify({"error": "Falta o arquivo de áudio binário (audio_file)"}), 400
        
    audio_file = request.files['audio_file']
    audio_path = "temp_audio.mp3"
    output_video_path = "output_zettro.mp4"
    
    audio_file.save(audio_path)

    search_term = extrair_termo_busca(roteiro_texto, termo_recebido)

    audio_clip = AudioFileClip(audio_path)
    video_duration = audio_clip.duration

    urls = [
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=1",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=2",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=3",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=4",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=5"
    ]

    duration_per_slide = video_duration / len(urls)
    clips = []

    # Cabeçalho para simular um navegador comum e evitar bloqueio de robôs no Render
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for idx, url in enumerate(urls):
        try:
            img_name = f"img_{idx}.jpg"
            # Fazemos o download passando os headers simulados
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                with open(img_name, 'wb') as handler:
                    handler.write(response.content)

                pil_img = Image.open(img_name).convert('RGB').resize((1080, 1920))
                img_array = np.array(pil_img)
                
                clip = ImageClip(img_array).set_duration(duration_per_slide)
                clips.append(clip)
            else:
                print(f"Erro HTTP {response.status_code} na imagem {idx}")
        except Exception as e:
            print(f"Erro ao processar imagem {idx} via PIL/NumPy: {e}")
            continue

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
