import os
import random
import re
from flask import Flask, request, send_file, jsonify
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, vfx
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

    # Descobre o termo (ex: "toyota,corolla")
    search_term = extrair_termo_busca(roteiro_texto, termo_recebido)

    audio_clip = AudioFileClip(audio_path)
    video_duration = audio_clip.duration

    # Geramos 5 URLs dinâmicas do Unsplash que usam a API de imagens deles sem bloqueio de IP
    # Mudando o "sig" a cada imagem, forçamos o Unsplash a entregar fotos diferentes do carro
    urls = [
        f"https://images.unsplash.com/featured/1080x1920/?{search_term}&sig=1",
        f"https://images.unsplash.com/featured/1080x1920/?{search_term}&sig=2",
        f"https://images.unsplash.com/featured/1080x1920/?{search_term}&sig=3",
        f"https://images.unsplash.com/featured/1080x1920/?{search_term}&sig=4",
        f"https://images.unsplash.com/featured/1080x1920/?{search_term}&sig=5"
    ]

    duration_per_slide = video_duration / len(urls)
    clips = []

    for idx, url in enumerate(urls):
        try:
            img_name = f"img_{idx}.jpg"
            # Baixa a foto direto do repositório público do Unsplash
            img_data = requests.get(url, timeout=10).content
            with open(img_name, 'wb') as handler:
                handler.write(img_data)

            clip = ImageClip(img_name).set_duration(duration_per_slide).resize(height=1920)
            if clip.w > 1080:
                clip = clip.crop(x_center=clip.w/2, width=1080)
            
            if idx % 2 == 0:
                clip = clip.fx(vfx.zoom, lambda t: 1 + 0.05 * (t / duration_per_slide))
            else:
                clip = clip.fx(vfx.zoom, lambda t: 1.05 - 0.05 * (t / duration_per_slide))

            clips.append(clip)
        except Exception as e:
            print(f"Erro na imagem {idx}: {e}")
            continue

    if not clips:
        return jsonify({"error": "Nenhum slide pôde ser gerado pelas URLs do Unsplash"}), 500

    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_audio(audio_clip)

    final_video.write_videofile(
        output_video_path, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac",
        bitrate="2500k",
        threads=2,
        logger=None
    )

    audio_clip.close()
    final_video.close()

    return send_file(output_video_path, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
