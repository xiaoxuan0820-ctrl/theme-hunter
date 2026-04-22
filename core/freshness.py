# -*- coding: utf-8 -*-
"""
题材新鲜度管理器
判断题材新旧，过滤旧题材
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ThemeRecord:
    """题材记录"""
    name: str
    first_mention: datetime
    last_active: datetime
    status: str = "active"  # new, active, old, dead
    news_count: int = 0
    stage: str = "unknown"
    leader_gain: float = 0.0  # 龙头涨幅%
    days_active: int = 0
    notes: str = ""
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['first_mention'] = self.first_mention.isoformat()
        d['last_active'] = self.last_active.isoformat()
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'ThemeRecord':
        d['first_mention'] = datetime.fromisoformat(d['first_mention'])
        d['last_active'] = datetime.fromisoformat(d['last_active'])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    @property
    def is_new(self) -> bool:
        """是否是新题材（30天内）"""
        return self.days_active <= 30 and self.status != "old"
    
    @property
    def is_old(self) -> bool:
        """是否是旧题材"""
        if self.status == "old" or self.status == "dead":
            return True
        if self.days_active > 30:
            return True
        if self.leader_gain > 100:  # 龙头翻倍
            return True
        return False


class ThemeFreshnessManager:
    """
    题材新鲜度管理器
    
    核心功能：
    - 判断题材新旧
    - 过滤旧题材
    - 记录题材历史
    - 发现新题材
    """
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "keywords.yaml"
        
        self.keywords_config = yaml.safe_load(open(config_path, 'r', encoding='utf-8'))
        
        # 存储路径
        self.records_dir = Path(__file__).parent.parent / "data" / "themes"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.records_dir / "theme_history.json"
        
        # 题材记录
        self.records: Dict[str, ThemeRecord] = {}
        self._load_records()
    
    def _load_records(self):
        """加载记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, d in data.items():
                        self.records[name] = ThemeRecord.from_dict(d)
            except Exception as e:
                self.logger.warning(f"加载题材记录失败: {e}")
    
    def _save_records(self):
        """保存记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({k: v.to_dict() for k, v in self.records.items()}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存题材记录失败: {e}")
    
    def discover_new_themes(self, news_list: List[Any]) -> List[str]:
        """
        从新闻中发现新题材
        
        Args:
            news_list: 新闻列表
            
        Returns:
            新发现的题材列表
        """
        new_themes = []
        theme_kw_map = self.keywords_config.get('theme_keywords', {})
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            for theme_name, config in theme_kw_map.items():
                keywords = config.get('keywords', [])
                
                for kw in keywords:
                    if kw in text:
                        # 检查是否已存在
                        if theme_name not in self.records:
                            # 新题材！
                            record = ThemeRecord(
                                name=theme_name,
                                first_mention=getattr(news, 'publish_time', datetime.now()),
                                last_active=datetime.now(),
                                status="new",
                                news_count=1,
                            )
                            self.records[theme_name] = record
                            new_themes.append(theme_name)
                            self.logger.info(f"发现新题材: {theme_name}")
                        break
        
        if new_themes:
            self._save_records()
        
        return new_themes
    
    def update_theme(self, theme_name: str, news_count: int = 0, stage: str = None):
        """更新题材记录"""
        if theme_name in self.records:
            record = self.records[theme_name]
            record.last_active = datetime.now()
            record.days_active = (datetime.now() - record.first_mention).days + 1
            
            if news_count > 0:
                record.news_count += news_count
            
            if stage:
                record.stage = stage
            
            # 判断是否变成旧题材
            if self._is_old_theme(record):
                if record.status != "old":
                    self.logger.info(f"题材变为旧题材: {theme_name}")
                    record.status = "old"
                    record.notes = f"已活跃{days}天，龙头涨幅{record.leader_gain}%"
        else:
            # 新建记录
            record = ThemeRecord(
                name=theme_name,
                first_mention=datetime.now(),
                last_active=datetime.now(),
                status="active",
                news_count=news_count or 1,
            )
            self.records[theme_name] = record
        
        self._save_records()
    
    def _is_old_theme(self, record: ThemeRecord) -> bool:
        """判断是否为旧题材"""
        # 活跃天数超过30天
        if record.days_active > 30:
            return True
        
        # 龙头涨幅超过100%
        if record.leader_gain > 100:
            return True
        
        # 已标记为dead
        if record.status == "dead":
            return True
        
        return False
    
    def filter_new_themes(self, themes: List[str]) -> List[str]:
        """
        过滤出新鲜题材
        
        Args:
            themes: 题材名称列表
            
        Returns:
            只包含新题材的列表
        """
        new_themes = []
        old_themes = []
        
        for theme in themes:
            if theme in self.records:
                record = self.records[theme]
                if record.is_old:
                    old_themes.append(theme)
                else:
                    new_themes.append(theme)
            else:
                # 新发现
                new_themes.append(theme)
        
        if old_themes:
            self.logger.info(f"过滤旧题材: {', '.join(old_themes)}")
        
        return new_themes
    
    def get_theme_status(self, theme_name: str) -> Optional[ThemeRecord]:
        """获取题材状态"""
        return self.records.get(theme_name)
    
    def get_new_themes(self) -> List[ThemeRecord]:
        """获取所有新题材"""
        return [r for r in self.records.values() if r.is_new]
    
    def get_old_themes(self) -> List[ThemeRecord]:
        """获取所有旧题材"""
        return [r for r in self.records.values() if r.is_old]
    
    def mark_as_old(self, theme_name: str, reason: str = ""):
        """标记为旧题材"""
        if theme_name in self.records:
            record = self.records[theme_name]
            record.status = "old"
            record.notes = reason
            self._save_records()
            self.logger.info(f"标记旧题材: {theme_name}, 原因: {reason}")
    
    def generate_freshness_report(self) -> str:
        """生成新鲜度报告"""
        new_themes = self.get_new_themes()
        old_themes = self.get_old_themes()
        
        parts = ["📊 题材新鲜度报告", "=" * 40]
        
        if new_themes:
            parts.append(f"\n🆕 新题材 ({len(new_themes)}个):")
            for r in sorted(new_themes, key=lambda x: x.last_active, reverse=True)[:5]:
                parts.append(f"• {r.name}: 活跃{r.days_active}天")
        
        if old_themes:
            parts.append(f"\n📦 旧题材 ({len(old_themes)}个):")
            for r in sorted(old_themes, key=lambda x: x.last_active, reverse=True)[:5]:
                parts.append(f"• {r.name}: {r.notes or f'活跃{r.days_active}天'}")
        
        return "\n".join(parts)
