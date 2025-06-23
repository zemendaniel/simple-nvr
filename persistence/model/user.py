from alchemical import Model
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash


class User(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(180), nullable=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)

    def save(self):
        UserRepository.save(self)

    def delete(self):
        UserRepository.delete(self)

    def check_password(self, password) -> bool:
        return check_password_hash(self.password, password)


from persistence.repository.user import UserRepository
