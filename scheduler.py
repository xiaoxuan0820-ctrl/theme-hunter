# -*- coding: utf-8 -*-
"""
定时调度器
定时执行任务
"""

import os
import logging
import time
from datetime import datetime, time as dtime
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class Scheduler:
    """定时调度器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载配置
        config_path = Path(__file__).parent / "config" / "config.yaml"
        self.config = yaml.safe_load(open(config_path, 'r', encoding='utf-8'))
        
        self.schedule = self.config.get('schedule', {})
        
        # 任务映射
        self.tasks = {
            'morning_report': self._run_morning_report,
            'midday_scan': self._run_midday_scan,
            'afternoon_report': self._run_afternoon_report,
            'evening_summary': self._run_evening_summary,
        }
        
        self.logger.info("调度器初始化完成")
        self.logger.info(f"定时任务: {list(self.schedule.keys())}")
    
    def _run_morning_report(self):
        """早报"""
        self.logger.info("执行早报任务...")
        from main import ThemeHunter
        hunter = ThemeHunter()
        report = hunter.run_morning_report()
        self._save_report("早报", report)
        self._send_notification(report)
    
    def _run_midday_scan(self):
        """午间扫描"""
        self.logger.info("执行午间扫描...")
        from main import ThemeHunter
        hunter = ThemeHunter()
        report = hunter.run_scan()
        self._save_report("午间扫描", report)
    
    def _run_afternoon_report(self):
        """午后报告"""
        self.logger.info("执行午后报告...")
        from main import ThemeHunter
        hunter = ThemeHunter()
        report = hunter.run_morning_report()  # 复用早报逻辑
        self._save_report("午后报告", report)
    
    def _run_evening_summary(self):
        """晚间总结"""
        self.logger.info("执行晚间总结...")
        from main import ThemeHunter
        hunter = ThemeHunter()
        report = hunter.run_morning_report()
        self._save_report("晚间总结", report)
        self._send_notification(report)
    
    def _run_hourly_report(self):
        """每小时报告"""
        self.logger.info("执行每小时报告...")
        from main import ThemeHunter
        hunter = ThemeHunter()
        report = hunter.run_morning_report()
        self._save_report("每小时报告", report)
        self._send_notification(report)
    
    def _save_report(self, report_type: str, content: str):
        """保存报告"""
        output_dir = Path(__file__).parent / "output" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{report_type}_{date_str}.txt"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"报告已保存: {filepath}")
    
    def _send_notification(self, content: str):
        """发送通知"""
        # Telegram通知（如果配置了）
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if bot_token and chat_id:
            try:
                import requests
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': content[:4096],  # Telegram限制4096字符
                    'parse_mode': 'Markdown',
                }
                requests.post(url, data=data, timeout=10)
                self.logger.info("Telegram通知已发送")
            except Exception as e:
                self.logger.error(f"Telegram通知失败: {e}")
    
    def run_scheduler(self):
        """运行调度器"""
        self.logger.info("调度器启动...")
        
        last_hour = -1  # 记录上次执行的小时
        
        while True:
            now = datetime.now()
            current_time = now.time()
            current_hour = now.hour
            
            # 检查每个定时任务
            for task_name, task_time_str in self.schedule.items():
                # 跳过非时间字符串配置
                if not isinstance(task_time_str, str) or ':' not in str(task_time_str):
                    continue
                try:
                    task_time = dtime.fromisoformat(task_time_str)
                except:
                    continue
                
                # 判断是否到达执行时间（精确到分钟）
                if (current_time.hour == task_time.hour and 
                    current_time.minute == task_time.minute):
                    
                    if task_name in self.tasks:
                        try:
                            self.tasks[task_name]()
                        except Exception as e:
                            self.logger.error(f"任务执行失败 {task_name}: {e}")
            
            # 每小时推送一次报告（整点时刻）
            if current_hour != last_hour and current_time.minute == 0:
                self.logger.info(f"⏰ 每小时报告触发: {current_hour}:00")
                try:
                    self._run_hourly_report()
                except Exception as e:
                    self.logger.error(f"每小时报告执行失败: {e}")
                last_hour = current_hour
            
            # 每分钟检查一次
            time.sleep(60)


def main():
    """主入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = Scheduler()
    scheduler.run_scheduler()


if __name__ == "__main__":
    main()
