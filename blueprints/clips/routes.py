from io import BytesIO

from flask import redirect, url_for, flash, render_template, send_file, current_app, send_from_directory
from blueprints.clips import bp
from security.decorators import is_admin, is_fully_authenticated
from persistence.model.app_config import AppConfig
import os


@bp.route('/')
@is_fully_authenticated
def list_all():
    clips = [f for f in os.listdir('clips/cams/1') if f.endswith('.mp4')]
    return render_template('clips/list.html', clips=clips)


@bp.route('/play/<filename>')
@is_fully_authenticated
def play(filename):
    file_path = f"clips/cams/1/{filename}"

    if not os.path.exists(file_path):
        return "File not found", 404

    return send_file(file_path,
                     mimetype='video/mp4',
                     as_attachment=False,
                     download_name=filename)
