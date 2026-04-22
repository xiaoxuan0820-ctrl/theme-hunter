# -*- coding: utf-8 -*-
"""
Telegram Bot
与用户交互，响应查询请求
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ThemeBot:
    """Telegram Bot"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            self.logger.warning("未配置TELEGRAM_BOT_TOKEN")
        
        self.logger.info("ThemeBot 初始化完成")
    
    def send_message(self, text: str):
        """发送消息"""
        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram未配置")
            return False
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown',
            }
            resp = requests.post(url, data=data, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            self.logger.error(f"发送失败: {e}")
            return False
    
    def handle_command(self, command: str) -> str:
        """处理命令"""
        command = command.strip().lower()
        
        from main import ThemeHunter
        hunter = ThemeHunter()
        
        if command in ['/start', '/help']:
            return self._help_text()
        
        elif command == '/scan':
            return hunter.run_scan()
        
        elif command == '/report':
            return hunter.run_morning_report()
        
        elif command.startswith('/query '):
            theme_name = command[7:].strip()
            return hunter.query_theme(theme_name)
        
        elif command == '/list':
            return self._list_themes()
        
        else:
            return f"未知命令: {command}\n\n{self._help_text()}"
    
    def _help_text(self) -> str:
        """帮助文本"""
        return """
🎯 ThemeHunter Bot 命令

/start - 显示帮助
/scan - 快速扫描新题材
/report - 生成早报
/list - 列出所有题材
/query <题材名> - 查询特定题材

示例:
/query 低空经济
/query 固态电池
"""
    
    def _list_themes(self) -> str:
        """列出题材"""
        from core.freshness import ThemeFreshnessManager
        freshness = ThemeFreshnessManager()
        
        new_themes = freshness.get_new_themes()
        old_themes = freshness.get_old_themes()
        
        parts = ["📋 题材列表", "=" * 40]
        
        if new_themes:
            parts.append("\n🆕 新题材:")
            for t in new_themes[:10]:
                parts.append(f"• {t.name} (活跃{t.days_active}天)")
        
        if old_themes:
            parts.append("\n📦 旧题材:")
            for t in old_themes[:5]:
                parts.append(f"• {t.name}")
        
        return "\n".join(parts)
    
    def start_webhook(self, port: int = 8080):
        """启动Webhook服务器"""
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        
        @app.route(f'/webhook/{self.bot_token}', methods=['POST'])
        def webhook():
            data = request.get_json()
            
            if 'message' in data:
                chat_id = data['message']['chat']['id']
                text = data['message'].get('text', '')
                
                response = self.handle_command(text)
                self.send_message(response)
            
            return jsonify({'ok': True})
        
        @app.route('/health')
        def health():
            return jsonify({'status': 'ok'})
        
        self.logger.info(f"启动Webhook服务: :{port}")
        app.run(host='0.0.0.0', port=port)


def main():
    """主入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    bot = ThemeBot()
    bot.start_webhook()


if __name__ == "__main__":
    main()
