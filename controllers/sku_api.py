import uuid
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy import select, label, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from models import sku, stock_table, discount
from schemas import NewPriceRequest, MarkDownRequest, RequestId, RequestHidden

router = APIRouter(
    tags=["SkuController"]
)


@router.get("/getItemInfo")
async def get_item_info(id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):

    query = select(stock_table.c.id, stock_table.c.sku_id, stock_table.c.stock, stock_table.c.reserved_state) \
        .where(stock_table.c.id == id)
    result = await session.execute(query)
    result_info = result.mappings().all()

    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found")

    return result_info[0]


@router.get("/getSkuInfo")
async def get_sku_info(id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):

    query = select(sku.c.id, sku.c.created_at, func.sum(stock_table.c.actual_price).label('actual_price'),
                   sku.c.base_price, func.count(stock_table.c.id).label('count'), sku.c.is_hidden)\
        .join(stock_table, stock_table.c.sku_id == sku.c.id).where(sku.c.id == id)\
        .group_by(sku.c.id)
    result = await session.execute(query)
    result_info = result.mappings().all()

    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found")

    return result_info[0]


@router.get("/getItemInfoBySkuId")
async def get_item_info_by_sku_id(id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):

    query = select(label('item_id', stock_table.c.id), stock_table.c.stock, stock_table.c.reserved_state) \
        .where(stock_table.c.sku_id == id)
    result = await session.execute(query)
    result_info = result.mappings().all()

    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found")

    return {"items": result_info}


@router.post("/markdownItem")
async def mark_down_item(request: MarkDownRequest, session: AsyncSession = Depends(get_async_session)):

    query = select(stock_table, sku).join(sku, sku.c.id == stock_table.c.sku_id).where(stock_table.c.id == request.id)
    result = await session.execute(query)
    result_info = result.mappings().all()

    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found")

    update_price = stock_table.update().values(markdown=request.percentage).where(stock_table.c.id == request.id)
    await session.execute(update_price)
    await session.commit()

    query_check = select(stock_table, sku.c.base_price, discount.c.percentage) \
        .join(sku, sku.c.id == stock_table.c.sku_id) \
        .join(discount, discount.c.id == sku.c.active_discount, isouter=True)\
        .where(stock_table.c.id == request.id)
    result = await session.execute(query_check)
    item_list = result.mappings().all()

    if item_list[0].percentage is None:
        discount_check: float = 0
    else:
        discount_check = item_list[0].percentage
    new_actual_price = round(item_list[0].base_price * min((1 - discount_check), (1 - item_list[0].markdown)), 2)
    update_discount_info = stock_table.update().values(actual_price=new_actual_price, stock="defect") \
        .where(stock_table.c.id == item_list[0].id)
    await session.execute(update_discount_info)
    await session.commit()

    return {"status": "Success set markdown"}


@router.post("/setSkuPrice")
async def set_sku_price(request: NewPriceRequest, session: AsyncSession = Depends(get_async_session)):

    query = select(sku.c.id).where(sku.c.id == request.sku_id)
    result = await session.execute(query)

    if result.scalar() is None:
        raise HTTPException(status_code=404, detail="ID not found")

    update_base_price = sku.update().values(base_price=request.base_price).where(sku.c.id == request.sku_id)
    await session.execute(update_base_price)
    await session.commit()

    query_check = select(stock_table, sku.c.base_price, discount.c.percentage) \
        .join(sku, sku.c.id == stock_table.c.sku_id) \
        .join(discount, discount.c.id == sku.c.active_discount, isouter=True) \
        .where(sku.c.id == request.sku_id)
    result = await session.execute(query_check)
    item_list = result.mappings().all()

    if item_list[0].percentage is None:
        discount_check: float = 0
    else:
        discount_check = item_list[0].percentage
    for c in range(len(item_list)):
        new_actual_price = round(
            item_list[c].base_price * min((1 - discount_check), (1 - item_list[c].markdown)), 2)
        update_discount_info = stock_table.update().values(actual_price=new_actual_price) \
            .where(stock_table.c.id == item_list[c].id)
        await session.execute(update_discount_info)
    await session.commit()

    return {"status": "Success set sku price"}


@router.post("/toggleIsHidden")
async def toggle_is_hidden(id: RequestHidden, session: AsyncSession = Depends(get_async_session)):

    query = select(sku.c.id).where(sku.c.id == id.id, not sku.c.is_hidden == id.is_hidden)
    result = await session.execute(query)

    if result.scalar() is None:
        raise HTTPException(status_code=404, detail="ID not found or already hidden")
    update_hidden = sku.update().values(is_hidden=id.is_hidden).where(sku.c.id == id.id)
    await session.execute(update_hidden)
    await session.commit()

    return {"status": "Success hidden"}


@router.post("/moveToNotFound")
async def move_to_not_found(id: RequestId, session: AsyncSession = Depends(get_async_session)):

    query = select(stock_table.c.id).where(stock_table.c.id == id.id, stock_table.c.stock != "NotFound")
    result = await session.execute(query)

    if result.scalar() is None:
        raise HTTPException(status_code=404, detail="ID not found or already move to NotFound")

    update_price = stock_table.update().values(stock="NotFound").where(stock_table.c.id == id.id)
    await session.execute(update_price)
    await session.commit()

    return {"status": "Success move to NotFound"}
