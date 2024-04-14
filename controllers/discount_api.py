import uuid
from datetime import datetime
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from models import sku, stock_table, discount
from schemas import DiscountRequest, RequestId

router = APIRouter(
    tags=["DiscountApi"]
)


@router.get("/getDiscount")
async def get_discount(id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):

    query = select(discount).where(discount.c.id == id)
    result = await session.execute(query)
    result_info = result.mappings().all()

    query_sku = select(sku.c.id).where(sku.c.active_discount == id)
    result_sku = await session.execute(query_sku)
    result_sku_info = result_sku.mappings().all()

    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found")
    return result_info, {"sku_ids": list(result_sku_info)}


@router.post("/createDiscount")
async def create_discount(discount_request: DiscountRequest, session: AsyncSession = Depends(get_async_session)):

    query_check = select(sku).where(sku.c.id.in_(discount_request.sku_ids), sku.c.active_discount.is_(None))
    result = await session.execute(query_check)
    sku_ids_list = result.mappings().all()

    if len(sku_ids_list) != len(discount_request.sku_ids):
        raise HTTPException(status_code=404, detail="Some sku_id not found or already have active discount")

    new_id_discount = uuid.uuid4()

    update_sku = sku.update().values(active_discount=new_id_discount) \
        .where(sku.c.id.in_(discount_request.sku_ids), sku.c.active_discount.is_(None))
    await session.execute(update_sku)

    stmt = insert(discount).values([new_id_discount, "active", datetime.utcnow(), discount_request.percentage])
    await session.execute(stmt)
    await session.commit()

    query_check = select(stock_table, sku.c.base_price, discount.c.percentage)\
        .join(sku, sku.c.id == stock_table.c.sku_id) \
        .join(discount, discount.c.id == sku.c.active_discount) \
        .where(sku.c.id.in_(discount_request.sku_ids))
    result = await session.execute(query_check)
    item_list = result.mappings().all()

    for c in range(len(item_list)):
        new_actual_price = round(item_list[c].base_price * min(1 - item_list[c].percentage, 1 - item_list[c].markdown), 2)
        update_price = stock_table.update().values(actual_price=new_actual_price) \
            .where(stock_table.c.id == item_list[c].id)
        await session.execute(update_price)

    return {"id": str(new_id_discount)}


@router.post("/cancelDiscount")
async def cancel_discount(id: RequestId, session: AsyncSession = Depends(get_async_session)):

    query_check = select(discount, sku)\
        .join(sku, sku.c.active_discount == discount.c.id)\
        .where(discount.c.id == id.id, discount.c.status == "active")
    result = await session.execute(query_check)
    result_info = result.mappings().all()

    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found or already finished")

    update_discount = discount.update().values(status="finished") \
        .where(discount.c.id == id.id)
    await session.execute(update_discount)

    query_check = select(stock_table, sku.c.base_price, discount.c.percentage) \
        .join(sku, sku.c.id == stock_table.c.sku_id) \
        .join(discount, discount.c.id == sku.c.active_discount)\
        .where(discount.c.id == id.id)
    result = await session.execute(query_check)
    item_list = result.mappings().all()

    for c in range(len(item_list)):
        new_actual_price = round(item_list[c].base_price * (1 - item_list[c].markdown), 2)
        update_price = stock_table.update().values(actual_price=new_actual_price) \
            .where(stock_table.c.id == item_list[c].id)
        await session.execute(update_price)

    update_finish_discount_info = sku.update().values(active_discount=None) \
        .where(sku.c.active_discount == id.id)
    await session.execute(update_finish_discount_info)
    await session.commit()

    return {"Discount finished"}
