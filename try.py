import re
from fastapi import FastAPI, Path, Query
from fastapi.params import Depends
from pydantic import AfterValidator
from schemas import UserCreate, UserResponse
from typing import Annotated
from pydantic import BaseModel, Field



app = FastAPI(
    title="Tec | Vac"
    )

@app.post('/create_user', response_model=UserCreate)
async def create_user(create_user: UserCreate):
    return create_user

@app.get('/items')
def read_item(
    w: str | None = None,
    skip: int = 0,
    limit: int = 10
   ):
    return {"w": w, "skip": skip, "limit": limit}

@app.get('/search')
def searching(
    w: str | None = Query(
        default=None,
        min_length=0,
        max_length=50,
        pattern=r"^[a-zA-Z0-9\- ]+$",   # only letters, numbers, hyphen, space
        description="Search keyword (3-50 chars, alphanumeric + space/-)",
        examples=["python", "fast api", "ml-2025"]
    ),
   page: int = Query(
       default=1,
       ge=1,
       le=100,
       description='page number'
   )
  ):
    
    return {"w": w, "page": page}




def must_be_alphanumeric_and_not_too_generic(v: str) -> str:
    if len(v) < 3:
        raise ValueError("Too short")
    if not re.match(r"^[a-zA-Z0-9\- ]+$", v):
        raise ValueError("Only letters, numbers, space and hyphen allowed")
    if v.lower() in {"admin", "root", "test", "demo"}:
        raise ValueError("Generic names not allowed")
    return v

SearchQuery = Annotated[
    str,
    Query(min_length=3, max_length=80),
    AfterValidator(must_be_alphanumeric_and_not_too_generic)
]

@app.get("/products/")
async def list_products(q: SearchQuery | None = None):
    return {"search": q}
    

@app.get('/hey')
def hey(
    name: Annotated[list[str] | None, Query()] = None
  ):
    return name



@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[
        int,
        Path(
            title='the id of the item to get',
            description='must be positive integer between 1 to 1000',
            ge=1,
            le=1000,
            example=123
        )
    ]
  ):
    return {"item id": item_id}



class ItemFilter(BaseModel):
    q: str | None = Field(
        default=None,
        max_length=100,
        description="search keyword"
    )

    skip: int = Field(
        default=0,
        ge=0,
        description="number of items to skip(pagnation)"
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Max number of items to return"
    )
    min_price: float | None = Field(
        default=None,
        ge=0,
        description="Minimum price filter"
    )
    in_stock: bool = False

@app.get("/itemo/")
async def read_items(
    filters: ItemFilter = Depends()   # ← magic line
):
    # filters is already a validated ItemFilter object!
    return {
        "filters_applied": filters.model_dump(),
        "example_result": ["item1", "item2"]
    }