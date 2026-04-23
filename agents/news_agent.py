# -*- coding: utf-8 -*-
"""
News Agent - 新闻猎手（升级版）
权重: 1.3
功能：
- 区分新闻来源权威性
- 交叉验证多源信息
- 识别信息真伪
- 输出：新闻可信度、热度指数、传播速度
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class SourceAuthority(Enum):
    """来源权威性等级"""
    OFFICIAL = ("官方媒体", 1.0)                    # 新华社、人民日报等
    AUTHORITATIVE_FINANCE = ("权威财经", 0.9)       # 三大报等
    PROFESSIONAL_FINANCE = ("专业财经", 0.8)        # 东方财富等
    INDUSTRY = ("行业媒体", 0.7)                   # 行业专业媒体
    SELF_MEDIA = ("自媒体", 0.5)                   # 自媒体
    
    def __init__(self, label, score):
        self.label = label
        self.score = score


@dataclass
class NewsInsight:
    """新闻洞察"""
    title: str
    source: str
    publish_time: datetime
    
    # 权威性评估
    authority: SourceAuthority
    authority_score: float           # 0-1
    
    # 可信度评估
    credibility: float               # 0-1
    
    # 热度评估
    heat_score: float                # 0-100
    propagation_speed: float         # 传播速度 0-1
    
    # 题材关联
    related_themes: List[str] = field(default_factory=list)
    
    # 类型标签
    is_germination: bool = False     # 萌芽期信号
    is_hot: bool = False             # 爆发期信号
    is_warning: bool = False         # 预警信号
    
    # 情感分析
    sentiment_score: float = 0.0     # -1到1
    
    # 交叉验证
    cross_validated: bool = False    # 是否多源验证
    similar_news_count: int = 0       # 相似新闻数量


@dataclass
class VerificationResult:
    """验证结果"""
    is_verified: bool
    verification_count: int          # 验证来源数量
    consistency_score: float        # 一致性得分
    verified_aspects: List[str]      # 已验证的方面
    warning_signs: List[str]         # 可疑迹象


class NewsAgent:
    """新闻猎手 - 多维度新闻分析"""
    
    # 权威来源定义
    SOURCE_CATEGORIES = {
        SourceAuthority.OFFICIAL: [
            '新华社', '人民日报', '央视', '央视新闻', '中国政府网',
            '国务院', '人民网', '新华网'
        ],
        SourceAuthority.AUTHORITATIVE_FINANCE: [
            '上海证券报', '中国证券报', '证券时报', '证券日报',
            '第一财经', '财新', '经济观察报', '21世纪经济报道'
        ],
        SourceAuthority.PROFESSIONAL_FINANCE: [
            '东方财富网', '同花顺', '雪球', 'Wind资讯',
            '彭博', '路透', '36氪', '钛媒体'
        ],
        SourceAuthority.INDUSTRY: [
            '汽车之家', '盖世汽车', 'OFweek', '高工锂电',
            '芯智讯', 'ittbank', '半导体行业观察'
        ],
        SourceAuthority.SELF_MEDIA: [
            '微博', '微信公众号', '头条号', '百家号'
        ]
    }
    
    # 萌芽期关键词
    GERMINATION_KEYWORDS = [
        '首次', '突破', '首款', '首创', '新产品', '新技术',
        '重大进展', '取得成功', '研发成功', '填补空白'
    ]
    
    # 爆发期关键词
    HOT_KEYWORDS = [
        '涨停', '暴涨', '引爆', '爆发', '出圈', '全民',
        '抢筹', '疯涨', '连续涨停', '翻倍', '引爆'
    ]
    
    # 预警关键词
    WARNING_KEYWORDS = [
        '澄清', '否认', '减持', '退市', 'ST', '风险',
        '监管', '调查', '问询', '爆雷', '造假'
    ]
    
    # 情感词典
    POSITIVE_WORDS = [
        '利好', '大涨', '爆发', '突破', '看好', '推荐',
        '买入', '增持', '超预期', '高增长', '景气', '强势'
    ]
    
    NEGATIVE_WORDS = [
        '利空', '下跌', '风险', '问题', '亏损', '减持',
        '悲观', '下调', '不及预期', '暴雷', '造假'
    ]
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.3
        self.name = "新闻猎手"
        
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "keywords.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            self.source_authority = self.config.get('source_authority', {})
        except Exception as e:
            self.logger.warning(f"加载配置失败: {e}")
            self.source_authority = {}
        
        # 新闻缓存用于交叉验证
        self.news_cache: Dict[str, List[NewsInsight]] = defaultdict(list)
    
    def analyze(self, news_list: List[Any], keywords_config: Dict = None) -> List[NewsInsight]:
        """分析新闻列表"""
        insights = []
        
        for news in news_list:
            insight = self._analyze_single_news(news, keywords_config)
            if insight:
                insights.append(insight)
        
        # 交叉验证
        insights = self._cross_validate(insights)
        
        # 按热度排序
        insights.sort(key=lambda x: x.heat_score, reverse=True)
        
        return insights
    
    def _analyze_single_news(self, news: Any, keywords_config: Dict = None) -> Optional[NewsInsight]:
        """分析单条新闻"""
        title = getattr(news, 'title', '')
        content = getattr(news, 'content', '')
        source = getattr(news, 'source', '')
        publish_time = getattr(news, 'publish_time', datetime.now())
        text = f"{title} {content}"
        
        if not title:
            return None
        
        # 权威性评估
        authority = self._determine_authority(source, text)
        authority_score = authority.score
        
        # 类型判断
        is_germination = any(kw in text for kw in self.GERMINATION_KEYWORDS)
        is_hot = any(kw in text for kw in self.HOT_KEYWORDS)
        is_warning = any(kw in text for kw in self.WARNING_KEYWORDS)
        
        # 情感分析
        sentiment = self._calc_sentiment(text)
        
        # 热度评分
        heat = self._calc_heat_score(news, authority, is_hot, is_germination)
        
        # 传播速度
        propagation = self._calc_propagation_speed(publish_time, heat)
        
        # 题材关联
        themes = self._extract_themes(text, keywords_config)
        
        # 可信度评估
        credibility = self._assess_credibility(text, authority, is_warning)
        
        return NewsInsight(
            title=title,
            source=source,
            publish_time=publish_time,
            authority=authority,
            authority_score=authority_score,
            credibility=credibility,
            heat_score=heat,
            propagation_speed=propagation,
            related_themes=themes,
            is_germination=is_germination,
            is_hot=is_hot,
            is_warning=is_warning,
            sentiment_score=sentiment
        )
    
    def _determine_authority(self, source: str, text: str) -> SourceAuthority:
        """判断来源权威性"""
        # 优先匹配
        for authority, sources in self.SOURCE_CATEGORIES.items():
            for s in sources:
                if s in source or s in text:
                    return authority
        
        # 配置文件中的来源
        config_sources = self.source_authority.get('official', {}).get('sources', [])
        for s in config_sources:
            if s in source:
                return SourceAuthority.OFFICIAL
        
        return SourceAuthority.SELF_MEDIA
    
    def _calc_sentiment(self, text: str) -> float:
        """计算情感得分"""
        pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text)
        
        score = (pos_count - neg_count) / max(pos_count + neg_count, 1)
        return max(-1.0, min(score, 1.0))
    
    def _calc_heat_score(self, news: Any, authority: SourceAuthority, 
                         is_hot: bool, is_germination: bool) -> float:
        """计算热度评分"""
        base = 50
        
        # 来源加成
        base += authority.score * 20
        
        # 爆发期加成
        if is_hot:
            base += 20
        
        # 萌芽期加成
        if is_germination:
            base += 15
        
        # 时效性加成
        publish_time = getattr(news, 'publish_time', datetime.now())
        age_hours = (datetime.now() - publish_time).total_seconds() / 3600
        
        if age_hours < 2:
            base += 15
        elif age_hours < 12:
            base += 10
        elif age_hours < 24:
            base += 5
        
        return min(base, 100)
    
    def _calc_propagation_speed(self, publish_time: datetime, heat_score: float) -> float:
        """计算传播速度"""
        age_hours = (datetime.now() - publish_time).total_seconds() / 3600
        
        if age_hours <= 0:
            return 1.0
        
        # 速度 = 热度 / 时间
        speed = min(heat_score / age_hours, 1.0)
        return speed
    
    def _extract_themes(self, text: str, keywords_config: Dict = None) -> List[str]:
        """提取题材"""
        themes = []
        
        if keywords_config:
            for theme, config in keywords_config.items():
                keywords = config.get('keywords', [])
                for kw in keywords:
                    if kw in text:
                        if theme not in themes:
                            themes.append(theme)
                        break
        
        return themes
    
    def _assess_credibility(self, text: str, authority: SourceAuthority, 
                            is_warning: bool) -> float:
        """评估可信度"""
        base = authority.score
        
        # 预警信号降低可信度
        if is_warning:
            base *= 0.7
        
        # 包含"澄清"或"否认"的可信度降低
        if '澄清' in text or '否认' in text:
            base *= 0.8
        
        # 包含具体数据的可信度提高
        if any(c in text for c in ['%', '亿元', '万元', '股', '次']):
            base += 0.1
        
        # 包含"根据"、"数据显示"等可信度提高
        formal_markers = ['根据', '数据显示', '据统计', '据悉', '从']
        if any(m in text for m in formal_markers):
            base += 0.05
        
        return max(0.0, min(base, 1.0))
    
    def _cross_validate(self, insights: List[NewsInsight]) -> List[NewsInsight]:
        """交叉验证"""
        # 按标题相似度分组
        similar_groups: Dict[str, List[NewsInsight]] = defaultdict(list)
        
        for insight in insights:
            # 使用标题前20个字符作为key
            key = insight.title[:20].lower()
            similar_groups[key].append(insight)
        
        # 更新验证状态
        for key, group in similar_groups.items():
            count = len(group)
            
            # 检查一致性（来源是否相近）
            sources = [g.source for g in group]
            
            for insight in group:
                insight.similar_news_count = count
                
                if count >= 3:
                    insight.cross_validated = True
                elif count >= 2:
                    # 检查来源一致性
                    if any(s == insight.source for s in sources if s != insight.source):
                        insight.cross_validated = True
        
        return insights
    
    def verify_information(self, title: str, news_list: List[NewsInsight]) -> VerificationResult:
        """验证信息真实性"""
        # 查找相似新闻
        similar = [n for n in news_list if n.title[:20] == title[:20]]
        
        if not similar:
            return VerificationResult(
                is_verified=False,
                verification_count=0,
                consistency_score=0.0,
                verified_aspects=[],
                warning_signs=["未找到其他来源验证"]
            )
        
        # 计算一致性
        sources = [n.source for n in similar]
        unique_sources = len(set(sources))
        
        # 检查情感一致性
        sentiments = [n.sentiment_score for n in similar]
        sentiment_variance = max(sentiments) - min(sentiments)
        
        verified_aspects = []
        warning_signs = []
        
        if unique_sources >= 2:
            verified_aspects.append("多源报道")
        elif unique_sources == 1:
            warning_signs.append("单一来源")
        
        if sentiment_variance < 0.5:
            verified_aspects.append("情感一致")
        else:
            warning_signs.append("情感矛盾")
        
        # 检查时间差
        times = [n.publish_time for n in similar]
        time_span = max(times) - min(times)
        if time_span < timedelta(hours=2):
            verified_aspects.append("同步报道")
        
        consistency = 1.0 - (sentiment_variance / 2)
        
        return VerificationResult(
            is_verified=unique_sources >= 2 and sentiment_variance < 0.5,
            verification_count=len(similar),
            consistency_score=max(0, consistency),
            verified_aspects=verified_aspects,
            warning_signs=warning_signs
        )
    
    def generate_news_report(self, insights: List[NewsInsight]) -> str:
        """生成新闻分析报告"""
        if not insights:
            return "📰 暂无相关新闻"
        
        parts = ["\n📰 新闻分析报告", "=" * 40]
        
        # 分类统计
        germination = [i for i in insights if i.is_germination]
        hot = [i for i in insights if i.is_hot]
        warning = [i for i in insights if i.is_warning]
        verified = [i for i in insights if i.cross_validated]
        
        parts.append(f"\n📊 统计概览")
        parts.append(f"├ 总计: {len(insights)}条")
        parts.append(f"├ 萌芽信号: {len(germination)}条")
        parts.append(f"├ 爆发信号: {len(hot)}条")
        parts.append(f"├ 预警信号: {len(warning)}条")
        parts.append(f"└ 多源验证: {len(verified)}条")
        
        # 重点新闻
        if germination:
            parts.append(f"\n🌱 萌芽期信号:")
            for i in germination[:3]:
                parts.append(f"  • {i.title[:35]}...")
        
        if hot:
            parts.append(f"\n🔥 爆发期信号:")
            for i in hot[:3]:
                parts.append(f"  • {i.title[:35]}...")
        
        if warning:
            parts.append(f"\n⚠️ 预警信号:")
            for i in warning[:3]:
                parts.append(f"  • {i.title[:35]}...")
        
        return "\n".join(parts)


from enum import Enum
