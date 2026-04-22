# -*- coding: utf-8 -*-
"""
题材分析引擎
从新闻中提取、分析题材，判断题材阶段和催化剂
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
    def color(self) -> str:
        """阶段颜色（用于Telegram消息）"""
        colors = {
            "unknown": "⚪",
            "germination": "🟢",
            "eruption": "🔵",
            "speculation": "🟡",
            "cooldown": "🟠",
            "dead": "🔴",
        }
        return colors.get(self.value, "⚪")


@dataclass
class Catalyst:
    """催化剂信息"""
    type: str                    # 类型: policy, commercial, technology, event
    title: str                   # 标题
    description: str             # 描述
    expected_date: datetime      # 预期时间
    confidence: float = 0.5      # 置信度 0-1
    impact_level: str = "medium" # 影响级别: high, medium, low
    
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
class Theme:
    """题材数据模型"""
    name: str                    # 题材名称
    keywords: List[str]          # 关键词
    related_sectors: List[str]  # 相关板块
    sentiment: str = "positive"  # 情绪: positive, negative, neutral
    
    # 分析结果
    stage: ThemeStage = ThemeStage.UNKNOWN
    catalysts: List[Catalyst] = field(default_factory=list)
    news_count: int = 0         # 相关新闻数量
    heat_score: float = 0.0    # 热度得分 0-100
    confidence: float = 0.0     # 置信度 0-1
    
    # 龙头股信息
    leader_stocks: List[str] = field(default_factory=list)  # 股票代码列表
    following_stocks: List[str] = field(default_factory=list)
    
    # 时间信息
    first_appearance: datetime = None
    last_update: datetime = field(default_factory=datetime.now)
    
    # 元信息
    sources: List[str] = field(default_factory=list)  # 新闻来源
    related_news: List[str] = field(default_factory=list)  # 相关新闻ID
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        d = asdict(self)
        d['stage'] = self.stage.value
        d['catalysts'] = [c.to_dict() if isinstance(c, Catalyst) else c for c in self.catalysts]
        if self.first_appearance:
            d['first_appearance'] = self.first_appearance.isoformat()
        d['last_update'] = self.last_update.isoformat()
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
        
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ThemeAnalyzer:
    """
    题材分析器
    
    功能：
    - 从新闻中提取题材
    - 判断题材阶段
    - 识别催化剂和时间点
    - 计算热度得分
    """
    
    def __init__(self, keywords_path: str = None):
        """
        初始化分析器
        
        Args:
            keywords_path: 关键词配置文件路径
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载关键词配置
        if keywords_path is None:
            keywords_path = Path(__file__).parent.parent / "config" / "keywords.yaml"
        
        with open(keywords_path, 'r', encoding='utf-8') as f:
            self.keywords_config = yaml.safe_load(f)
        
        self.theme_keywords = self.keywords_config.get('theme_keywords', {})
        self.catalyst_keywords = self.keywords_config.get('catalyst_keywords', {})
        
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
        
        Args:
            news_list: 新闻列表
            
        Returns:
            提取到的题材列表
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
        """
        base_score = min(theme.news_count * 5, 40)  # 基础分，最多40分
        
        # 时效性加分
        recent_count = 0
        for news in news_list:
            if hasattr(news, 'publish_time'):
                age_hours = (datetime.now() - news.publish_time).total_seconds() / 3600
                if age_hours < 24:
                    recent_count += 1
        recency_score = min(recent_count * 8, 30)  # 时效分，最多30分
        
        # 来源权重分
        source_weights = {
            '财联社电报': 3,
            '同花顺资讯': 2,
            '东方财富': 2,
            '证券时报': 2,
            '第一财经': 1.5,
            '新浪财经': 1,
            '中国政府网': 3,
            '发改委': 3,
            '工信部': 3,
        }
        
        source_score = 0
        for news in news_list:
            if hasattr(news, 'source'):
                weight = source_weights.get(news.source, 1)
                source_score += weight * 2
        source_score = min(source_score, 15)  # 来源分，最多15分
        
        # 催化剂分
        catalyst_score = min(len(theme.catalysts) * 5, 15)  # 催化剂分，最多15分
        
        total_score = base_score + recency_score + source_score + catalyst_score
        return min(total_score, 100)
    
    def classify_stage(self, theme: Theme) -> ThemeStage:
        """
        判断题材阶段
        
        阶段判断依据：
        - 萌芽期：首次出现，新闻量少
        - 爆发期：新闻量快速增加，多源报道
        - 炒作期：相关股票涨停，出现概念炒作
        - 退潮期：新闻量下降，热度降低
        - 消亡期：长时间无相关新闻
        """
        if theme.news_count == 0:
            return ThemeStage.UNKNOWN
        
        now = datetime.now()
        
        # 判断是否为新题材
        if theme.first_appearance:
            days_since_first = (now - theme.first_appearance).days
            
            if days_since_first <= 3:
                # 3天内的新题材
                if theme.news_count >= 5:
                    return ThemeStage.ERUPTION
                else:
                    return ThemeStage.GERMINATION
            elif days_since_first <= 7:
                # 一周内的题材
                if theme.heat_score >= 70:
                    return ThemeStage.SPECULATION
                else:
                    return ThemeStage.ERUPTION
            elif days_since_first <= 14:
                # 两周内的题材
                if theme.heat_score >= 60:
                    return ThemeStage.SPECULATION
                else:
                    return ThemeStage.COOLDOWN
            else:
                # 超过两周
                if theme.heat_score >= 50:
                    return ThemeStage.COOLDOWN
                else:
                    return ThemeStage.DEAD
        
        # 无首次出现时间
        if theme.news_count <= 3:
            return ThemeStage.GERMINATION
        elif theme.news_count <= 10:
            return ThemeStage.ERUPTION
        elif theme.heat_score >= 70:
            return ThemeStage.SPECULATION
        else:
            return ThemeStage.COOLDOWN
    
    def find_catalyst(self, theme: Theme, news_list: List[Any]) -> List[Catalyst]:
        """
        从新闻中识别催化剂
        
        Args:
            theme: 题材
            news_list: 相关新闻列表
            
        Returns:
            催化剂列表
        """
        catalysts = []
        existing_titles = {c.title for c in theme.catalysts}
        
        # 合并所有催化剂关键词
        all_catalyst_keywords = []
        for category, keywords in self.catalyst_keywords.items():
            all_catalyst_keywords.extend(keywords)
        
        for news in news_list:
            text = f"{news.title} {news.content}"
            
            # 检查是否包含催化剂关键词
            for kw in all_catalyst_keywords:
                if kw in text:
                    catalyst_type = self._identify_catalyst_type(text)
                    expected_date = self._extract_date(text, news.publish_time)
                    
                    # 避免重复
                    title = self._generate_catalyst_title(news, kw)
                    if title not in existing_titles:
                        catalyst = Catalyst(
                            type=catalyst_type,
                            title=title,
                            description=text[:200],
                            expected_date=expected_date,
                            confidence=0.6,
                            impact_level=self._estimate_impact(text)
                        )
                        catalysts.append(catalyst)
                        existing_titles.add(title)
                    break
        
        return catalysts
    
    def _identify_catalyst_type(self, text: str) -> str:
        """识别催化剂类型"""
        policy_keywords = ['政策', '国务院', '发改委', '工信部', '标准', '规划', '通知']
        commercial_keywords = ['发布', '上市', '量产', '订单', '签约', '量产']
        technology_keywords = ['突破', '研发', '首款', '首创', '技术']
        event_keywords = ['峰会', '论坛', '博览会', '发布会', '展会', '会议']
        
        for kw in policy_keywords:
            if kw in text:
                return 'policy'
        for kw in commercial_keywords:
            if kw in text:
                return 'commercial'
        for kw in technology_keywords:
            if kw in text:
                return 'technology'
        for kw in event_keywords:
            if kw in text:
                return 'event'
        
        return 'unknown'
    
    def _extract_date(self, text: str, default_date: datetime) -> datetime:
        """从文本中提取日期"""
        # 日期模式
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})/(\d{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                        if len(year) == 4:
                            return datetime(int(year), int(month), int(day))
                        else:
                            # 假设是今年
                            now = datetime.now()
                            return datetime(now.year, int(year), int(month))
                except ValueError:
                    continue
        
        # 返回默认日期+7天（假设一周后）
        return default_date + timedelta(days=7)
    
    def _generate_catalyst_title(self, news: Any, keyword: str) -> str:
        """生成催化剂标题"""
        title = news.title if hasattr(news, 'title') else str(news)
        return f"{keyword}: {title[:50]}"
    
    def _estimate_impact(self, text: str) -> str:
        """估计影响级别"""
        high_impact = ['重磅', '重大', '国家级', '全球', '首创', '颠覆']
        medium_impact = ['重要', '试点', '推广', '扩大']
        
        for kw in high_impact:
            if kw in text:
                return 'high'
        for kw in medium_impact:
            if kw in text:
                return 'medium'
        return 'low'
    
    def analyze_news_sentiment(self, news_list: List[Any]) -> Dict[str, float]:
        """
        分析新闻情绪
        
        Returns:
            {题材名: 情绪值(-1到1)}
        """
        sentiments = {}
        
        for theme_name, config in self.theme_keywords.items():
            related_news = []
            keywords = config.get('keywords', [])
            
            for news in news_list:
                text = f"{news.title} {news.content}".lower()
                for kw in keywords:
                    if kw.lower() in text:
                        related_news.append(news)
                        break
            
            if related_news:
                # 简单情绪分析
                positive_words = ['利好', '突破', '大涨', '爆发', '增长', '创新', '领先']
                negative_words = ['利空', '下跌', '风险', '亏损', '问题', '违规']
                
                score = 0
                for news in related_news:
                    text = f"{news.title} {news.content}"
                    for pw in positive_words:
                        if pw in text:
                            score += 1
                    for nw in negative_words:
                        if nw in text:
                            score -= 1
                
                sentiments[theme_name] = score / max(len(related_news), 1)
        
        return sentiments
    
    def get_theme_summary(self, theme: Theme) -> str:
        """生成题材摘要"""
        stage = theme.stage
        
        summary_parts = [
            f"📊 题材: {theme.name}",
            f"📍 阶段: {stage.color}{stage.description}",
            f"🔥 热度: {theme.heat_score:.0f}",
            f"📰 新闻: {theme.news_count}条",
        ]
        
        if theme.catalysts:
            summary_parts.append("⏰ 催化剂:")
            for cat in theme.catalysts[:3]:
                days = cat.days_until()
                date_str = cat.expected_date.strftime("%m-%d")
                summary_parts.append(f"  • {cat.title[:30]} ({date_str}, {days}天后)")
        
        if theme.leader_stocks:
            summary_parts.append(f"🐉 龙头: {', '.join(theme.leader_stocks[:3])}")
        
        return "\n".join(summary_parts)


# 示例用法
if __name__ == "__main__":
    from collector import NewsCollector, News
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建分析器
    analyzer = ThemeAnalyzer()
    
    # 创建测试新闻
    test_news = [
        News(
            id="test1",
            title="低空经济政策重磅出台 万丰奥威涨停",
            content="国务院发布低空空域管理改革政策，低空经济概念爆发，万丰奥威等多股涨停",
            source="财联社",
            url="http://test.com",
            publish_time=datetime.now(),
            category="policy"
        ),
        News(
            id="test2",
            title="eVTOL商业化加速 飞行汽车最快明年量产",
            content="多家企业宣布eVTOL项目进展，商业化进程超预期",
            source="同花顺",
            url="http://test.com",
            publish_time=datetime.now(),
            category="finance"
        ),
    ]
    
    # 提取题材
    themes = analyzer.extract_themes(test_news)
    
    for theme in themes:
        print(analyzer.get_theme_summary(theme))
        print("-" * 50)
