import os
import random
from flask import Flask, request, send_file, jsonify
from duckduckgo_search import DDGS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, vfx
import requests

app = Flask(__name__)

def download_images(query, count=5):
    image_urls = []
    try:
        with DDGS() as ddgs:
            results = ddgs.images(query, max_results=20)
            # Filtra links válidos e mistura para dar dinamismo
            urls = [r['image'] for r in results if r['image'].startswith('http')]
            random.shuffle(urls)
            image_urls = urls[:count]
    except Exception as e:
        print(f"Erro na busca de imagens: {e}")
    return image_urls

@app.route('/generate-video', methods=['POST'])
def generate_video():
    data = request.json
    search_term = data.get('search_term', 'Toyota Corolla GR')
    audio_url = data.get('audio_url') # Link do áudio temporário enviado pelo n8n
    
    if not audio_url:
        return jsonify({"error": "Falta a URL do áudio da ElevenLabs"}), 400

    # 1. Baixar o áudio gerado no n8n
    audio_path = "temp_audio.mp3"
    output_video_path = "output_zettro.mp4"
    
    r = requests.get(audio_url)
    with open(audio_path, 'wb') as f:
        f.write(r.content)

    # 2. Carregar o áudio para saber a duração exata do vídeo
    audio_clip = AudioFileClip(audio_path)
    video_duration = audio_clip.duration

    # 3. Buscar fotos dinamicamente na internet baseadas no modelo do carro
    urls = download_images(search_term, count=5)
    if not urls:
        # Imagens fallback caso a busca falhe
        urls = [
            "https://images.unsplash.com/photo-1621259182978-f09e5e2b091e?w=1080",
            "https://images.unsplash.com/photo-1617788130017-80ad40651399?w=1080"
        ]

    # 4. Criar os cortes de slide no formato vertical 9:16 (1080x1920)
    duration_per_slide = video_duration / len(urls)
    clips = []

    for idx, url in enumerate(urls):
        try:
            # Baixa a imagem localmente para processar
            img_name = f"img_{idx}.jpg"
            img_data = requests.get(url, timeout=5).content
            with open(img_name, 'wb') as handler:
                handler.write(img_data)

            # Cria o clip de imagem configurando tamanho vertical de Reels
            clip = ImageClip(img_name).set_duration(duration_per_slide).resize(height=1920)
            
            # Garante que a largura fique centralizada em 1080 (formato Reels)
            if clip.w > 1080:
                clip = clip.crop(x_center=clip.w/2, width=1080)
            
            # Aplica um efeito de zoom progressivo básico (Ken Burns simulado por script)
            # Para simplificar na nuvem sem estourar memória RAM de 512MB do Render:
            if idx % 2 == 0:
                clip = clip.fx(vfx.zoom, lambda t: 1 + 0.03 * (t / duration_per_slide))
            else:
                clip = clip.fx(vfx.zoom, lambda t: 1.03 - 0.03 * (t / duration_per_slide))

            clips.append(clip)
        except Exception as e:
            print(f"Erro ao processar imagem {idx}: {e}")
            continue

    if not clips:
        return jsonify({"error": "Não foi possível renderizar nenhum slide de imagem."}), 500

    # 5. Concatenar e juntar áudio + vídeo
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_audio(audio_clip)

    # 6. Exportar arquivo final otimizado para servidores leves de 512MB RAM
    final_video.write_videofile(
        output_video_path, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac",
        bitrate="2000k",
        threads=2,
        logger=None
    )

    # Fecha os arquivos abertos na memória
    audio_clip.close()
    final_video.close()

    # Retorna o arquivo de vídeo bruto diretamente para o n8n
    return send_file(output_video_path, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
