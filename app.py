import os
import random
from flask import Flask, request, send_file, jsonify
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
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

    # O SEGREDO: Limitamos o tamanho da imagem direto na URL (&w=600&h=1066) para não estourar os 512MB de RAM do Render
    urls = [
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=1",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=2",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=3",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=4",
        f"https://images.unsplash.com/featured/?{search_term}&w=600&h=1066&fit=crop&sig=5"
    ]

    duration_per_slide = video_duration / len(urls)
    clips = []

    for idx, url in enumerate(urls):
        try:
            img_name = f"img_{idx}.jpg"
            img_data = requests.get(url, timeout=10).content
            with open(img_name, 'wb') as handler:
                handler.write(img_data)

            # Carrega a imagem já leve e removemos os efeitos pesados de movimento (zoom) para economizar CPU
            clip = ImageClip(img_name).set_duration(duration_per_slide).resize(newsize=(1080, 1920))
            clips.append(clip)
        except Exception as e:
            print(f"Erro na imagem {idx}: {e}")
            continue

    if not clips:
        return jsonify({"error": "Nenhum slide pôde ser gerado"}), 500

    # Processamento simplificado focado em baixa RAM
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_audio(audio_clip)

    final_video.write_videofile(
        output_video_path, 
        fps=20, # Reduzido levemente de 24 para 20 fps para processar mais rápido
        codec="libx264", 
        audio_codec="aac",
        bitrate="1500k",
        threads=1, # Força rodar em thread única para não travar a CPU free do Render
        logger=None
    )

    audio_clip.close()
    final_video.close()

    return send_file(output_video_path, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
