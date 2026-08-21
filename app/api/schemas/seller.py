from pydantic import BaseModel, EmailStr


class BaseSeller(BaseModel):
    name: str
    email: EmailStr
    zip_code: int

class SellerRead(BaseSeller):
    pass

class SellerCreate(BaseSeller):
    password: str