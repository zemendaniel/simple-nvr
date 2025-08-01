import time

from flask import redirect, url_for, Response, stream_with_context, render_template, abort, flash, request, g, session
from blueprints.cams import bp
from security.decorators import is_fully_authenticated, is_admin
from .forms import CamForm
from persistence.model.cam import Cam
from persistence.repository.cam import CamRepository
from cameras.manager import CameraManager


@bp.route('/video/<int:cam_id>')
@is_fully_authenticated
def video_feed(cam_id):
    cam = CameraManager.get_instance().get_camera(cam_id) or abort(404)
    return Response(
        stream_with_context(cam.generate_frames()),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@bp.route('/snapshot/<int:cam_id>')
@is_fully_authenticated
def snapshot(cam_id):
    cam = CameraManager.get_instance().get_camera(cam_id) or abort(404)
    frame = cam.get_frame()
    if frame:
        return Response(response=frame, mimetype='image/jpeg')
    else:
        return Response("Camera frame not available.", status=404)


@bp.route('/')
@is_fully_authenticated
def list_all():
    cam_manager = CameraManager.get_instance()
    cams = cam_manager.cameras
    cam_id = request.args.get('cam', type=int)

    if cam_id:
        selected_cam = next((cam for cam in cams if cam.id == cam_id), None) or abort(404)
        g.user.last_viewed_cam = selected_cam.id
        g.user.save()
    else:
        selected_cam = cam_manager.get_camera(g.user.last_viewed_cam)
        if not selected_cam and cams:
            selected_cam = cams[0]

    return render_template("cams/list.html", cams=cams, selected_cam=selected_cam)


@bp.route('/create', methods=['GET', 'POST'])
@is_fully_authenticated
@is_admin
def create():
    form = CamForm()
    cam = Cam()

    if form.validate_on_submit():
        form.populate_obj(cam)
        cam.save()
        session['pending_changes'] = True
        flash("Camera added successfully. You need to reload the cameras to apply the changes.", "success")
        return redirect(url_for('cams.settings'))

    return render_template("cams/form.html", create=True, form=form)


@bp.route('/edit/<int:cam_id>', methods=['GET', 'POST'])
@is_fully_authenticated
@is_admin
def edit(cam_id):
    cam = CamRepository.find_by_id(cam_id) or abort(404)
    form = CamForm(obj=cam)

    if form.validate_on_submit():
        form.populate_obj(cam)
        cam.save()
        session['pending_changes'] = True
        flash("Camera modified successfully. You need to reload the cameras to apply the changes.", "success")
        return redirect(url_for('cams.settings'))

    return render_template("cams/form.html", form=form, cam=cam)


@bp.route('/delete/<int:cam_id>', methods=['POST'])
@is_fully_authenticated
@is_admin
def delete(cam_id):
    cam = CamRepository.find_by_id(cam_id) or abort(404)
    cam.delete()
    session['pending_changes'] = True
    flash("Camera deleted successfully. You need to reload the cameras to apply the changes.", 'sucess')
    return redirect(url_for("cams.settings"))


@bp.route('/settings')
@is_fully_authenticated
@is_admin
def settings():
    cams = CamRepository.find_all()

    return render_template("cams/settings.html", cams=cams)


@bp.route('/reload', methods=['POST'])
@is_fully_authenticated
@is_admin
def reload():
    CameraManager.get_instance().reload_cameras()
    session['pending_changes'] = False
    flash("Cameras reloaded successfully", 'success')
    return redirect(url_for('cams.settings'))
