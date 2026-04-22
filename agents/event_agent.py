# -*- coding: utf-8 -*-
"""
Event Agent - 事件策划师
权重: 1.0
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Event:
    name: str
    event_type: str
    date: datetime
    affected_themes: List[str]
    impact_level: str = "medium"


class EventAgent:
    """事件策划师"""
    
    EVENT_KEYWORDS = ['峰会', '论坛', '博览会', '发布会', '发布会', '新品']
    
    REGULAR_EVENTS = [
        {'name': '全国两会', 'month': 3, 'day': 5, 'type': 'policy', 'themes': ['政策']},
        {'name': '博鳌亚洲论坛', 'month': 3, 'day': 28, 'type': 'conference', 'themes': ['一带一路']},
        {'name': '进博会', 'month': 11, 'day': 5, 'type': 'conference', 'themes': ['消费']},
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.0
        self.events = []
        self._load_events()
    
    def _load_events(self):
        year = datetime.now().year
        for config in self.REGULAR_EVENTS:
            if config.get('month') and config.get('day'):
                self.events.append(Event(
                    name=config['name'],
                    event_type=config['type'],
                    date=datetime(year, config['month'], config['day']),
                    affected_themes=config.get('themes', []),
                    impact_level='high',
                ))
    
    def analyze_upcoming(self, days: int = 30) -> List[Event]:
        result = []
        cutoff = datetime.now() + timedelta(days=days)
        
        for event in self.events:
            if datetime.now() <= event.date <= cutoff:
                result.append(event)
        
        return sorted(result, key=lambda e: e.date)
    
    def detect_from_news(self, news_list: List[Any]) -> List[Event]:
        detected = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            for kw in self.EVENT_KEYWORDS:
                if kw in text:
                    event = Event(
                        name=getattr(news, 'title', '')[:50],
                        event_type='news',
                        date=getattr(news, 'publish_time', datetime.now()),
                        affected_themes=[],
                        impact_level='medium',
                    )
                    detected.append(event)
                    break
        
        return detected
