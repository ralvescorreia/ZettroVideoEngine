import os
import subprocess
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

@app.route('/generate-video', methods=['POST'])
def generate_video():
    # 1. Limpeza de arquivos de execuções anteriores para não lotar o disco
    audio_path = "input_audio.mp3"
    img_path = "fundo_grafite.png"
    output_video_path = "output_zettro.mp4"
    
    for arquivo in [audio_path, output_video_path]:
        if os.path.exists(arquivo):
            try:
                os.remove(arquivo)
            except Exception as e:
                print(f"Erro ao remover arquivo antigo {arquivo}: {e}")

    # 2. Receber o arquivo de áudio vindo do n8n (ElevenLabs)
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo de audio enviado no campo 'file'"}), 400
    
    audio_file = request.files['file']
    audio_file.save(audio_path)

    # 3. Validar se a imagem de fundo existe no repositório
    if not os.path.exists(img_path):
        return jsonify({"error": f"A imagem de fundo '{img_path}' nao foi encontrada no servidor."}), 500

    try:
        # 4. Comando FFmpeg Ultra-Light (MPEG4 + compressão inteligente)
        # Evita estourar o timeout e processa o Reels em poucos segundos
        comando = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', img_path,
            '-i', audio_path,
            '-c:v', 'mpeg4', '-q:v', '5',
            '-c:a', 'aac', '-b:a', '96k',
            '-shortest',
            output_video_path
        ]

        print("Iniciando renderizacao do video com FFmpeg...")
        subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Video gerado com sucesso!")

        # Retorna o arquivo binário diretamente para o n8n registrar o nó com sucesso
        return send_file(output_video_path, mimetype='video/mp4')

    except subprocess.CalledProcessError as e:
        print(f"Erro no FFmpeg: {e}")
        return jsonify({"error": "Falha ao processar o video com o FFmpeg"}), 500
    except Exception as e:
        print(f"Erro interno: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download-video', methods=['GET'])
def download_video():
    """
    Rota publica para o Instagram (via Make) baixar o video 
    diretamente do servidor da ZETTRO de forma automatica.
    """
    output_video_path = "output_zettro.mp4"
    if os.path.exists(output_video_path):
        return send_file(output_video_path, mimetype='video/mp4')
    else:
        return jsonify({"error": "Video final ainda nao foi gerado ou nao foi encontrado"}), 404

if __name__ == '__main__':
    # Porta padrão exigida pelo Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
