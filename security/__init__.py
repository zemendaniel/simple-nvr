from flask import g, session
from persistence.repository.user import UserRepository


def init_app(app):
    app.before_request(__load_current_user)
    app.jinja_env.globals['is_fully_authenticated'] = lambda: g.user
    app.jinja_env.globals['is_admin'] = lambda: g.user and g.user.role == "admin"


def __load_current_user():
    user_id = session.get('user_id')
    g.user = UserRepository.find_by_id(user_id) if user_id else None
