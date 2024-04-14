from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Table, Column, String, MetaData, Boolean, Float, DateTime, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID
from uuid import UUID


metadata = MetaData()

stock_table: Table = Table(
    "stock_table",
    metadata,
    Column('id', SQLAlchemyUUID, primary_key=True),
    Column('sku_id', SQLAlchemyUUID, nullable=False),
    Column('stock', String, nullable=False),
    Column('created_at', DateTime(timezone=False), nullable=False),
    Column('reserved_state', Boolean, nullable=False),
    Column('actual_price', Float),
    Column('is_hidden', Boolean),
    Column('markdown', Float),
)


class StockTable(BaseModel):
    id: UUID
    sku_id: UUID
    stock: str
    created_at: datetime
    reserved_state: bool
    actual_price: float
    is_hidden: bool
    markdown: float

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True


sku: Table = Table(
    "sku",
    metadata,
    Column('id', SQLAlchemyUUID(as_uuid=True), primary_key=True),
    Column('base_price', Float),
    Column('created_at', DateTime(timezone=False)),
    Column('active_discount', SQLAlchemyUUID(as_uuid=True), nullable=True),
    Column('is_hidden', Boolean),
)


class Sku(BaseModel):
    id: UUID
    base_price: float
    created_at: datetime
    active_discount: UUID
    is_hidden: bool

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True


task = Table(
    "task",
    metadata,
    Column('id', SQLAlchemyUUID(as_uuid=True), primary_key=True),
    Column('status', String),
    Column('created_at', DateTime(timezone=False)),
    Column('type', String, nullable=False),
    Column('process_id', SQLAlchemyUUID(as_uuid=True), nullable=True),
    Column('sku_id', SQLAlchemyUUID(as_uuid=True)),
    Column('stock', String, nullable=False),
    Column('item_id', SQLAlchemyUUID(as_uuid=True)),
    Column('posting_id', SQLAlchemyUUID(as_uuid=True), nullable=True),

)


class Task(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    type: str
    process_id: UUID
    sku_id: UUID
    stock: str
    item_id: UUID
    posting_id: UUID

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True


discount = Table(
    "discount",
    metadata,
    Column('id', SQLAlchemyUUID(as_uuid=True), primary_key=True),
    Column('status', String),
    Column('created_at', DateTime(timezone=False)),
    Column('percentage', Float),
)


class Discount(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    percentage: float

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True


acceptance = Table(
    "acceptance",
    metadata,
    Column('id', SQLAlchemyUUID(as_uuid=True), primary_key=True),
    Column('created_at', DateTime(timezone=False)),
)


class Acceptance(BaseModel):
    id: UUID
    created_at: datetime

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True


posting = Table(
    "posting",
    metadata,
    Column('id', SQLAlchemyUUID(as_uuid=True), primary_key=True),
    Column('status', String),
    Column('created_at', DateTime(timezone=False)),
)


class Posting(BaseModel):
    id: UUID
    created_at: datetime
    status: str

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True
