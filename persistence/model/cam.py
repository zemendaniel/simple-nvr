from alchemical import Model
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column


class Cam(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    folder: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    fps: Mapped[int] = mapped_column(Integer(), nullable=False)
    width: Mapped[int] = mapped_column(Integer(), nullable=False)
    height: Mapped[int] = mapped_column(Integer(), nullable=False)
    sensitivity: Mapped[int] = mapped_column(Integer(), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean(), default=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean(), default=True)

    def save(self):
        CamRepository.save(self)
        return self

    def delete(self):
        CamRepository.delete(self)


from persistence.repository.cam import CamRepository
