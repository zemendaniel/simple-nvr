from datetime import date, datetime
from sqlalchemy import func, or_
from flask import g


class CamRepository:
    @staticmethod
    def find_all():
        statement = (
            Cam
            .select().order_by(Cam.id)
        )

        return g.session.scalars(statement).all()

    @staticmethod
    def find_all_enabled():
        statement = (
            Cam
            .select()
            .where(Cam.enabled == True)
            .order_by(Cam.id)
        )

        return g.session.scalars(statement).all()

    @staticmethod
    def find_by_id(cam_id: int):
        statement = (
            Cam
            .select()
            .where(Cam.id == cam_id)
        )

        return g.session.scalar(statement)

    @staticmethod
    def save(cam):
        g.session.add(cam)
        g.session.commit()

    @staticmethod
    def delete(cam) -> None:
        g.session.delete(cam)
        g.session.commit()


from persistence.model.cam import Cam
