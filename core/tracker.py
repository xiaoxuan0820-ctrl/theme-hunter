# -*- coding: utf-8 -*-
"""
题材跟踪引擎
跟踪已识别题材的发展，监控关键指标
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class TrackingStatus(Enum):
    """跟踪状态枚举"""
    ACTIVE = "active"           # 活跃跟踪中
    TRIGGERED = "triggered"      # 已触发信号
    COOLDOWN = "cooldown"        # 冷却中
    CLOSED = "closed"           # 已关闭
    
    @property
    def emoji(self) -> str:
        """状态表情"""
        emojis = {
            "active": "🔵",
            "triggered": "🟢",
            "cooldown": "🟡",
            "closed": "⚪",
        }
        return emojis.get(self.value, "⚪")


@dataclass
class TrackingRecord:
    """跟踪记录"""
    record_id: str
    theme_name: str
    status: TrackingStatus
    
    # 跟踪指标
    score_history: List[float] = field(default_factory=list)  # 得分历史
    heat_history: List[float] = field(default_factory=list)   # 热度历史
    news_count_history: List[int] = field(default_factory=list)  # 新闻数量历史
    
    # 事件记录
    events: List[Dict] = field(default_factory=list)  # 触发事件
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    triggered_at: datetime = None
    
    # 预警
    alerts: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'record_id': self.record_id,
            'theme_name': self.theme_name,
            'status': self.status.value,
            'score_history': self.score_history,
            'heat_history': self.heat_history,
            'news_count_history': self.news_count_history,
            'events': self.events,
            'created_at': self.created_at.isoformat(),
            'last_update': self.last_update.isoformat(),
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'alerts': self.alerts,
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'TrackingRecord':
        """从字典创建"""
        d['status'] = TrackingStatus(d.get('status', 'active'))
        d['created_at'] = datetime.fromisoformat(d['created_at'])
        d['last_update'] = datetime.fromisoformat(d['last_update'])
        if d.get('triggered_at'):
            d['triggered_at'] = datetime.fromisoformat(d['triggered_at'])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ThemeTracker:
    """
    题材跟踪器
    
    功能：
    - 跟踪题材发展轨迹
    - 监控关键指标变化
    - 触发预警和信号
    - 记录历史数据
    """
    
    def __init__(self, data_dir: str = None):
        """
        初始化跟踪器
        
        Args:
            data_dir: 数据目录路径
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "themes"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.tracking_file = self.data_dir / "tracking_records.json"
        self.records: Dict[str, TrackingRecord] = {}
        self._load_records()
        
        # 预警回调函数
        self.alert_callbacks: List[Callable] = []
    
    def _load_records(self):
        """加载跟踪记录"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for d in data:
                        record = TrackingRecord.from_dict(d)
                        self.records[record.theme_name] = record
            except Exception as e:
                self.logger.warning(f"加载跟踪记录失败: {e}")
    
    def _save_records(self):
        """保存跟踪记录"""
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [r.to_dict() for r in self.records.values()],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            self.logger.error(f"保存跟踪记录失败: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """添加预警回调"""
        self.alert_callbacks.append(callback)
    
    def start_tracking(self, theme: Any) -> TrackingRecord:
        """
        开始跟踪题材
        
        Args:
            theme: 题材对象
            
        Returns:
            跟踪记录
        """
        theme_name = theme.name
        
        if theme_name in self.records:
            record = self.records[theme_name]
            record.status = TrackingStatus.ACTIVE
        else:
            record = TrackingRecord(
                record_id=f"tr_{theme_name}_{datetime.now().strftime('%Y%m%d%H%M')}",
                theme_name=theme_name,
                status=TrackingStatus.ACTIVE,
            )
            self.records[theme_name] = record
        
        # 记录初始状态
        self._update_record(record, theme)
        
        self._save_records()
        return record
    
    def stop_tracking(self, theme_name: str):
        """停止跟踪"""
        if theme_name in self.records:
            self.records[theme_name].status = TrackingStatus.CLOSED
            self._save_records()
    
    def _update_record(self, record: TrackingRecord, theme: Any):
        """更新跟踪记录"""
        record.last_update = datetime.now()
        
        # 获取当前指标
        score = getattr(theme, 'heat_score', 0)
        heat = getattr(theme, 'heat_score', 0)
        news_count = getattr(theme, 'news_count', 0)
        
        # 添加历史
        record.score_history.append(score)
        record.heat_history.append(heat)
        record.news_count_history.append(news_count)
        
        # 保持最近30条历史
        max_history = 30
        record.score_history = record.score_history[-max_history:]
        record.heat_history = record.heat_history[-max_history:]
        record.news_count_history = record.news_count_history[-max_history:]
        
        # 检查预警条件
        self._check_alerts(record, theme, score)
    
    def _check_alerts(self, record: TrackingRecord, theme: Any, current_score: float):
        """检查预警条件"""
        alerts = []
        
        if len(record.score_history) >= 2:
            prev_score = record.score_history[-2]
            
            # 热度突然下降
            if prev_score > 70 and current_score < prev_score * 0.7:
                alerts.append({
                    'type': 'heat_drop',
                    'level': 'warning',
                    'message': f"热度突然下降: {prev_score:.0f} → {current_score:.0f}",
                    'time': datetime.now().isoformat(),
                })
            
            # 热度突然上升
            if current_score > 80 and current_score > prev_score * 1.2:
                alerts.append({
                    'type': 'heat_rise',
                    'level': 'opportunity',
                    'message': f"热度快速上升: {prev_score:.0f} → {current_score:.0f}",
                    'time': datetime.now().isoformat(),
                })
        
        # 得分达到高机会阈值
        if current_score >= 85 and record.status != TrackingStatus.TRIGGERED:
            alerts.append({
                'type': 'high_opportunity',
                'level': 'opportunity',
                'message': f"达到高机会评分: {current_score:.0f}",
                'time': datetime.now().isoformat(),
            })
            record.status = TrackingStatus.TRIGGERED
            record.triggered_at = datetime.now()
        
        # 添加预警
        for alert in alerts:
            if alert not in record.alerts[-10:]:  # 避免重复
                record.alerts.append(alert)
                self._trigger_alert(alert, theme)
    
    def _trigger_alert(self, alert: Dict, theme: Any):
        """触发预警"""
        self.logger.info(f"触发预警 [{alert['level']}]: {alert['message']}")
        
        # 调用所有回调
        for callback in self.alert_callbacks:
            try:
                callback(alert, theme)
            except Exception as e:
                self.logger.error(f"预警回调执行失败: {e}")
    
    def update_tracking(self, theme: Any):
        """
        更新跟踪
        
        Args:
            theme: 题材对象
        """
        theme_name = theme.name
        
        if theme_name not in self.records:
            self.start_tracking(theme)
            return
        
        record = self.records[theme_name]
        
        if record.status == TrackingStatus.CLOSED:
            return
        
        self._update_record(record, theme)
        self._save_records()
    
    def get_tracking_status(self, theme_name: str) -> Optional[TrackingRecord]:
        """获取跟踪状态"""
        return self.records.get(theme_name)
    
    def get_active_tracking(self) -> List[TrackingRecord]:
        """获取所有活跃跟踪"""
        return [
            r for r in self.records.values()
            if r.status == TrackingStatus.ACTIVE
        ]
    
    def get_triggered_opportunities(self) -> List[TrackingRecord]:
        """获取已触发的机会"""
        return [
            r for r in self.records.values()
            if r.status == TrackingStatus.TRIGGERED
        ]
    
    def get_trend(self, theme_name: str) -> str:
        """
        获取题材趋势
        
        Returns:
            trend: 'rising', 'falling', 'stable'
        """
        if theme_name not in self.records:
            return 'unknown'
        
        record = self.records[theme_name]
        history = record.score_history
        
        if len(history) < 3:
            return 'stable'
        
        recent = history[-3:]
        
        if all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            return 'rising'
        elif all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            return 'falling'
        else:
            return 'stable'
    
    def generate_report(self, theme_name: str) -> str:
        """生成跟踪报告"""
        if theme_name not in self.records:
            return f"未跟踪题材: {theme_name}"
        
        record = self.records[theme_name]
        
        parts = [
            f"📊 题材跟踪报告: {theme_name}",
            f"状态: {record.status.emoji} {record.status.value}",
            f"开始时间: {record.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"最后更新: {record.last_update.strftime('%Y-%m-%d %H:%M')}",
        ]
        
        if record.score_history:
            current = record.score_history[-1]
            parts.append(f"当前评分: {current:.0f}")
            
            trend = self.get_trend(theme_name)
            trend_emoji = {'rising': '📈', 'falling': '📉', 'stable': '➡️'}.get(trend, '➡️')
            parts.append(f"趋势: {trend_emoji} {trend}")
        
        if record.triggered_at:
            parts.append(f"触发时间: {record.triggered_at.strftime('%Y-%m-%d %H:%M')}")
        
        if record.alerts:
            parts.append(f"\n⚠️ 最近预警 ({len(record.alerts)}条):")
            for alert in record.alerts[-5:]:
                parts.append(f"  • [{alert['level']}] {alert['message']}")
        
        return "\n".join(parts)
    
    def cleanup_old_records(self, days: int = 30):
        """清理旧的跟踪记录"""
        cutoff = datetime.now() - timedelta(days=days)
        
        to_remove = []
        for name, record in self.records.items():
            if record.last_update < cutoff and record.status in [
                TrackingStatus.CLOSED, TrackingStatus.COOLDOWN
            ]:
                to_remove.append(name)
        
        for name in to_remove:
            del self.records[name]
        
        if to_remove:
            self._save_records()
            self.logger.info(f"清理了 {len(to_remove)} 条旧跟踪记录")


# 示例用法
if __name__ == "__main__":
    import logging
    from analyzer import Theme, ThemeStage
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建跟踪器
    tracker = ThemeTracker()
    
    # 创建测试题材
    test_theme = Theme(
        name="低空经济",
        keywords=["低空经济", "eVTOL"],
        related_sectors=["航空航天"],
        sentiment="positive",
        stage=ThemeStage.ERUPTION,
        news_count=15,
        heat_score=88,
    )
    
    # 开始跟踪
    record = tracker.start_tracking(test_theme)
    print(f"开始跟踪: {record.record_id}")
    
    # 更新跟踪
    tracker.update_tracking(test_theme)
    
    # 生成报告
    print(tracker.generate_report("低空经济"))
