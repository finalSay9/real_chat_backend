from sqlalchemy import Column, Integer, String
from database import Base


class User(Base):
    __tablename__ = "users"


    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    fullname =Column(String, index=True)
    hashed_password = Column(String, nullable=False)