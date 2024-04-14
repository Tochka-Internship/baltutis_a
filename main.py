from fastapi import FastAPI
from controllers.posting_api import router as posting_controller
from controllers.task_api import router as taskapi
from controllers.discount_api import router as discountapi
from controllers.sku_api import router as sku_controller
from controllers.acceptance_api import router as acceptance_controller
from database import get_async_session
from models import acceptance, task, stock_table, discount, sku, posting
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


app = FastAPI(
    title="Tochka.Univermag 2.0"
)

app.include_router(posting_controller)
app.include_router(taskapi)
app.include_router(discountapi)
app.include_router(sku_controller)
app.include_router(acceptance_controller)

