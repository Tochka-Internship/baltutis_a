from typing import List
from pydantic import BaseModel, validator
from uuid import UUID


class SkuPriceChange(BaseModel):
    new_price: float

    @validator('new_price')
    def check_price_non_negative(cls, value):
        if value < 0:
            raise ValueError('Price must be non-negative')
        return value

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class ItemToAccept(BaseModel):
    sku_id: UUID
    stock: str = 'valid'
    count: int = 1

    @validator('stock')
    def check_stock(cls, value):
        if not value == 'valid' and not value == 'defect':
            raise ValueError('Stock must be "valid" or "defect"')
        return value

    @validator('count')
    def check_count_non_negative(cls, value):
        if value <= 0:
            raise ValueError('Count must be positive')
        return value

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class AcceptanceRequest(BaseModel):
    items_to_accept: List[ItemToAccept]

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class SkuidRequest(BaseModel):
    sku_ids: UUID

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class DiscountRequest(BaseModel):
    sku_ids: List[UUID]
    percentage: float = 0.10

    @validator('percentage')
    def check_percentage(cls, value):
        if not 0 < value < 1:
            raise ValueError('Percentage must be positive and must be < 1')
        return value

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class NewPriceRequest(BaseModel):
    sku_id: UUID
    base_price: float = 0.10

    @validator('base_price')
    def check_percentage(cls, value):
        if value < 0:
            raise ValueError('base_price must be not negative')
        return value

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class MarkDownRequest(BaseModel):
    id: UUID
    percentage: float = 0.10

    @validator('percentage')
    def check_percentage(cls, value):
        if not 0 < value < 1:
            raise ValueError('Percentage must be positive and must be < 1')
        return value

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class ItemRequest(BaseModel):
    sku: UUID
    from_valid_ids: List[UUID]
    from_defect_ids: List[UUID]

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class PostingRequest(BaseModel):
    ordered_goods: List[ItemRequest]

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


class RequestId(BaseModel):
    id: UUID


class RequestHidden(BaseModel):
    id: UUID
    is_hidden: bool = True


class RequestTask(BaseModel):
    id: UUID
    status: str = "completed"

    @validator('status')
    def check_percentage(cls, value):
        if not (value == "canceled" or value == "completed"):
            raise ValueError('Status must be "canceled" or "completed"')
        return value

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
        table_valued = True


