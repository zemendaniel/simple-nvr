from flask import redirect, url_for, Response, stream_with_context, render_template, abort, flash
from blueprints.cams import bp
from security.decorators import is_fully_authenticated, is_admin
from .forms import CamForm
from persistence.model.cam import Cam
from persistence.repository.cam import CamRepository


@bp.route('/video/<int:cam_id>')
@is_fully_authenticated
def video_feed(cam_id):
    from app import camera_manager

    cam = camera_manager.get_camera(cam_id) or abort(404)
    return Response(
        stream_with_context(cam.generate_frames()),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@bp.route('/snapshot/<int:cam_id>')
@is_fully_authenticated
def snapshot(cam_id):
    from app import camera_manager

    cam = camera_manager.get_camera(cam_id) or abort(404)
    frame = cam.get_frame()
    if frame:
        return Response(response=frame, mimetype='image/jpeg')
    else:
        return Response("Camera frame not available.", status=404)


@bp.route('/')
@is_fully_authenticated
def list_all():
    from app import camera_manager

    cams = camera_manager.cameras
    return render_template("cams/list.html", cams=cams)


@bp.route('/create', methods=['GET', 'POST'])
@is_fully_authenticated
@is_admin
def create():
    form = CamForm()
    cam = Cam()

    if form.validate_on_submit():
        form.populate_obj(cam)
        cam.save()
        from app import camera_manager
        camera_manager.reload_cameras()
        flash("Camera added successfully", "success")
        return redirect(url_for('pages.home'))

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
        from app import camera_manager
        camera_manager.reload_cameras()
        flash("Camera modified successfully", "success")
        return redirect(url_for('pages.home'))

    return render_template("cams/form.html", form=form, cam=cam)

