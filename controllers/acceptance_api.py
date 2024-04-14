import uuid
from datetime import datetime
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func
from database import get_async_session
from models import acceptance, task
from schemas import AcceptanceRequest
from uuid import UUID


router = APIRouter(
    tags=["AcceptanceController"]
)


@router.get("/getAcceptanceInfo")
async def get_acceptance_info(id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):

    query = select(acceptance.c.id).where(acceptance.c.id == id)
    result = await session.execute(query)
    if result.scalar() is None:
        raise HTTPException(status_code=404, detail="ID not found")

    query_tasks = select(task).where(task.c.process_id == id)
    tasks_result = await session.execute(query_tasks)
    tasks_info = tasks_result.mappings().all()

    query_acceptance = select(acceptance.c.id, acceptance.c.created_at).where(acceptance.c.id == id)
    acceptance_result = await session.execute(query_acceptance)
    acceptance_info = acceptance_result.mappings().all()

    query_sku = select(func.count(func.distinct(task.c.id)).label('sku_count'), task.c.sku_id,
                       task.c.stock).where(task.c.process_id == id).group_by(task.c.sku_id, task.c.stock)
    sku_result = await session.execute(query_sku)
    sku_info = sku_result.mappings().all()

    response_data = {
        "id": str(acceptance_info[0].id),
        "created_at": str(acceptance_info[0].created_at),
        "accepted": [{"sku_id": str(sku_info.sku_id), "stock": str(sku_info.stock),
                      "count": str(sku_info.sku_count)} for sku_info in sku_info],
        "task_ids": [{"id": str(task_info.id), "status": task_info.status} for task_info in tasks_info]
    }

    return response_data


@router.post("/createAcceptance")
async def create_acceptance(items_to_accept: AcceptanceRequest, session: AsyncSession = Depends(get_async_session)):

    new_acceptance = uuid.uuid4()

    for i in range(len(items_to_accept.items_to_accept)):
        for c in range(items_to_accept.items_to_accept[i].count):
            stmt_insert = insert(task).values([
                uuid.uuid4(),
                "in_work", datetime.utcnow(),
                "placing", new_acceptance,
                items_to_accept.items_to_accept[i].sku_id,
                items_to_accept.items_to_accept[i].stock,
                uuid.uuid4(),
                None])
            await session.execute(stmt_insert)

    stmt = insert(acceptance).values([new_acceptance, datetime.utcnow()])
    await session.execute(stmt)
    await session.commit()
    return {"id": new_acceptance}
