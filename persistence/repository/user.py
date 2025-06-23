from flask import g
from sqlalchemy import func


class UserRepository:
    @staticmethod
    def save(user):
        g.session.add(user)
        g.session.commit()

        return user

    @staticmethod
    def delete(user):
        g.session.delete(user)
        g.session.commit()

    @staticmethod
    def find_by_name(name):
        name = name.lower()
        statement = (
            User
            .select()
            .where(func.lower(User.name) == name)
        )

        return g.session.scalar(statement)

    @staticmethod
    def find_by_id(user_id):
        statement = (
            User
            .select()
            .where(User.id == user_id)
        )

        return g.session.scalar(statement)

    @staticmethod
    def find_all():
        statement = (
            User
            .select()
            .order_by(User.name)
        )

        return g.session.scalars(statement)


from persistence.model.user import User
