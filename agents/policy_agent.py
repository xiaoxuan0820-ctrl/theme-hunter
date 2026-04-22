# -*- coding: utf-8 -*-
"""
Policy Agent - 政策解读师
权重: 1.3
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PolicyInsight:
    policy_title: str
    source: str
    publish_date: datetime
    benefit_sectors: List[str]
    estimated_benefit_level: str
    expected_implementation: datetime
    confidence: float


class PolicyAgent:
    """政策解读师"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.3
    
    def analyze(self, news_list: List[Any]) -> List[PolicyInsight]:
        insights = []
        
        policy_sources = ['国务院', '发改委', '工信部', '财政部', '证监会']
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            for source in policy_sources:
                if source in text:
                    insight = PolicyInsight(
                        policy_title=getattr(news, 'title', ''),
                        source=getattr(news, 'source', source),
                        publish_date=getattr(news, 'publish_time', datetime.now()),
                        benefit_sectors=self._extract_sectors(text),
                        estimated_benefit_level=self._estimate_level(text),
                        expected_implementation=datetime.now(),
                        confidence=0.7,
                    )
                    insights.append(insight)
                    break
        
        return insights
    
    def _extract_sectors(self, text: str) -> List[str]:
        sectors = []
        known = ['新能源汽车', '半导体', 'AI', '低空经济', '氢能', '医药']
        for s in known:
            if s in text:
                sectors.append(s)
        return sectors
    
    def _estimate_level(self, text: str) -> str:
        if any(kw in text for kw in ['重磅', '重大', '全国']):
            return 'high'
        return 'medium'
