from numbers import Number
from fastapi import FastAPI, Query
from pydantic import AfterValidator, BaseModel
import re
from typing import Annotated, Any
from database import Base, engine
from routes  import users, auth


app = FastAPI()

Base.metadata.create_all(bind=engine)



app.include_router(users.router)
#app.include_router(auth.router)

