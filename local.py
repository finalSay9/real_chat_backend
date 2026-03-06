from typing import List

def normalize_id(user_id: int | str) -> str:
    if isinstance(user_id, int):
        return f'user-{100_000 + user_id}'
    
    else:
        return user_id

print(normalize_id(9))