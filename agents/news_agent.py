# -*- coding: utf-8 -*-
"""
News Agent - 新闻猎手
权重: 1.2
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class NewsInsight:
    title: str
    source: str
    publish_time: datetime
    related_themes: List[str] = field(default_factory=list)
    is_hot: bool = False
    is_germination: bool = False
    sentiment_score: float = 0.0


class NewsAgent:
    """新闻猎手"""
    
    HOT_KEYWORDS = ['涨停', '暴涨', '引爆', '爆发', '出圈']
    GERMINATION_KEYWORDS = ['首次', '突破', '首款', '首创', '新产品']
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.2
    
    def analyze(self, news_list: List[Any], keywords_config: Dict = None) -> List[NewsInsight]:
        insights = []
        
        for news in news_list:
            title = getattr(news, 'title', '')
            content = getattr(news, 'content', '')
            text = f"{title} {content}"
            
            themes = []
            if keywords_config:
                for theme, config in keywords_config.items():
                    for kw in config.get('keywords', []):
                        if kw in text:
                            themes.append(theme)
                            break
            
            insight = NewsInsight(
                title=title,
                source=getattr(news, 'source', ''),
                publish_time=getattr(news, 'publish_time', datetime.now()),
                related_themes=themes,
                is_hot=any(kw in text for kw in self.HOT_KEYWORDS),
                is_germination=any(kw in text for kw in self.GERMINATION_KEYWORDS),
                sentiment_score=self._calc_sentiment(text),
            )
            insights.append(insight)
        
        return insights
    
    def _calc_sentiment(self, text: str) -> float:
        positive = ['利好', '大涨', '爆发', '突破', '看好']
        negative = ['利空', '下跌', '风险', '问题']
        score = sum(1 for p in positive if p in text) - sum(1 for n in negative if n in text)
        return max(-1, min(score / 5, 1))
