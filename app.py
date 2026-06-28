import os
import random
import re
from flask import Flask, request, send_file, jsonify
from duckduckgo_search import DDGS
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
                return "Toyota Corolla 2026"
            return marca.capitalize()
            
    return "Sports Car 2026"

def download_images(query, count=5):
    image_urls = []
    try:
        with DDGS() as ddgs:
            results = ddgs.images(query, max_results=15)
            urls = [r['image'] for r in results if r['image'].startswith('http')]
            random.shuffle(urls)
            image_urls = urls[:count]
    except Exception as e:
        print(f"Erro na busca de imagens: {e}")
    return image_urls

@app.route('/generate-video', methods=['POST'])
def generate_video():
    # Coleta os dados de forma resiliente se vier como Form, Multipart ou JSON
    roteiro_texto = request.form.get('roteiro', '')
    termo_recebido = request.form.get('search_term', '')

    # Se mesmo assim vier vazio, tenta buscar do JSON caso o n8n force o cabeçalho
    if not roteiro_texto and request.is_json:
        data = request.get_json(silent=True) or {}
        roteiro_texto = data.get('roteiro', '')
        termo_recebido = data.get('search_term', '')

    # Valida se o arquivo de áudio veio
    if 'audio_file' not in request.files:
        return jsonify({"error": "Falta o arquivo de áudio binário (audio_file) na requisição"}), 400
        
    audio_file = request.files['audio_file']
    audio_path = "temp_audio.mp3"
    output_video_path = "output_zettro.mp4"
    
    # Salva o arquivo enviado
    audio_file.save(audio_path)

    # Descobre o termo de busca das imagens
    search_term = extrair_termo_busca(roteiro_texto, termo_recebido)

    # Processamento do vídeo com MoviePy
    audio_clip = AudioFileClip(audio_path)
    video_duration = audio_clip.duration

    urls = download_images(search_term, count=5)
    if not urls:
        urls = [
            "https://images.unsplash.com/photo-1621259182978-f09e5e2b091e?w=1080",
            "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1080"
        ]

    duration_per_slide = video_duration / len(urls)
    clips = []

    for idx, url in enumerate(urls):
        try:
            img_name = f"img_{idx}.jpg"
            img_data = requests.get(url, timeout=5).content
            with open(img_name, 'wb') as handler:
                handler.write(img_data)

            clip = ImageClip(img_name).set_duration(duration_per_slide).resize(height=1920)
            if clip.w > 1080:
                clip = clip.crop(x_center=clip.w/2, width=1080)
            
            if idx % 2 == 0:
                clip = clip.fx(vfx.zoom, lambda t: 1 + 0.04 * (t / duration_per_slide))
            else:
                clip = clip.fx(vfx.zoom, lambda t: 1.04 - 0.04 * (t / duration_per_slide))

            clips.append(clip)
        except Exception as e:
            print(f"Erro na imagem {idx}: {e}")
            continue

    if not clips:
        return jsonify({"error": "Nenhum slide gerado"}), 500

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
