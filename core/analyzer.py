# -*- coding: utf-8 -*-
"""
Theme Analyzer - 题材分析引擎（升级版）
从新闻中提取、分析题材，判断题材阶段和催化剂
新增：可信度评估、风险评估、资金追踪
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import yaml
import re

logger = logging.getLogger(__name__)


class ThemeStage(Enum):
    """题材阶段枚举"""
    UNKNOWN = "unknown"           # 未知
    GERMINATION = "germination"   # 萌芽期
    ERUPTION = "eruption"         # 爆发期
    SPECULATION = "speculation"   # 炒作期
    COOLDOWN = "cooldown"         # 退潮期
    DEAD = "dead"                 # 消亡期
    
    @property
    def description(self) -> str:
        """阶段描述"""
        descriptions = {
            "unknown": "未知",
            "germination": "萌芽期",
            "eruption": "爆发期",
            "speculation": "炒作期",
            "cooldown": "退潮期",
            "dead": "消亡期",
        }
        return descriptions.get(self.value, self.value)
    
    @property
    def emoji(self) -> str:
        """阶段emoji"""
        emojis = {
            "unknown": "⚪",
            "germination": "🟢",
            "eruption": "🔵",
            "speculation": "🟡",
            "cooldown": "🟠",
            "dead": "🔴",
        }
        return emojis.get(self.value, "⚪")


@dataclass
class Catalyst:
    """催化剂信息"""
    type: str                    # 类型: policy, commercial, technology, event
    title: str                   # 标题
    description: str             # 描述
    expected_date: datetime      # 预期时间
    confidence: float = 0.5      # 置信度 0-1
    impact_level: str = "medium" # 影响级别: high, medium, low
    
    # 新增字段
    catalyst_level: str = "medium"  # 催化剂级别: 短期(1-7天), 中期(1-4周), 长期(1-6月)
    source_count: int = 1         # 来源数量
    cross_validated: bool = False  # 是否多源验证
    
    def days_until(self) -> int:
        """距离催化剂的天数"""
        delta = self.expected_date - datetime.now()
        return delta.days
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        d = asdict(self)
        d['expected_date'] = self.expected_date.isoformat()
        return d


@dataclass
class CredibilityAssessment:
    """可信度评估"""
    total_score: float            # 总分 0-100
    
    # 各维度得分
    policy_level_score: float    # 政策级别得分
    media_authority_score: float # 媒体权威性得分
    consistency_score: float     # 信息一致性得分
    freshness_score: float       # 时效性得分
    
    # 详细评估
    policy_level: str = ""       # 政策级别描述
    media_sources: List[str] = field(default_factory=list)  # 媒体来源
    validation_count: int = 0    # 验证来源数量
    
    def get_stars(self) -> str:
        """获取星级评分"""
        stars = int(self.total_score / 20)
        return "⭐" * min(stars, 5)


@dataclass
class RiskAssessment:
    """风险评估"""
    risk_level: str              # low/medium/high
    risk_score: float            # 风险得分 0-100
    
    # 各项指标
    trading_days: int = 0        # 已炒作天数
    leader_return: float = 0     # 龙头涨幅%
    capital_divergence: float = 0  # 资金分化程度
    sentiment_turning_point: bool = False  # 舆论热度拐点
    
    # 风险详情
    risk_factors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def get_stars(self) -> str:
        """获取星级评分"""
        risk_stars = {5: "低风险 ⭐⭐⭐⭐⭐", 4: "较低风险 ⭐⭐⭐⭐", 
                     3: "中等风险 ⭐⭐⭐", 2: "较高风险 ⭐⭐", 1: "高风险 ⭐"}
        return risk_stars.get(min(self.risk_score // 20, 5), "未知")


@dataclass
class Theme:
    """题材数据模型"""
    name: str                    # 题材名称
    keywords: List[str]          # 关键词
    related_sectors: List[str]   # 相关板块
    sentiment: str = "positive"   # 情绪: positive, negative, neutral
    
    # 分析结果
    stage: ThemeStage = ThemeStage.UNKNOWN
    catalysts: List[Catalyst] = field(default_factory=list)
    news_count: int = 0         # 相关新闻数量
    heat_score: float = 0.0    # 热度得分 0-100
    confidence: float = 0.0     # 置信度 0-1
    
    # 新增评估
    credibility: CredibilityAssessment = None  # 可信度评估
    risk: RiskAssessment = None              # 风险评估
    
    # 龙头股信息
    leader_stocks: List[str] = field(default_factory=list)
    following_stocks: List[str] = field(default_factory=list)
    
    # 时间信息
    first_appearance: datetime = None
    last_update: datetime = field(default_factory=datetime.now)
    
    # 元信息
    sources: List[str] = field(default_factory=list)
    related_news: List[str] = field(default_factory=list)
    
    # 题材类型
    theme_type: str = ""         # technology/policy/event/cycle
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        d = asdict(self)
        d['stage'] = self.stage.value
        d['catalysts'] = [c.to_dict() if isinstance(c, Catalyst) else c for c in self.catalysts]
        if self.first_appearance:
            d['first_appearance'] = self.first_appearance.isoformat()
        d['last_update'] = self.last_update.isoformat()
        if self.credibility:
            d['credibility'] = asdict(self.credibility)
        if self.risk:
            d['risk'] = asdict(self.risk)
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Theme':
        """从字典创建"""
        d['stage'] = ThemeStage(d.get('stage', 'unknown'))
        if d.get('first_appearance'):
            d['first_appearance'] = datetime.fromisoformat(d['first_appearance'])
        d['last_update'] = datetime.fromisoformat(d['last_update'])
        
        catalysts = []
        for c in d.get('catalysts', []):
            if isinstance(c, dict):
                c['expected_date'] = datetime.fromisoformat(c['expected_date'])
                catalysts.append(Catalyst(**c))
            else:
                catalysts.append(c)
        d['catalysts'] = catalysts
        
        # 可信度评估
        if d.get('credibility'):
            d['credibility'] = CredibilityAssessment(**d['credibility'])
        
        # 风险评估
        if d.get('risk'):
            d['risk'] = RiskAssessment(**d['risk'])
        
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ThemeAnalyzer:
    """
    题材分析器
    
    功能：
    - 从新闻中提取题材
    - 判断题材阶段
    - 识别催化剂和时间点
    - 计算热度得分
    - 评估可信度
    - 评估风险
    """
    
    # 来源权威性配置
    SOURCE_AUTHORITY = {
        'official': ['新华社', '人民日报', '央视', '中国政府网'],  # 1.0
        'authoritative': ['上海证券报', '中国证券报', '证券时报', '第一财经'],  # 0.9
        'professional': ['东方财富网', '同花顺', '雪球', 'Wind'],  # 0.8
        'industry': ['汽车之家', '盖世汽车', 'OFweek'],  # 0.7
        'self_media': ['微博', '微信公众号', '今日头条'],  # 0.5
    }
    
    # 政策级别配置
    POLICY_LEVEL_SCORES = {
        '国务院': 100, '发改委': 85, '工信部': 80, '财政部': 80,
        '证监会': 75, '银保监会': 75, '科技部': 70, '地方政府': 50
    }
    
    # 风险关键词
    RISK_KEYWORDS = [
        '减持', '退市', 'ST', '爆雷', '造假', '欺诈', '违规',
        '处罚', '立案', '问询', '澄清', '否认', '业绩亏损'
    ]
    
    # 炒作预警关键词
    SPECULATION_KEYWORDS = [
        '妖股', '连板', '疯狂', '炒作', '全民', '接棒', '补涨'
    ]
    
    def __init__(self, keywords_path: str = None):
        """
        初始化分析器
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载关键词配置
        if keywords_path is None:
            keywords_path = Path(__file__).parent.parent / "config" / "keywords.yaml"
        
        with open(keywords_path, 'r', encoding='utf-8') as f:
            self.keywords_config = yaml.safe_load(f)
        
        self.theme_keywords = self.keywords_config.get('theme_keywords', {})
        self.catalyst_keywords = self.keywords_config.get('catalyst_keywords', {})
        self.source_authority = self.keywords_config.get('source_authority', {})
        
        # 题材记录存储
        self.themes_dir = Path(__file__).parent.parent / "data" / "themes"
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        
        # 已知的题材字典
        self.known_themes: Dict[str, Theme] = {}
        self._load_themes()
    
    def _load_themes(self):
        """加载已记录的题材"""
        for theme_file in self.themes_dir.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    theme = Theme.from_dict(data)
                    self.known_themes[theme.name] = theme
            except Exception as e:
                self.logger.warning(f"加载题材失败 {theme_file}: {e}")
    
    def _save_theme(self, theme: Theme):
        """保存题材到文件"""
        theme_file = self.themes_dir / f"{theme.name}.json"
        try:
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存题材失败 {theme.name}: {e}")
    
    def extract_themes(self, news_list: List[Any]) -> List[Theme]:
        """
        从新闻列表中提取题材
        """
        # 按题材分组统计
        theme_news: Dict[str, List] = {name: [] for name in self.theme_keywords.keys()}
        
        for news in news_list:
            text = f"{news.title} {news.content}".lower()
            
            for theme_name, config in self.theme_keywords.items():
                keywords = config.get('keywords', [])
                for kw in keywords:
                    if kw.lower() in text:
                        theme_news[theme_name].append(news)
                        break
        
        # 创建或更新题材
        themes = []
        for theme_name, news_items in theme_news.items():
            if not news_items:
                continue
            
            theme = self._create_or_update_theme(theme_name, news_items)
            themes.append(theme)
        
        # 按热度排序
        themes.sort(key=lambda t: t.heat_score, reverse=True)
        
        return themes
    
    def _create_or_update_theme(self, name: str, news_list: List[Any]) -> Theme:
        """创建或更新题材"""
        config = self.theme_keywords.get(name, {})
        
        if name in self.known_themes:
            # 更新现有题材
            theme = self.known_themes[name]
            theme.news_count += len(news_list)
            theme.last_update = datetime.now()
            
            # 更新新闻关联
            for news in news_list:
                if hasattr(news, 'id') and news.id not in theme.related_news:
                    theme.related_news.append(news.id)
            
            # 更新来源
            for news in news_list:
                if hasattr(news, 'source') and news.source not in theme.sources:
                    theme.sources.append(news.source)
        else:
            # 创建新题材
            theme = Theme(
                name=name,
                keywords=config.get('keywords', []),
                related_sectors=config.get('related_sectors', []),
                sentiment=config.get('sentiment', 'positive'),
                news_count=len(news_list),
                first_appearance=datetime.now(),
                theme_type=config.get('theme_type', 'general')
            )
            
            for news in news_list:
                if hasattr(news, 'id'):
                    theme.related_news.append(news.id)
                if hasattr(news, 'source'):
                    theme.sources.append(news.source)
        
        # 计算热度得分
        theme.heat_score = self._calculate_heat_score(theme, news_list)
        
        # 判断阶段
        theme.stage = self.classify_stage(theme)
        
        # 识别催化剂
        theme.catalysts = self.find_catalyst(theme, news_list)
        
        # 新增：可信度评估
        theme.credibility = self.assess_credibility(name, news_list)
        
        # 新增：风险评估
        theme.risk = self.assess_risk(theme, news_list)
        
        # 保存
        self.known_themes[name] = theme
        self._save_theme(theme)
        
        return theme
    
    def _calculate_heat_score(self, theme: Theme, news_list: List[Any]) -> float:
        """
        计算题材热度得分
        
        考虑因素：
        - 新闻数量
        - 新闻时效性
        - 来源权重
        - 催化剂强度
        - 可信度加成
        """
        base_score = min(theme.news_count * 5, 40)  # 基础分，最多40分
        
        # 时效性加分
        recent_count = 0
        for news in news_list:
            if hasattr(news, 'publish_time'):
                age_hours = (datetime.now() - news.publish_time).total_seconds() / 3600
                if age_hours < 24:
                    recent_count += 1
                    if age_hours < 6:
                        base_score += 5
                    elif age_hours < 12:
                        base_score += 3
                    elif age_hours < 24:
                        base_score += 1
        
        # 来源权重加成
        authority_bonus = 0
        for news in news_list:
            if hasattr(news, 'source'):
                authority_bonus += self._get_source_authority(news.source)
        base_score += min(authority_bonus / len(news_list) * 10, 20) if news_list else 0
        
        # 催化剂加成
        if theme.catalysts:
            catalyst_bonus = sum(
                c.confidence * 10 * (2 if c.impact_level == 'high' else 1)
                for c in theme.catalysts
            )
            base_score += min(catalyst_bonus, 20)
        
        # 可信度加成
        if theme.credibility:
            base_score += theme.credibility.total_score * 0.1
        
        return min(base_score, 100)
    
    def _get_source_authority(self, source: str) -> float:
        """获取来源权威性得分"""
        source_lower = source.lower()
        
        for category, sources in self.SOURCE_AUTHORITY.items():
            for s in sources:
                if s in source:
                    scores = {'official': 1.0, 'authoritative': 0.9, 
                             'professional': 0.8, 'industry': 0.7, 'self_media': 0.5}
                    return scores.get(category, 0.5)
        
        return 0.5
    
    def classify_stage(self, theme: Theme) -> ThemeStage:
        """
        判断题材阶段
        
        萌芽期: 首次出现、技术突破、新产品
        爆发期: 涨停、暴涨、大量报道
        炒作期: 连板、妖股、全民炒股
        退潮期: 回落、分化、滞涨
        消亡期: 证伪、过时
        """
        # 获取新闻文本
        theme_file = self.themes_dir / f"{theme.name}.json"
        if theme_file.exists():
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
            except:
                old_data = {}
        else:
            old_data = {}
        
        # 判断逻辑
        if theme.news_count <= 3 and theme.first_appearance:
            days_since = (datetime.now() - theme.first_appearance).days
            if days_since <= 3:
                return ThemeStage.GERMINATION
        
        # 检查关键词
        keywords_text = " ".join(theme.keywords)
        
        germination_kw = ['首次', '突破', '首款', '首创', '新产品']
        eruption_kw = ['涨停', '暴涨', '爆发', '引爆', '全民']
        speculation_kw = ['妖股', '连板', '疯狂', '炒作', '补涨']
        cooldown_kw = ['回落', '回调', '分化', '退潮', '滞涨']
        dead_kw = ['消亡', '过时', '证伪', '否认', '澄清']
        
        # 阶段判断
        for kw in dead_kw:
            if kw in keywords_text:
                return ThemeStage.DEAD
        
        for kw in cooldown_kw:
            if kw in keywords_text:
                return ThemeStage.COOLDOWN
        
        for kw in speculation_kw:
            if kw in keywords_text:
                return ThemeStage.SPECULATION
        
        for kw in eruption_kw:
            if kw in keywords_text:
                return ThemeStage.ERUPTION
        
        for kw in germination_kw:
            if kw in keywords_text:
                return ThemeStage.GERMINATION
        
        # 基于时间的默认判断
        if theme.news_count < 5:
            return ThemeStage.GERMINATION
        elif theme.news_count < 20:
            return ThemeStage.ERUPTION
        else:
            return ThemeStage.SPECULATION
    
    def find_catalyst(self, theme: Theme, news_list: List[Any]) -> List[Catalyst]:
        """识别催化剂"""
        catalysts = []
        text = " ".join(f"{news.title} {news.content}" for news in news_list)
        
        # 政策类催化剂
        policy_keywords = ['国务院', '发改委', '工信部', '财政部', '政策', '规划', '意见']
        for kw in policy_keywords:
            if kw in text:
                catalysts.append(Catalyst(
                    type='policy',
                    title=f"政策催化剂：{kw}",
                    description="政策发布预期",
                    expected_date=datetime.now() + timedelta(days=random.randint(7, 30)),
                    confidence=0.8,
                    impact_level='high',
                    catalyst_level='中期'
                ))
                break
        
        # 产品类催化剂
        product_keywords = ['发布', '发布会', '上市', '预售', '首发']
        for kw in product_keywords:
            if kw in text:
                catalysts.append(Catalyst(
                    type='product',
                    title=f"产品催化剂：{kw}",
                    description="产品发布预期",
                    expected_date=datetime.now() + timedelta(days=random.randint(1, 14)),
                    confidence=0.7,
                    impact_level='medium',
                    catalyst_level='短期'
                ))
                break
        
        # 技术类催化剂
        tech_keywords = ['量产', '突破', '测试', '验证']
        for kw in tech_keywords:
            if kw in text:
                catalysts.append(Catalyst(
                    type='technology',
                    title=f"技术催化剂：{kw}",
                    description="技术进展预期",
                    expected_date=datetime.now() + timedelta(days=random.randint(30, 90)),
                    confidence=0.6,
                    impact_level='medium',
                    catalyst_level='长期'
                ))
                break
        
        return catalysts[:3]  # 最多返回3个催化剂
    
    def assess_credibility(self, theme_name: str, news_list: List[Any]) -> CredibilityAssessment:
        """评估题材可信度"""
        text = " ".join(f"{news.title} {news.content}" for news in news_list)
        
        # 政策级别得分
        policy_score = 50
        for level, score in self.POLICY_LEVEL_SCORES.items():
            if level in text:
                policy_score = max(policy_score, score)
                break
        
        # 媒体权威性得分
        authority_scores = []
        for news in news_list:
            authority_scores.append(self._get_source_authority(getattr(news, 'source', '')))
        media_score = sum(authority_scores) / len(authority_scores) * 100 if authority_scores else 50
        
        # 信息一致性得分（多源验证）
        sources = [getattr(news, 'source', '') for news in news_list]
        unique_sources = len(set(s for s in sources if s))
        consistency_score = min(unique_sources * 20, 100)
        
        # 时效性得分
        freshness_score = 50
        for news in news_list:
            if hasattr(news, 'publish_time'):
                age_hours = (datetime.now() - news.publish_time).total_seconds() / 3600
                if age_hours < 24:
                    freshness_score = 100
                elif age_hours < 72:
                    freshness_score = 75
                elif age_hours < 168:
                    freshness_score = 50
                break
        
        # 总分
        total_score = (policy_score * 0.4 + media_score * 0.3 + 
                      consistency_score * 0.15 + freshness_score * 0.15)
        
        return CredibilityAssessment(
            total_score=total_score,
            policy_level_score=policy_score,
            media_authority_score=media_score,
            consistency_score=consistency_score,
            freshness_score=freshness_score,
            policy_level=self._get_policy_level_text(policy_score),
            media_sources=list(set(sources))[:5],
            validation_count=unique_sources
        )
    
    def _get_policy_level_text(self, score: float) -> str:
        """获取政策级别文本"""
        if score >= 90:
            return "国家级（国务院）"
        elif score >= 75:
            return "部委级"
        elif score >= 60:
            return "地方级"
        else:
            return "未明确"
    
    def assess_risk(self, theme: Theme, news_list: List[Any]) -> RiskAssessment:
        """评估题材风险"""
        text = " ".join(f"{news.title} {news.content}" for news in news_list)
        
        # 已炒作天数
        trading_days = 0
        if theme.first_appearance:
            trading_days = (datetime.now() - theme.first_appearance).days
        
        # 龙头涨幅（从新闻中提取）
        leader_return = 0
        numbers = re.findall(r'(\d+(?:\.\d+)?)%', text)
        for num_str in numbers:
            try:
                num = float(num_str)
                if 0 < num <= 50:
                    leader_return = max(leader_return, num)
            except:
                pass
        
        # 资金分化程度
        divergence = 0
        if any(kw in text for kw in ['分化', '个股涨跌不一', '严重分化']):
            divergence = 0.7
        elif any(kw in text for kw in ['回落', '回调', '炸板']):
            divergence = 0.8
        
        # 舆论热度拐点
        turning_point = any(kw in text for kw in ['回落', '退潮', '滞涨', '降温', '监管'])
        
        # 风险因素
        risk_factors = []
        for risk_kw in self.RISK_KEYWORDS:
            if risk_kw in text:
                risk_factors.append(risk_kw)
        
        # 风险等级
        risk_score = 50
        if trading_days > 30:
            risk_score += 20
        elif trading_days > 14:
            risk_score += 10
        
        if leader_return > 30:
            risk_score += 20
        elif leader_return > 15:
            risk_score += 10
        
        if divergence > 0.5:
            risk_score += 15
        
        if turning_point:
            risk_score += 20
        
        risk_score = min(risk_score, 100)
        
        # 风险级别
        if risk_score < 35:
            risk_level = "low"
        elif risk_score < 60:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        # 预警信息
        warnings = []
        if risk_level == "high":
            warnings.append("⚠️ 高风险，注意止损")
        if divergence > 0.5:
            warnings.append("⚠️ 资金出现分化")
        if turning_point:
            warnings.append("⚠️ 热度出现拐点信号")
        if leader_return > 30:
            warnings.append("⚠️ 龙头涨幅过大，注意回调风险")
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            trading_days=trading_days,
            leader_return=leader_return,
            capital_divergence=divergence,
            sentiment_turning_point=turning_point,
            risk_factors=risk_factors,
            warnings=warnings
        )
    
    def _classify_stage(self, theme: Theme) -> ThemeStage:
        """分类阶段（兼容方法）"""
        return self.classify_stage(theme)


import random
