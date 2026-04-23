# -*- coding: utf-8 -*-
"""
Event Agent - 事件策划师（升级版）
权重: 1.1
功能：
- 事件影响力分级（S/A/B/C）
- 事件确定性评估
- 市场预期差分析
- 输出：事件级别、确定性、预期差
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EventLevel(Enum):
    """事件影响力等级"""
    S_LEVEL = ("S级", 100, "super_major", "超级事件", "对市场有决定性影响")
    A_LEVEL = ("A级", 80, "major", "重大事件", "对特定板块有重大影响")
    B_LEVEL = ("A级", 60, "important", "重要事件", "对局部有影响")
    C_LEVEL = ("B级", 40, "general", "一般事件", "影响有限")
    
    def __init__(self, label, score, code, name, description):
        self._label = label
        self._score = score
        self._code = code
        self._name = name
        self.description = description
    
    @property
    def label(self):
        return self._label
    
    @property
    def score(self):
        return self._score
    
    @property
    def name_code(self):
        return self._name


class CertaintyLevel(Enum):
    """确定性等级"""
    CONFIRMED = ("已确认", 1.0, "official_confirmed", "官方宣布，确定无疑")
    HIGH = ("大概率", 0.85, "high_prob", "多项证据支持")
    MEDIUM = ("中等", 0.65, "medium_prob", "部分证据支持")
    LOW = ("小概率", 0.45, "low_prob", "传闻或预期")
    UNCERTAIN = ("不确定", 0.3, "uncertain", "仅为猜测")
    
    def __init__(self, label, prob_value, code, description):
        self.label = label
        self._prob_value = prob_value
        self._code = code
        self.description = description
    
    @property
    def value(self):
        return self._prob_value


@dataclass
class EventInsight:
    """事件洞察"""
    event_name: str
    event_title: str
    source: str
    
    # 事件等级
    level: EventLevel
    level_score: int
    
    # 确定性
    certainty: CertaintyLevel
    certainty_value: float
    
    # 时间
    expected_date: datetime
    time_confidence: str
    
    # 预期差
    expectation_gap: float              # -1到1，正值表示超预期
    market_expectation: str             # 市场当前预期
    actual_expectation: str              # 实际/潜在预期
    gap_direction: str                  # 超预期/低于预期/符合预期
    
    # 影响分析
    affected_themes: List[str]          # 受影响题材
    affected_sectors: List[str]         # 受影响行业
    impact_scope: str                   # 影响范围
    
    # 事件详情
    event_type: str                     # 类型：发布会/财报/政策/业绩
    description: str = ""
    
    # 历史参考
    historical_similar: List[str] = field(default_factory=list)


@dataclass
class ExpectationGapAnalysis:
    """预期差分析"""
    is_positive_gap: bool               # 是否超预期
    gap_magnitude: float                # 差距幅度
    trading_implication: str           # 交易含义
    risk_factors: List[str]             # 风险因素


class EventAgent:
    """事件策划师 - 深度事件分析"""
    
    # 事件级别关键词
    LEVEL_KEYWORDS = {
        EventLevel.S_LEVEL: [
            '全国', '国务院', '中央', '重大政策', '历史性', '划时代',
            '颠覆性', '诺贝尔', '全球首个', '世界首例'
        ],
        EventLevel.A_LEVEL: [
            '突破', '重大进展', '重磅', '首次', '首款', '首创',
            '重要', '显著', '大幅', '涨停', '暴涨'
        ],
        EventLevel.B_LEVEL: [
            '消息', '传闻', '预期', '有望', '可能', '计划'
        ],
        EventLevel.C_LEVEL: [
            '一般', '普通', '常规', '例行'
        ]
    }
    
    # 确定性关键词
    CERTAINTY_KEYWORDS = {
        CertaintyLevel.CONFIRMED: ['官宣', '正式', '确定', '宣布', '发布', '落实'],
        CertaintyLevel.HIGH: ['预计', '大概率', '很可能', '有望', '基本确定'],
        CertaintyLevel.MEDIUM: ['预期', '可能', '或将', '有望', '计划'],
        CertaintyLevel.LOW: ['传闻', '据传', '市场传闻', '猜测'],
        CertaintyLevel.UNCERTAIN: ['不确定', '未知', '待定']
    }
    
    # 事件类型关键词
    EVENT_TYPES = {
        'product_launch': ['发布', '发布会', '上市', '发售', '首发', '新品'],
        'policy': ['政策', '规划', '意见', '通知', '办法', '规定'],
        'financial': ['财报', '业绩', '营收', '利润', '超预期', '不及预期'],
        'technology': ['技术', '突破', '量产', '研发', '专利'],
        'cooperation': ['合作', '签约', '战略', '联手', '并购'],
        'certificate': ['认证', '获批', '通过', '验收', '许可']
    }
    
    # 超预期/低于预期关键词
    EXPECTATION_KEYWORDS = {
        'positive': ['超预期', '大超预期', '大幅超过', '远超', '显著高于', '超预期增长'],
        'negative': ['不及预期', '低于预期', '远低于', '大幅低于', '低于', '令人失望'],
        'neutral': ['符合预期', '符合', '基本符合']
    }
    
    # 历史同类事件
    HISTORICAL_EVENTS = {
        '苹果发布会': ['iPhone15发布', 'iPhone14发布', 'WWDC23'],
        '华为发布会': ['Mate60发布', 'Mate50发布'],
        'AI大模型': ['ChatGPT发布', 'GPT4发布', 'Claude发布', '文心一言发布'],
        '固态电池': ['QuantumScape产品', '丰田固态电池计划'],
        '新能源汽车政策': ['购置税减免延续', '补贴政策']
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.1
        self.name = "事件策划师"
    
    def analyze(self, news_list: List[Any]) -> List[EventInsight]:
        """分析事件信息"""
        insights = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            if not self._is_event_news(text):
                continue
            
            insight = self._extract_event(news, text)
            if insight:
                insights.append(insight)
        
        # 按等级和确定性排序
        insights.sort(key=lambda x: (x.level_score, x.certainty_value), reverse=True)
        
        return insights
    
    def _is_event_news(self, text: str) -> bool:
        """判断是否为事件新闻"""
        event_markers = [
            '发布', '上市', '会议', '大会', '论坛', '展览',
            '签约', '合作', '财报', '业绩', '政策', '规划',
            '认证', '获批', '突破', '重大'
        ]
        return any(marker in text for marker in event_markers)
    
    def _extract_event(self, news: Any, text: str) -> Optional[EventInsight]:
        """提取事件信息"""
        title = getattr(news, 'title', '')
        source = getattr(news, 'source', '')
        publish_time = getattr(news, 'publish_time', datetime.now())
        
        # 判断事件级别
        level = self._determine_level(text)
        level_score = level.score
        
        # 判断确定性
        certainty = self._determine_certainty(text)
        
        # 提取事件类型
        event_type = self._determine_event_type(text)
        
        # 预测时间
        expected_date, time_confidence = self._predict_event_time(text, publish_time)
        
        # 分析预期差
        gap_analysis = self._analyze_expectation_gap(text)
        
        # 影响范围
        affected_themes = self._extract_affected_themes(text)
        affected_sectors = self._extract_affected_sectors(text)
        
        # 历史参考
        historical = self._find_historical_similar(title)
        
        return EventInsight(
            event_name=title[:50],
            event_title=title,
            source=source,
            level=level,
            level_score=level_score,
            certainty=certainty,
            certainty_value=certainty.value,
            expected_date=expected_date,
            time_confidence=time_confidence,
            expectation_gap=gap_analysis.gap_magnitude,
            market_expectation=gap_analysis.trading_implication,
            actual_expectation=gap_analysis.trading_implication,
            gap_direction='超预期' if gap_analysis.is_positive_gap else ('低于预期' if gap_analysis.gap_magnitude < -0.3 else '符合预期'),
            affected_themes=affected_themes,
            affected_sectors=affected_sectors,
            impact_scope=self._determine_impact_scope(level, affected_sectors),
            event_type=event_type,
            description=self._generate_description(event_type, level, certainty),
            historical_similar=historical
        )
    
    def _determine_level(self, text: str) -> EventLevel:
        """判断事件级别"""
        scores = {level: 0 for level in EventLevel}
        
        for level, keywords in self.LEVEL_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[level] += 1
        
        # 加权计算
        for level, score in scores.items():
            scores[level] = score * level.score / 20
        
        max_level = max(scores.items(), key=lambda x: x[1])
        if max_level[1] == 0:
            return EventLevel.C_LEVEL
        
        for level, score in scores.items():
            if score == max_level[1]:
                return level
        
        return EventLevel.B_LEVEL
    
    def _determine_certainty(self, text: str) -> CertaintyLevel:
        """判断确定性"""
        scores = {level: 0 for level in CertaintyLevel}
        
        for level, keywords in self.CERTAINTY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[level] += 1
        
        max_level = max(scores.items(), key=lambda x: x[1])
        if max_level[1] == 0:
            return CertaintyLevel.MEDIUM
        
        for level, score in scores.items():
            if score == max_level[1]:
                return level
        
        return CertaintyLevel.MEDIUM
    
    def _determine_event_type(self, text: str) -> str:
        """判断事件类型"""
        for etype, keywords in self.EVENT_TYPES.items():
            if any(kw in text for kw in keywords):
                return etype
        return 'general'
    
    def _predict_event_time(self, text: str, base_time: datetime) -> Tuple[datetime, str]:
        """预测事件时间"""
        # 提取时间信息
        date_patterns = [
            (r'(\d+)月(\d+)日', '%m月%d日'),
            (r'(\d+)日', '%m月%d日'),
            (r'本?周([一二三四五六日])', '周%s'),
            (r'下个?月', '%m月'),
        ]
        
        for pattern, _ in date_patterns:
            match = re.search(pattern, text)
            if match:
                # 简化处理，返回估算日期
                if '日' in pattern:
                    return base_time + timedelta(days=7), "7天内"
                elif '周' in pattern:
                    return base_time + timedelta(weeks=1), "1周内"
                elif '月' in pattern:
                    return base_time + timedelta(days=30), "1月内"
        
        return base_time + timedelta(days=14), "2周内"
    
    def _analyze_expectation_gap(self, text: str) -> ExpectationGapAnalysis:
        """分析预期差"""
        gap = 0.0
        is_positive = False
        trading_imply = "符合预期，观望"
        risk_factors = []
        
        if any(kw in text for kw in self.EXPECTATION_KEYWORDS['positive']):
            gap = 0.6
            is_positive = True
            trading_imply = "超预期，积极参与"
        elif any(kw in text for kw in self.EXPECTATION_KEYWORDS['negative']):
            gap = -0.6
            is_positive = False
            trading_imply = "低于预期，谨慎"
        elif any(kw in text for kw in self.EXPECTATION_KEYWORDS['neutral']):
            gap = 0.0
            trading_imply = "符合预期，按计划操作"
        
        # 检查风险因素
        if any(kw in text for kw in ['减持', '解禁', 'ST', '退市']):
            risk_factors.append('存在减持/解禁风险')
        
        return ExpectationGapAnalysis(
            is_positive_gap=is_positive,
            gap_magnitude=gap,
            trading_implication=trading_imply,
            risk_factors=risk_factors
        )
    
    def _extract_affected_themes(self, text: str) -> List[str]:
        """提取受影响题材"""
        themes = []
        known_themes = [
            '新能源汽车', '人工智能', '半导体', '固态电池',
            '低空经济', '氢能', '脑机接口', '量子计算',
            '苹果产业链', '华为产业链', '特斯拉'
        ]
        
        for theme in known_themes:
            if theme in text:
                themes.append(theme)
        
        return themes
    
    def _extract_affected_sectors(self, text: str) -> List[str]:
        """提取受影响行业"""
        sectors = []
        known_sectors = [
            '新能源', '半导体', '电子', '汽车', '医药',
            '军工', '通信', '计算机', '消费'
        ]
        
        for sector in known_sectors:
            if sector in text:
                sectors.append(sector)
        
        return sectors
    
    def _determine_impact_scope(self, level: EventLevel, sectors: List[str]) -> str:
        """判断影响范围"""
        if level == EventLevel.S_LEVEL:
            return '全市场'
        elif level == EventLevel.A_LEVEL:
            return '多个行业'
        elif len(sectors) > 1:
            return '多个行业'
        elif sectors:
            return f'{sectors[0]}行业'
        return '局部'
    
    def _generate_description(self, event_type: str, level: EventLevel, 
                            certainty: CertaintyLevel) -> str:
        """生成事件描述"""
        type_map = {
            'product_launch': '产品发布',
            'policy': '政策事件',
            'financial': '财报业绩',
            'technology': '技术突破',
            'cooperation': '合作签约',
            'certificate': '认证获批'
        }
        
        return f"{type_map.get(event_type, '一般事件')}|{level.label}|{certainty.label}"
    
    def _find_historical_similar(self, title: str) -> List[str]:
        """查找历史同类事件"""
        similar = []
        
        for event, history in self.HISTORICAL_EVENTS.items():
            if any(keyword in title for keyword in event.split()):
                similar.extend(history)
        
        return similar[:3]
    
    def generate_event_report(self, insights: List[EventInsight]) -> str:
        """生成事件分析报告"""
        if not insights:
            return "📅 暂无重要事件"
        
        parts = ["\n📅 事件分析报告", "=" * 40]
        
        # 统计
        s_events = [e for e in insights if e.level == EventLevel.S_LEVEL]
        a_events = [e for e in insights if e.level == EventLevel.A_LEVEL]
        confirmed = [e for e in insights if e.certainty == CertaintyLevel.CONFIRMED]
        
        parts.append(f"\n📊 事件概览")
        parts.append(f"├ S级事件: {len(s_events)}个")
        parts.append(f"├ A级事件: {len(a_events)}个")
        parts.append(f"├ 已确认: {len(confirmed)}个")
        parts.append(f"└ 总计: {len(insights)}个")
        
        # 重点事件
        parts.append("\n🎯 重点事件:")
        for insight in insights[:5]:
            gap_icon = "📈" if insight.expectation_gap > 0 else ("📉" if insight.expectation_gap < 0 else "➡️")
            
            parts.append(f"\n{gap_icon} {insight.event_name[:30]}...")
            parts.append(f"   ├ 级别: {insight.level.label}")
            parts.append(f"   ├ 确定: {insight.certainty.label}")
            parts.append(f"   ├ 预期: {insight.gap_direction}")
            if insight.affected_themes:
                parts.append(f"   └ 题材: {', '.join(insight.affected_themes[:2])}")
        
        return "\n".join(parts)
