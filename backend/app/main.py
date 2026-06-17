from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
import app.database as db
from app.api.routes import api_router
from app.services.sync import sync_catalog
from sqlmodel import Session
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os

# Thiết lập ghi log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo scheduler chạy nền để đồng bộ dữ liệu
scheduler = BackgroundScheduler()

def run_sync_job():
    """
    Công việc đồng bộ chạy định kỳ
    """
    logger.info("Bắt đầu chạy job đồng bộ dữ liệu BurgerPrints định kỳ...")
    with Session(db.engine) as session:
        import asyncio
        # Chạy đồng bộ catalog đồng bộ đồng thời
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(sync_catalog(session))
        loop.close()
        if success:
            logger.info("Job đồng bộ định kỳ hoàn thành thành công!")
        else:
            logger.error("Job đồng bộ định kỳ thất bại!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("Ứng dụng FastAPI đang khởi động...")

    # 1. Khởi tạo CSDL
    logger.info("Khởi tạo các bảng cơ sở dữ liệu SQLModel...")
    init_db()
    logger.info("Đã khởi tạo các bảng thành công.")

    # 2. Thực hiện đồng bộ dữ liệu BurgerPrints lần đầu tiên (nếu không ở chế độ TESTING)
    if not os.getenv("TESTING"):
        import asyncio
        async def run_initial_sync():
            logger.info("Thực hiện đồng bộ dữ liệu catalog lần đầu tiên dưới nền...")
            with Session(db.engine) as session:
                try:
                    # Kiểm tra xem Database đã có dữ liệu sản phẩm chưa
                    from app.models.catalog import Product
                    from sqlmodel import select
                    existing_product = session.exec(select(Product)).first()
                    if existing_product:
                        logger.info("Dữ liệu catalog đã tồn tại trong Database. Bỏ qua đồng bộ ban đầu khi startup để tăng tốc khởi động.")
                        return

                    logger.info("Database rỗng. Bắt đầu tải dữ liệu từ BurgerPrints API...")
                    await sync_catalog(session)
                    logger.info("Đồng bộ dữ liệu ban đầu hoàn tất.")
                except Exception as e:
                    logger.error(f"Đồng bộ dữ liệu ban đầu gặp lỗi: {str(e)}")
        asyncio.create_task(run_initial_sync())
    else:
        logger.info("Chế độ TESTING được bật. Bỏ qua đồng bộ dữ liệu catalog ban đầu.")

    # 3. Cấu hình và chạy scheduler đồng bộ dữ liệu định kỳ mỗi 6 giờ
    scheduler.add_job(run_sync_job, 'interval', hours=6, id='sync_burgerprints_catalog')
    scheduler.start()
    logger.info("Đã khởi chạy Scheduler đồng bộ định kỳ.")

    yield

    # --- SHUTDOWN ---
    logger.info("Ứng dụng FastAPI đang tắt...")
    scheduler.shutdown()
    logger.info("Đã dừng Scheduler.")

app = FastAPI(
    title="BurgerPrints POD Catalog Assistant API",
    description="Backend API hỗ trợ AI Agent tư vấn catalog, tính toán landed cost và tạo đơn hàng nháp.",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký routes
app.include_router(api_router)
