import re
from datetime import datetime
from io import BytesIO
from persistence.repository.cam import CamRepository
from flask import redirect, url_for, flash, render_template, send_file, g, abort, request, Response
from blueprints.clips import bp
from security.decorators import is_admin, is_fully_authenticated
from persistence.model.app_config import AppConfig
import os


@bp.route('/')
@is_fully_authenticated
def list_all():
    cams = CamRepository.find_all()
    saved = request.args.get('saved')
    cam_id = None
    if cams:
        cam_id = request.args.get('cam', type=int)
        if cam_id:
            if not CamRepository.find_by_id(cam_id):
                abort(404)
            g.user.last_viewed_cam = cam_id
            g.user.save()
        else:
            last_viewed = g.user.last_viewed_cam
            if CamRepository.find_by_id(last_viewed):
                cam_id = g.user.last_viewed_cam
            else:
                cam_id = cams[0].id
        
        if saved:
            clip_dir = f'{AppConfig.get().root_folder}/saved/{cam_id}'
        else:
            clip_dir = f'{AppConfig.get().root_folder}/cams/{cam_id}'

        clips = []
        for f in os.listdir(clip_dir):
            if f.endswith('.mp4'):
                path = os.path.join(clip_dir, f)
                clips.append({
                    'name': f,
                    'modified': datetime.fromtimestamp(os.path.getmtime(path))
                })

        clips.sort(key=lambda x: x['modified'], reverse=True)

        if request.args.get('search'):
            from_datetime_str = request.args.get('from_datetime')
            to_datetime_str = request.args.get('to_datetime')

            try:
                if from_datetime_str:
                    from_datetime = datetime.strptime(from_datetime_str, '%Y-%m-%dT%H:%M')
                    clips = [c for c in clips if c['modified'] >= from_datetime]
                if to_datetime_str:
                    to_datetime = datetime.strptime(to_datetime_str, '%Y-%m-%dT%H:%M')
                    clips = [c for c in clips if c['modified'] <= to_datetime]
            except ValueError:
                pass  # ignore invalid formats

    else:
        clips = []
    
    return render_template('clips/list.html', clips=clips, cams=cams, saved=saved, cam_id=cam_id)


@bp.route('/play/<filename>')
@is_fully_authenticated
def play(filename):
    saved = request.args.get('saved', default=None)  # "true" or None
    cam_id = request.args.get('cam_id')
    if cam_id is None:
        return "Missing camera ID", 400

    if saved:
        base_dir = f"clips/saved/{cam_id}"
    else:
        base_dir = f"clips/cams/{cam_id}"

    safe_base = os.path.abspath(base_dir)
    file_path = os.path.abspath(os.path.join(safe_base, filename))

    if not file_path.startswith(safe_base):
        return "Forbidden", 403

    if not os.path.exists(file_path):
        return "File not found", 404

    # Let Flask/Werkzeug handle Range requests natively:
    try:
        return send_file(file_path, mimetype='video/mp4', conditional=True)
    except Exception:
        # If send_file doesn't handle range properly, fallback to manual handling
        range_header = request.headers.get('Range', None)
        size = os.path.getsize(file_path)
        byte1, byte2 = 0, size - 1

        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                byte1 = int(match.group(1))
                if match.group(2):
                    byte2 = int(match.group(2))
        length = byte2 - byte1 + 1

        with open(file_path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        rv = Response(data, 206 if range_header else 200, mimetype='video/mp4', direct_passthrough=True)
        if range_header:
            rv.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
            rv.headers.add('Accept-Ranges', 'bytes')
            rv.headers.add('Content-Length', str(length))
        return rv
