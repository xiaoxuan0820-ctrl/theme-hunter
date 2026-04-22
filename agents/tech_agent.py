# -*- coding: utf-8 -*-
"""
Tech Agent - 技术前瞻者
权重: 1.1
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TechInsight:
    tech_name: str
    news_title: str
    tech_category: str
    maturity_level: str
    readiness_score: float
    market_potential: float
    affected_industries: List[str]


class TechAgent:
    """技术前瞻者"""
    
    TECH_CATEGORIES = {
        'AI': ['AI', '人工智能', '大模型', 'ChatGPT'],
        '新能源': ['锂电池', '固态电池', '氢能', '光伏'],
        '半导体': ['芯片', '半导体', '光刻机'],
        '机器人': ['人形机器人', '具身智能'],
    }
    
    MATURITY_KEYWORDS = {
        '实验室': ['实验室', '研发中'],
        '中试': ['中试', '试验', '验证'],
        '量产': ['量产', '批量生产', '规模化'],
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.1
    
    def analyze(self, news_list: List[Any]) -> List[TechInsight]:
        insights = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            category = None
            for cat, kws in self.TECH_CATEGORIES.items():
                if any(kw in text for kw in kws):
                    category = cat
                    break
            
            if not category:
                continue
            
            maturity = 'unknown'
            for mat, kws in self.MATURITY_KEYWORDS.items():
                if any(kw in text for kw in kws):
                    maturity = mat
                    break
            
            insight = TechInsight(
                tech_name=self._get_tech_name(text, category),
                news_title=getattr(news, 'title', ''),
                tech_category=category,
                maturity_level=maturity,
                readiness_score=self._calc_readiness(maturity),
                market_potential=self._calc_potential(category),
                affected_industries=self._get_affected(category),
            )
            insights.append(insight)
        
        return insights
    
    def _get_tech_name(self, text: str, category: str) -> str:
        for kw in self.TECH_CATEGORIES.get(category, []):
            if kw in text:
                return kw
        return category
    
    def _calc_readiness(self, maturity: str) -> float:
        scores = {'实验室': 20, '中试': 50, '量产': 80}
        return scores.get(maturity, 30)
    
    def _calc_potential(self, category: str) -> float:
        potentials = {'AI': 95, '新能源': 90, '半导体': 85, '机器人': 80}
        return potentials.get(category, 70)
    
    def _get_affected(self, category: str) -> List[str]:
        mapping = {
            'AI': ['软件开发', '云计算', '智能硬件'],
            '新能源': ['汽车', '电力', '储能'],
            '半导体': ['消费电子', '汽车电子'],
            '机器人': ['制造业', '物流'],
        }
        return mapping.get(category, [])
