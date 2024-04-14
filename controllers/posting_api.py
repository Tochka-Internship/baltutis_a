import uuid
from datetime import datetime
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func
from database import get_async_session
from models import task, sku, stock_table, posting
from schemas import PostingRequest, RequestId

router = APIRouter(
    tags=["PostingController"]
)


@router.get("/getPosting")
async def get_posting(id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):

    query_posting = select(posting).where(posting.c.id == id)
    result = await session.execute(query_posting)
    posting_list = result.mappings().all()
    if len(posting_list) == 0:
        raise HTTPException(status_code=404, detail="ID not found")

    query_cost = select(func.sum(stock_table.c.actual_price).label('cost')) \
        .join(task, task.c.item_id == stock_table.c.id) \
        .where(task.c.posting_id == id,
               stock_table.c.stock != "NotFound",
               stock_table.c.reserved_state.is_(True))
    result = await session.execute(query_cost)
    cost_list = result.mappings().all()

    query_stock = select(task).where(task.c.posting_id == id)
    result = await session.execute(query_stock)
    stock_list = result.mappings().all()

    ordered_goods = {}

    for item in stock_list:
        if item.sku_id not in ordered_goods:
            ordered_goods[item.sku_id] = {"sku": item.sku_id, "from_valid_ids": [], "from_defect_ids": []}
        if item.stock == "valid":
            ordered_goods[item.sku_id]["from_valid_ids"].append(item.item_id)
        elif item.stock == "defect":
            ordered_goods[item.sku_id]["from_defect_ids"].append(item.item_id)
    ordered_goods_list = list(ordered_goods.values())

    query_notfound = select(stock_table.c.id) \
        .join(task, task.c.item_id == stock_table.c.id) \
        .where(task.c.posting_id == id, stock_table.c.stock == "NotFound")
    result = await session.execute(query_notfound)
    notfound = result.mappings().all()

    query_task = select(task.c.id, task.c.type, task.c.status).where(task.c.posting_id == id)
    result = await session.execute(query_task)
    task_list = result.mappings().all()

    response_data = {
        "id": str(posting_list[0].id),
        "status": str(posting_list[0].status),
        "created_at": str(posting_list[0].created_at),
        "cost": str(cost_list[0].cost),
        "ordered_goods": list(ordered_goods_list),
        "not_found": list(notfound),
        "task_ids": list(task_list)
    }

    return response_data


@router.post("/createPosting")
async def create_posting(order_request: PostingRequest, session: AsyncSession = Depends(get_async_session)):

    sku_ids = [item.sku for item in order_request.ordered_goods]
    query_check = select(sku.c.id).where(sku.c.id.in_(sku_ids), sku.c.is_hidden.is_(False))
    result = await session.execute(query_check)
    sku_ids_list = result.mappings().all()

    if len(sku_ids_list) != len(sku_ids):
        raise HTTPException(status_code=404, detail="Some sku not found or sku is hidden")

    for i in range(len(sku_ids)):
        if not order_request.ordered_goods[i].from_valid_ids is None:
            valid_list = order_request.ordered_goods[i].from_valid_ids
            query_check_valid = select(stock_table.c.id).where(stock_table.c.id.in_(valid_list),
                                                               stock_table.c.stock == "valid",
                                                               stock_table.c.reserved_state.is_(False))
            result = await session.execute(query_check_valid)
            valid_item_check = result.mappings().all()
            if len(valid_item_check) != len(valid_list):
                raise HTTPException(status_code=404, detail="Some item not found or reserved or placed in another stock")
        if not order_request.ordered_goods[i].from_defect_ids is None:
            defect_list = order_request.ordered_goods[i].from_defect_ids
            query_check_defect = select(stock_table.c.id).where(stock_table.c.id.in_(defect_list),
                                                                stock_table.c.stock == "defect",
                                                                stock_table.c.reserved_state.is_(False))
            result = await session.execute(query_check_defect)
            defect_item_check = result.mappings().all()
            if len(defect_item_check) != len(defect_list):
                raise HTTPException(status_code=404, detail="Some item not found or reserved or placed in another stock")

    new_posting_id = uuid.uuid4()

    for i in range(len(sku_ids)):
        if not order_request.ordered_goods[i].from_valid_ids is None:
            valid_list = order_request.ordered_goods[i].from_valid_ids
            for c in range(len(valid_list)):
                stmt_valid_list = insert(task).values([
                    uuid.uuid4(),
                    "in_work", datetime.utcnow(),
                    "picking", None,
                    sku_ids[i],
                    "valid",
                    valid_list[c],
                    new_posting_id])
                await session.execute(stmt_valid_list)
                update_reserved_valid = stock_table.update().values(reserved_state=True)\
                    .where(stock_table.c.id == valid_list[c])
                await session.execute(update_reserved_valid)
        if not order_request.ordered_goods[i].from_defect_ids is None:
            defect_list = order_request.ordered_goods[i].from_defect_ids
            for c in range(len(defect_list)):
                stmt_defect_list = insert(task).values([
                    uuid.uuid4(),
                    "in_work", datetime.utcnow(),
                    "picking", None,
                    sku_ids[i],
                    "defect",
                    defect_list[c],
                    new_posting_id])
                await session.execute(stmt_defect_list)
                update_reserved_defect = stock_table.update().values(reserved_state=True) \
                    .where(stock_table.c.id == defect_list[c])
                await session.execute(update_reserved_defect)

    stmt_posting = insert(posting).values([new_posting_id, "in_item_pick", datetime.utcnow()])
    await session.execute(stmt_posting)
    await session.commit()

    return {"id": new_posting_id}


@router.post("/cancelPosting")
async def cancel_posting(id: RequestId, session: AsyncSession = Depends(get_async_session)):

    query_check = select(posting).where(posting.c.id == id.id, posting.c.status == "in_item_pick")
    result = await session.execute(query_check)
    result_info = result.mappings().all()

    if len(result_info) == 0:
        raise HTTPException(status_code=404, detail="ID not found or already canceled or sent")

    update_stmt = task.update().values(status="canceled").where(task.c.posting_id == id.id)
    await session.execute(update_stmt)
    await session.commit()

    query_task = select(task).where(task.c.posting_id == id.id)
    result = await session.execute(query_task)
    result_task_info = result.mappings().all()

    for c in range(len(result_task_info)):
        stmt_new_task = insert(task).values([
            uuid.uuid4(),
            "in_work", datetime.utcnow(),
            "placing", None,
            result_task_info[c].sku_id,
            result_task_info[c].stock,
            result_task_info[c].item_id,
            id.id])
        await session.execute(stmt_new_task)

    update_posting = posting.update().values(status="canceled").where(posting.c.id == id.id)
    await session.execute(update_posting)
    await session.commit()

    return {"id": id.id}

