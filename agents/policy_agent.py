# -*- coding: utf-8 -*-
"""
Policy Agent - 政策解读师（升级版）
权重: 1.4
功能：
- 区分政策级别（国务院/部委/地方）
- 判断政策落地时间表
- 分析政策对产业链各环节影响
- 输出：政策级别评分、影响范围、时间线
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class PolicyLevel(Enum):
    """政策级别枚举"""
    STATE_COUNCIL = ("国务院", 100)      # 国务院/政治局
    JOINT_MINISTRIES = ("部委联合", 85)  # 多部委联合
    SINGLE_MINISTRY = ("部委级", 70)     # 单一部委
    LOCAL_GOVERNMENT = ("地方级", 50)    # 地方政府
    
    def __init__(self, label, score):
        self.label = label
        self.score = score


class ImpactScope(Enum):
    """影响范围枚举"""
    NATIONAL = ("全国", 1.0)           # 全国性影响
    INDUSTRY_WIDE = ("行业性", 0.8)     # 行业性影响
    REGIONAL = ("区域性", 0.6)          # 区域性影响
    ENTERPRISE = ("企业级", 0.4)         # 单个企业影响


@dataclass
class PolicyInsight:
    """政策洞察"""
    policy_title: str
    source: str
    publish_date: datetime
    
    # 级别评估
    level: PolicyLevel
    level_score: int              # 0-100
    
    # 影响范围
    scope: ImpactScope
    benefit_sectors: List[str]     # 受益行业
    affected_industries: List[str] # 受影响行业
    
    # 时间线
    expected_implementation: datetime  # 预期实施时间
    implementation_timeline: str     # 时间线说明
    
    # 置信度
    confidence: float             # 置信度 0-1
    
    # 产业链分析
    upstream_impact: str = ""      # 上游影响
    midstream_impact: str = ""     # 中游影响
    downstream_impact: str = ""    # 下游影响
    
    # 关键词
    policy_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'policy_title': self.policy_title,
            'source': self.source,
            'publish_date': self.publish_date.isoformat(),
            'level': self.level.label,
            'level_score': self.level_score,
            'scope': self.scope.label,
            'benefit_sectors': self.benefit_sectors,
            'confidence': self.confidence,
            'expected_implementation': self.expected_implementation.isoformat(),
            'implementation_timeline': self.implementation_timeline,
        }


class PolicyAgent:
    """政策解读师 - 深度政策分析"""
    
    # 政策级别关键词
    LEVEL_KEYWORDS = {
        PolicyLevel.STATE_COUNCIL: [
            '国务院', '国务院常务会议', '国务院办公厅', '中共中央', '政治局',
            '全国人民代表大会', '全国人大', '中央经济工作会议', '两会'
        ],
        PolicyLevel.JOINT_MINISTRIES: [
            '发改委', '工信部', '财政部', '证监会', '银保监会', '科技部', '商务部',
            '生态环境部', '交通运输部', '人民银行', '多部门', '联合', '共同'
        ],
        PolicyLevel.SINGLE_MINISTRY: [
            '工信部表示', '发改委称', '财政部指出', '证监会', '银保监会',
            '科技部', '商务部', '住建部', '自然资源部'
        ],
        PolicyLevel.LOCAL_GOVERNMENT: [
            '省政府', '市政府', '区政府', '省级', '市级', '地方', '区县'
        ]
    }
    
    # 时间线关键词
    TIMELINE_KEYWORDS = {
        'immediate': ['立即', '马上', '即刻', '当天', '3日内', '本周'],
        'short_term': ['1个月内', '30日内', '一季度', '近期', '短期'],
        'medium_term': ['6个月内', '年内', '今年', '十四五期间', '2025年'],
        'long_term': ['3年', '5年', '长期', '持续', '远期']
    }
    
    # 受益行业关键词
    BENEFIT_KEYWORDS = {
        '新能源汽车': ['新能源汽车', '电动车', '充电桩', '锂电', '动力电池', '储能'],
        '半导体': ['半导体', '芯片', '集成电路', '国产替代', '光刻机'],
        '人工智能': ['人工智能', 'AI', '大模型', '算力', '智能制造'],
        '低空经济': ['低空经济', '无人机', 'eVTOL', '通用航空', '低空'],
        '氢能': ['氢能', '氢燃料', '绿氢', '制氢', '储氢'],
        '医疗': ['医疗器械', '创新药', '生物医药', '中药', '疫苗'],
        '消费': ['消费', '家电', '汽车下乡', '以旧换新'],
        '数字经济': ['数字经济', '数据要素', '数据安全', '云计算', '大数据'],
    }
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.4
        self.name = "政策解读师"
        
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "keywords.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            self.policy_level_scores = self.config.get('policy_level_scores', {})
        except Exception as e:
            self.logger.warning(f"加载政策配置失败: {e}")
            self.policy_level_scores = {}
    
    def analyze(self, news_list: List[Any]) -> List[PolicyInsight]:
        """分析新闻中的政策信息"""
        insights = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            # 检测是否为政策新闻
            if not self._is_policy_news(text):
                continue
            
            insight = self._extract_policy(news, text)
            if insight:
                insights.append(insight)
        
        # 按级别排序
        insights.sort(key=lambda x: x.level_score, reverse=True)
        
        return insights
    
    def _is_policy_news(self, text: str) -> bool:
        """判断是否为政策新闻"""
        policy_markers = [
            '国务院', '发改委', '工信部', '财政部', '证监会', '银保监会',
            '科技部', '商务部', '政策', '规划', '意见', '通知', '办法',
            '指导意见', '实施方案', '工作方案', '行动计划', '发布', '出台'
        ]
        return any(marker in text for marker in policy_markers)
    
    def _extract_policy(self, news: Any, text: str) -> Optional[PolicyInsight]:
        """提取政策信息"""
        title = getattr(news, 'title', '')
        source = getattr(news, 'source', '')
        publish_time = getattr(news, 'publish_time', datetime.now())
        
        # 判断政策级别
        level = self._determine_level(text)
        level_score = level.score
        
        # 判断影响范围
        scope = self._determine_scope(text)
        
        # 提取受益行业
        benefit_sectors = self._extract_benefit_sectors(text)
        
        # 预测实施时间
        expected_time, timeline = self._predict_timeline(text)
        
        # 计算置信度
        confidence = self._calculate_confidence(text, level, benefit_sectors)
        
        # 产业链分析
        upstream, midstream, downstream = self._analyze_industry_chain(text, benefit_sectors)
        
        # 提取政策关键词
        policy_keywords = self._extract_policy_keywords(text)
        
        return PolicyInsight(
            policy_title=title,
            source=source,
            publish_date=publish_time,
            level=level,
            level_score=level_score,
            scope=scope,
            benefit_sectors=benefit_sectors,
            affected_industries=[],
            expected_implementation=expected_time,
            implementation_timeline=timeline,
            confidence=confidence,
            upstream_impact=upstream,
            midstream_impact=midstream,
            downstream_impact=downstream,
            policy_keywords=policy_keywords
        )
    
    def _determine_level(self, text: str) -> PolicyLevel:
        """判断政策级别"""
        scores = {level: 0 for level in PolicyLevel}
        
        for level, keywords in self.LEVEL_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[level] += 1
        
        # 额外检查：联合发文
        if '联合' in text or '共同' in text:
            scores[PolicyLevel.JOINT_MINISTRIES] += 2
        
        # 最高级别优先
        max_score = max(scores.values())
        if max_score == 0:
            return PolicyLevel.SINGLE_MINISTRY
        
        for level, score in scores.items():
            if score == max_score:
                return level
        
        return PolicyLevel.SINGLE_MINISTRY
    
    def _determine_scope(self, text: str) -> ImpactScope:
        """判断影响范围"""
        if any(kw in text for kw in ['全国', '中央', '统一']):
            return ImpactScope.NATIONAL
        elif any(kw in text for kw in ['行业', '产业', '领域']):
            return ImpactScope.INDUSTRY_WIDE
        elif any(kw in text for kw in ['地方', '区域', '试点']):
            return ImpactScope.REGIONAL
        return ImpactScope.ENTERPRISE
    
    def _extract_benefit_sectors(self, text: str) -> List[str]:
        """提取受益行业"""
        sectors = []
        for sector, keywords in self.BENEFIT_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                if sector not in sectors:
                    sectors.append(sector)
        return sectors
    
    def _predict_timeline(self, text: str) -> tuple:
        """预测政策实施时间"""
        timeline_type = 'medium_term'
        
        for ttype, keywords in self.TIMELINE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                timeline_type = ttype
                break
        
        now = datetime.now()
        timelines = {
            'immediate': (now + timedelta(days=1), '立即实施'),
            'short_term': (now + timedelta(days=30), '短期(1个月内)'),
            'medium_term': (now + timedelta(days=180), '中期(年内)'),
            'long_term': (now + timedelta(days=365), '长期(1年以上)')
        }
        
        return timelines.get(timeline_type, timelines['medium_term'])
    
    def _calculate_confidence(self, text: str, level: PolicyLevel, sectors: List[str]) -> float:
        """计算置信度"""
        base = 0.5
        
        # 级别加成
        base += level.score / 200
        
        # 行业明确加成
        if sectors:
            base += 0.1
        
        # 来源加成
        high_quality_sources = ['新华社', '人民日报', '央视', '中国政府网']
        if any(s in text for s in high_quality_sources):
            base += 0.15
        
        return min(base, 1.0)
    
    def _analyze_industry_chain(self, text: str, sectors: List[str]) -> tuple:
        """分析产业链各环节影响"""
        upstream = ""
        midstream = ""
        downstream = ""
        
        if '新能源汽车' in sectors or '电动车' in sectors:
            upstream = "锂矿、钴矿、正极材料、负极材料、电解液、隔膜"
            midstream = "电池制造、电机电控、整车制造"
            downstream = "充电桩、换电站、售后服务"
        
        elif '半导体' in sectors:
            upstream = "硅片、光刻胶、电子特气"
            midstream = "芯片设计、制造、封装测试"
            downstream = "消费电子、通信、汽车电子"
        
        elif '人工智能' in sectors:
            upstream = "AI芯片、算力基础设施"
            midstream = "算法研发、大模型训练"
            downstream = "AI应用、行业解决方案"
        
        elif '低空经济' in sectors:
            upstream = "原材料、核心零部件"
            midstream = "飞行器制造、基础设施"
            downstream = "运营服务、应用场景"
        
        return (upstream, midstream, downstream)
    
    def _extract_policy_keywords(self, text: str) -> List[str]:
        """提取政策关键词"""
        keywords = []
        policy_terms = [
            '政策支持', '财政补贴', '税收优惠', '产业基金', '试点',
            '扶持', '推动', '促进', '加快', '支持', '鼓励', '引导',
            '规范', '标准', '监管', '安全', '创新', '突破'
        ]
        
        for term in policy_terms:
            if term in text:
                keywords.append(term)
        
        return list(set(keywords))[:10]
    
    def generate_policy_report(self, insights: List[PolicyInsight]) -> str:
        """生成政策分析报告"""
        if not insights:
            return "📋 暂无政策相关信息"
        
        parts = ["\n📜 政策解读报告", "=" * 40]
        
        for insight in insights[:5]:
            stars = "⭐" * min(int(insight.level_score / 25), 4)
            
            parts.append(f"\n🔹 {insight.policy_title[:40]}")
            parts.append(f"   ├ 级别: {insight.level.label} {stars}")
            parts.append(f"   ├ 来源: {insight.source}")
            parts.append(f"   ├ 置信度: {insight.confidence:.0%}")
            
            if insight.benefit_sectors:
                parts.append(f"   ├ 受益: {', '.join(insight.benefit_sectors[:3])}")
            
            parts.append(f"   └ 时间: {insight.implementation_timeline}")
        
        return "\n".join(parts)
