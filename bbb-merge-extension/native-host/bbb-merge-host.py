#!/usr/bin/env python3
import json
import struct
import sys
import os
import subprocess
import tempfile
import shutil
import time
import platform
from urllib.request import Request, urlopen
from urllib.error import URLError


def send_message(msg):
    encoded = json.dumps(msg, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('<I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def read_message():
    raw = sys.stdin.buffer.read(4)
    if not raw or len(raw) < 4:
        return None
    length = struct.unpack('<I', raw)[0]
    if length == 0:
        return None
    data = sys.stdin.buffer.read(length)
    return json.loads(data)


def download_file(url, output_path, cookies='', timeout=300):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    if cookies:
        headers['Cookie'] = cookies
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        with open(output_path, 'wb') as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
    return output_path


def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def merge_videos(deskshare_path, webcams_path, output_path):
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', deskshare_path,
            '-i', webcams_path,
            '-c', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-1000:] if result.stderr else 'Unknown ffmpeg error')
        return True
    except subprocess.TimeoutExpired:
        raise RuntimeError('ffmpeg timeout after 2 hours')
    except FileNotFoundError:
        raise RuntimeError('ffmpeg not found')


def main():
    send_message({'type': 'ready'})

    msg = read_message()
    if not msg or msg.get('type') != 'merge':
        send_message({'type': 'error', 'text': 'Invalid message type'})
        return

    deskshare_url = msg.get('deskshareUrl') or None
    webcams_url = msg.get('webcamsUrl') or None
    cookies = msg.get('cookies', '')

    if not deskshare_url and not webcams_url:
        send_message({'type': 'error', 'text': 'No video URLs provided'})
        return

    if not check_ffmpeg():
        send_message({
            'type': 'error',
            'text': 'ffmpeg no está instalado. Instálalo con: sudo apt install ffmpeg (Linux), brew install ffmpeg (macOS), o winget install ffmpeg (Windows)'
        })
        return

    temp_dir = tempfile.mkdtemp(prefix='bbb_merge_')
    downloads_dir = os.path.expanduser('~/Downloads')
    timestamp = int(time.time())
    output_filename = f'BBB_merged_{timestamp}.webm'
    output_path = os.path.join(downloads_dir, output_filename)

    try:
        deskshare_local = None
        webcams_local = None

        if deskshare_url:
            send_message({'type': 'progress', 'text': '📥 Descargando video de pantalla (deskshare.webm)...'})
            deskshare_local = os.path.join(temp_dir, 'deskshare.webm')
            try:
                download_file(deskshare_url, deskshare_local, cookies)
            except URLError as e:
                send_message({'type': 'error', 'text': f'Error al descargar deskshare.webm: {str(e)}'})
                return
            except Exception as e:
                send_message({'type': 'error', 'text': f'Error inesperado al descargar deskshare.webm: {str(e)}'})
                return

        if webcams_url:
            send_message({'type': 'progress', 'text': '📥 Descargando video de webcams (webcams.webm)...'})
            webcams_local = os.path.join(temp_dir, 'webcams.webm')
            try:
                download_file(webcams_url, webcams_local, cookies)
            except URLError as e:
                send_message({'type': 'error', 'text': f'Error al descargar webcams.webm: {str(e)}'})
                return
            except Exception as e:
                send_message({'type': 'error', 'text': f'Error inesperado al descargar webcams.webm: {str(e)}'})
                return

        if deskshare_local and webcams_local:
            send_message({'type': 'progress', 'text': '🔀 Uniendo video de pantalla con audio de webcams...'})
            try:
                merge_videos(deskshare_local, webcams_local, output_path)
                send_message({
                    'type': 'complete',
                    'text': f'✅ Video guardado en: Descargas/{output_filename}',
                    'path': output_path
                })
            except RuntimeError as e:
                send_message({'type': 'error', 'text': f'Error al unir: {str(e)}'})
                return

        elif webcams_local:
            shutil.copy2(webcams_local, output_path)
            send_message({
                'type': 'complete',
                'text': f'⚠️ Solo se encontró webcams.webm. Copiado a Descargas/{output_filename}',
                'path': output_path
            })

        elif deskshare_local:
            shutil.copy2(deskshare_local, output_path)
            send_message({
                'type': 'complete',
                'text': f'⚠️ Solo se encontró deskshare.webm (sin audio). Copiado a Descargas/{output_filename}',
                'path': output_path
            })

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        send_message({'type': 'error', 'text': f'Error interno: {str(e)}'})
