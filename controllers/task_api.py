import uuid
from datetime import datetime
import random
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from models import task, stock_table, sku, posting
from schemas import RequestTask

router = APIRouter(
    tags=["TaskApi"]
)


@router.get("/getTaskInfo")
async def get_task_info(id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):
    query = select(task).where(task.c.id == id)
    result = await session.execute(query)
    result_info = result.mappings().all()
    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found")
    response_data = {
        "id": str(result_info[0].id),
        "status": str(result_info[0].status),
        "created_at": str(result_info[0].created_at),
        "type": str(result_info[0].type),
        "task_target": {"stock": str(result_info[0].stock), "id": str(result_info[0].item_id)},
        "posting_id": str(result_info[0].posting_id)
    }
    return response_data


@router.post("/finishTask")
async def finish_task(id: RequestTask, session: AsyncSession = Depends(get_async_session)):
    query = select(task).where(task.c.id == id.id, task.c.status == "in_work")
    result = await session.execute(query)
    result_info = result.mappings().all()
    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="id not found or already completed or canceled")
    query_item_id = select(stock_table).where(stock_table.c.id == result_info[0].item_id)
    result = await session.execute(query_item_id)
    result_item_info = result.mappings().all()
    check_new_task_create: bool = False
    if id.status == "completed" and result_info[0].type == "placing":
        if len(result_item_info[0]) == 0:
            query_sku = select(sku).where(sku.c.id == result_info[0].sku_id)
            result_sku = await session.execute(query_sku)
            result_sku_check = result_sku.mappings().all()
            if len(result_sku_check) == 0:
                price_check: float = 0.00
                smtm_sku = insert(sku).values([
                    result_info[0].sku_id,
                    price_check,
                    datetime.utcnow(),
                    None,
                    False])
                await session.execute(smtm_sku)
            else:
                price_check: float = result_sku_check[0].base_price
            stmt_stock = insert(stock_table).values([
                result_info[0].item_id,
                result_info[0].sku_id,
                result_info[0].stock,
                datetime.utcnow(),
                False,
                price_check,
                False,
                0.00])
            await session.execute(stmt_stock)
            update_stmt = task.update().values(status="completed").where(task.c.id == id)
            await session.execute(update_stmt)
        else:
            update_reserved = stock_table.update().values(reserved_state=False)\
                .where(stock_table.c.id == result_item_info[0].id)
            await session.execute(update_reserved)
        update_stmt = task.update().values(status="completed").where(task.c.id == id)
        await session.execute(update_stmt)
    if id.status == "canceled" and result_info[0].type == "placing":
        update_stmt = task.update().values(status="canceled").where(task.c.id == id.id)
        await session.execute(update_stmt)
    if id.status == "canceled" and result_info[0].type == "picking":
        update_reserved = stock_table.update().values(reserved_state=False)\
            .where(stock_table.c.id == result_item_info[0].id)
        await session.execute(update_reserved)
        update_stmt = task.update().values(status="canceled").where(task.c.id == id.id)
        await session.execute(update_stmt)
    if id.status == "completed" and result_info[0].type == "picking":
        if random.random() < 0.1:
            update_price = stock_table.update()\
                .values(stock="NotFound").where(stock_table.c.id == result_item_info[0].id)
            await session.execute(update_price)
            await session.commit()
        query_notfound_check = select(stock_table)\
            .where(stock_table.c.id == result_info[0].item_id, stock_table.c.stock != "NotFound")
        result = await session.execute(query_notfound_check)
        result_notfound_check = result.mappings().all()
        if len(result_notfound_check) == 0:
            query_new_found_check = select(stock_table) \
                .where(stock_table.c.sku_id == result_info[0].sku_id,
                       stock_table.c.stock == result_info[0].stock,
                       stock_table.c.reserved_state.is_(False))\
                .limit(1)
            result = await session.execute(query_new_found_check)
            result_new_found_check = result.mappings().all()
            if len(result_new_found_check) == 0:
                stmt_new_task = insert(task).values([
                    uuid.uuid4(),
                    "in_work", datetime.utcnow(),
                    "picking", None,
                    result_new_found_check[0].sku_id,
                    result_new_found_check[0].stock,
                    result_new_found_check[0].id,
                    result_info[0].posting_id])
                await session.execute(stmt_new_task)
            check_new_task_create = True
    if check_new_task_create is True:
        status_result = "canceled"
    else:
        status_result = id.status
    update_stmt = task.update().values(status=status_result).where(task.c.id == id.id)
    await session.execute(update_stmt)
    await session.commit()
    query_posting_check = select(task).where(task.c.posting_id == result_info[0].posting_id,
                                             task.c.status == "in_work")
    result = await session.execute(query_posting_check)
    result_posting_check = result.mappings().all()
    query_posting_finish = select(task).where(task.c.posting_id == result_info[0].posting_id,
                                              task.c.status == "completed")
    result = await session.execute(query_posting_finish)
    result_posting_finish = result.mappings().all()
    if len(result_posting_check) == 0 and len(result_posting_finish) != 0:
        update_stmt = posting.update().values(status="sent").where(posting.c.id == result_info[0].posting_id)
        await session.execute(update_stmt)
        await session.commit()
    if len(result_posting_check) == 0 and len(result_posting_finish) == 0:
        update_stmt = posting.update().values(status="canceled").where(posting.c.id == result_info[0].posting_id)
        await session.execute(update_stmt)
        await session.commit()
    return {"id": id.id, "status": status_result}















