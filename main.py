#!/usr/bin/env python3
"""
监控机器人主启动文件
"""

import asyncio
import signal
import sys
from typing import Optional

from src.core.monitor_manager import MonitorManager
from src.utils.logger import logger
from src.config.settings import settings

# 确保插件被注册
import src.plugins

# 全局管理器实例
manager: Optional[MonitorManager] = None
running = True

def signal_handler(signum, frame):
    """信号处理器"""
    global running
    logger.info(f"收到信号 {signum}，准备关闭...")
    running = False

async def main():
    """主函数"""
    global manager, running
    
    logger.info("🚀 启动监控机器人...")
    logger.info(f"当前配置: {settings.get_enabled_monitors()}")
    
    # 创建监控管理器
    manager = MonitorManager()
    
    try:
        # 使用生命周期管理器
        async with manager.lifecycle() as mgr:
            logger.info("✅ 监控系统已启动")
            
            # 显示启动状态
            stats = mgr.get_all_stats()
            for name, stat in stats.items():
                logger.info(f"插件 {name}: {stat.status.value}")
            
            # 主循环 - 等待信号或手动停止
            while running:
                try:
                    await asyncio.sleep(5)
                    
                    # 可选：定期显示健康状态
                    if settings.debug:
                        health = await mgr.health_check()
                        logger.debug(f"健康评分: {health['health_score']:.2f}")
                    
                except KeyboardInterrupt:
                    logger.info("收到中断信号")
                    break
                except Exception as e:
                    logger.error(f"主循环异常: {e}")
                    break
            
        logger.info("🛑 监控系统已停止")
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"启动异常: {e}")
        sys.exit(1)