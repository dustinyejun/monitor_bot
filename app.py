#!/usr/bin/env python3
"""
FastAPI Web 服务启动文件
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.monitor_manager import MonitorManager
from src.api.notification_routes import router as notification_router
from src.config.settings import settings
from src.utils.logger import logger

# 确保插件被注册
import src.plugins

# 全局管理器实例
manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global manager
    
    logger.info("🚀 启动 FastAPI 应用和监控系统...")
    
    # 启动监控系统
    manager = MonitorManager()
    await manager.load_plugins()
    await manager.start_all()
    
    logger.info("✅ 监控系统已启动")
    
    yield
    
    # 关闭监控系统
    logger.info("🛑 关闭监控系统...")
    if manager:
        await manager.stop_all()
    logger.info("✅ 应用已关闭")

# 创建 FastAPI 应用
app = FastAPI(
    title="Monitor Bot API",
    description="Twitter 和 Solana 监控机器人 API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(notification_router, prefix="/api")

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Monitor Bot API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """健康检查"""
    if manager:
        health = await manager.health_check()
        return {
            "status": "healthy" if health["health_score"] > 0.7 else "unhealthy",
            "details": health
        }
    return {"status": "starting"}

@app.get("/status")
async def get_status():
    """获取系统状态"""
    if manager:
        stats = manager.get_all_stats()
        return {
            "enabled_monitors": settings.get_enabled_monitors(),
            "plugins": [
                {
                    "name": name,
                    "status": stat.status.value,
                    "total_checks": stat.total_checks,
                    "success_rate": stat.success_rate
                }
                for name, stat in stats.items()
            ]
        }
    return {"status": "not_started"}

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"启动 FastAPI 服务 on {settings.host}:{settings.port}")
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )