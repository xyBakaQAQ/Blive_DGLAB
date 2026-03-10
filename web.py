# -*- coding: utf-8 -*-
"""Web UI 模块"""
import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime

import yaml
from aiohttp import web

logger = logging.getLogger(__name__)

class WebUI:
    """Web UI 服务器"""
    
    def __init__(self, config: dict, dglab_controller, host: str = "0.0.0.0", port: int = 8080):
        self.config = config
        self.dglab = dglab_controller
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # 日志缓冲区（最多保存 200 条）
        self.log_buffer = deque(maxlen=200)
        self.danmaku_log_buffer = deque(maxlen=100)  # 弹幕日志
        self.dglab_log_buffer = deque(maxlen=100)    # 郊狼日志
        self.obs_history = deque(maxlen=50)  # OBS 历史记录（最近50条）
        self.websockets = set()
        self.obs_websockets = set()  # OBS 专用 WebSocket 连接
        
        # 设置路由
        self._setup_routes()
        
        # 添加日志处理器
        self._setup_logging()
    
    def _setup_routes(self):
        """设置路由"""
        # 静态文件
        html_dir = os.path.join(os.path.dirname(__file__), "html")
        self.app.router.add_static('/static', os.path.join(html_dir, 'static'))
        
        # 页面路由
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/config.html', self.handle_config_page)
        self.app.router.add_get('/obs.html', self.handle_obs_page)
        self.app.router.add_get('/obs-source.html', self.handle_obs_source_page)
        
        # API 路由
        self.app.router.add_get('/api/config', self.handle_get_config)
        self.app.router.add_get('/api/config/full', self.handle_get_full_config)
        self.app.router.add_post('/api/config/save', self.handle_save_config)
        self.app.router.add_get('/api/logs', self.handle_get_logs)
        self.app.router.add_get('/api/obs/history', self.handle_get_obs_history)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.router.add_get('/ws/obs', self.handle_obs_websocket)
    
    def _setup_logging(self):
        """设置日志处理器以捕获日志"""
        class WebLogHandler(logging.Handler):
            def __init__(self, webui):
                super().__init__()
                self.webui = webui
            
            def emit(self, record):
                try:
                    message = self.format(record)
                    log_entry = {
                        'time': datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                        'level': record.levelname,
                        'message': message
                    }
                    
                    # 添加到总日志
                    self.webui.log_buffer.append(log_entry)
                    
                    # 检查是否有运行中的事件循环
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # 没有运行的事件循环，跳过广播
                        return
                    
                    # 根据消息内容分类
                    if any(keyword in message for keyword in ['[弹幕', '[礼物', '[SC', '[上舰', '[进入', '[关注', '[分享']):
                        self.webui.danmaku_log_buffer.append(log_entry)
                        asyncio.create_task(self.webui.broadcast_log(log_entry, 'danmaku'))
                    elif '[DGLab]' in message or '[手动控制]' in message:
                        self.webui.dglab_log_buffer.append(log_entry)
                        asyncio.create_task(self.webui.broadcast_log(log_entry, 'dglab'))
                    else:
                        # 其他日志广播到全部
                        asyncio.create_task(self.webui.broadcast_log(log_entry, 'all'))
                except Exception:
                    # 忽略日志处理中的错误，避免影响程序退出
                    pass
        
        handler = WebLogHandler(self)
        handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(handler)
        self.log_handler = handler
    
    async def broadcast_log(self, log_entry, log_type='all'):
        """广播日志到所有 WebSocket 连接"""
        if self.websockets:
            message = json.dumps({'type': 'log', 'log_type': log_type, 'data': log_entry})
            await asyncio.gather(
                *[ws.send_str(message) for ws in self.websockets],
                return_exceptions=True
            )
    
    async def handle_index(self, request):
        """首页"""
        html_path = os.path.join(os.path.dirname(__file__), "html", "index.html")
        with open(html_path, 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    
    async def handle_config_page(self, request):
        """配置页面"""
        html_path = os.path.join(os.path.dirname(__file__), "html", "config.html")
        with open(html_path, 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    
    async def handle_obs_page(self, request):
        """OBS 页面"""
        html_path = os.path.join(os.path.dirname(__file__), "html", "obs.html")
        with open(html_path, 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    
    async def handle_obs_source_page(self, request):
        """OBS 浏览器源页面"""
        html_path = os.path.join(os.path.dirname(__file__), "html", "obs-source.html")
        with open(html_path, 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    
    async def handle_get_config(self, request):
        """获取基本配置"""
        safe_config = {
            'bilibili': {
                'room_id': self.config['bilibili']['room_id']
            },
            'dglab': {
                'enabled': self.config['dglab'].get('enabled', True),
                'controller_id': self.config['dglab']['controller_id']
            }
        }
        return web.json_response(safe_config)
    
    async def handle_get_full_config(self, request):
        """获取完整配置"""
        return web.json_response(self.config)
    
    async def handle_save_config(self, request):
        """保存配置"""
        try:
            new_config = await request.json()
            
            # 保存到 config.yaml
            config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False)
            
            # 更新内存中的配置
            self.config.clear()
            self.config.update(new_config)
            
            # 更新 DGLab 控制器的启用状态
            self.dglab.enabled = new_config['dglab'].get('enabled', True)
            
            logger.info("配置已保存并重新加载")
            return web.json_response({'success': True, 'message': '配置已保存并生效！'})
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return web.json_response({'success': False, 'error': str(e)})
    
    async def handle_get_logs(self, request):
        """获取历史日志"""
        log_type = request.query.get('type', 'all')
        if log_type == 'danmaku':
            return web.json_response(list(self.danmaku_log_buffer))
        elif log_type == 'dglab':
            return web.json_response(list(self.dglab_log_buffer))
        else:
            return web.json_response(list(self.log_buffer))
    
    async def handle_websocket(self, request):
        """WebSocket 连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        
        try:
            async for msg in ws:
                pass  # 暂不处理客户端消息
        finally:
            self.websockets.discard(ws)
        
        return ws
    
    async def handle_obs_websocket(self, request):
        """OBS WebSocket 连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.obs_websockets.add(ws)
        
        try:
            async for msg in ws:
                pass
        finally:
            self.obs_websockets.discard(ws)
        
        return ws
    
    async def broadcast_to_obs(self, message_type: str, data: dict):
        """广播消息到 OBS WebSocket"""
        # 保存到历史记录
        self.obs_history.append({'type': message_type, 'data': data})
        
        # 广播到所有连接的 OBS 客户端
        if self.obs_websockets:
            message = json.dumps({'type': message_type, 'data': data})
            await asyncio.gather(
                *[ws.send_str(message) for ws in self.obs_websockets],
                return_exceptions=True
            )
    
    async def handle_get_obs_history(self, request):
        """获取 OBS 历史记录"""
        return web.json_response(list(self.obs_history))
    
    async def start(self):
        """启动 Web 服务器"""
        # 禁用 aiohttp 访问日志
        self.runner = web.AppRunner(self.app, access_log=None)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        display_host = "localhost" if self.host == "0.0.0.0" else self.host
        logger.info(f"WebUI 已启动: http://{display_host}:{self.port}")
    
    async def stop(self):
        """停止 Web 服务器"""
        # 移除日志处理器，避免退出时的错误
        if hasattr(self, 'log_handler'):
            logging.getLogger().removeHandler(self.log_handler)
        
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("WebUI 已停止")
