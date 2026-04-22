# -*- coding: utf-8 -*-
"""
题材周期师 Agent
权重: 1.4（最高）- 判断题材阶段，预警炒作过热
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ThemeStage(Enum):
    """题材阶段"""
    GERMINATION = "萌芽期"
    ERUPTION = "爆发期"
    SPECULATION = "炒作期"
    COOLDOWN = "退潮期"
    DEAD = "消亡期"
    
    @property
    def emoji(self) -> str:
        return {'萌芽期': '🌱', '爆发期': '🔥', '炒作期': '⚡', '退潮期': '💧', '消亡期': '💀'}.get(self.value, '❓')
    
    @property
    def action(self) -> str:
        return {'萌芽期': '提前布局', '爆发期': '积极参与', '炒作期': '谨慎追高', '退潮期': '逐步减仓', '消亡期': '坚决回避'}.get(self.value, '观望')


@dataclass
class CycleAnalysis:
    """周期分析"""
    theme_name: str
    stage: ThemeStage
    days_in_stage: int
    news_velocity: float
    sentiment: float
    warnings: List[str]
    recommendations: List[str]


class CycleAgent:
    """题材周期师 - 判断阶段和预警"""
    
    STAGE_SIGNALS = {
        ThemeStage.GERMINATION: ['首次', '首款', '首创', '突破', '新产品'],
        ThemeStage.ERUPTION: ['爆发', '涨停', '暴涨', '引爆', '全民'],
        ThemeStage.SPECULATION: ['妖股', '连板', '疯狂', '炒作'],
        ThemeStage.COOLDOWN: ['回落', '回调', '分化', '退潮'],
        ThemeStage.DEAD: ['消亡', '过时', '淘汰'],
    }
    
    WARNING_KEYWORDS = ['过热', '减持', '解禁', '监管', '降温', '风险', '澄清']
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.4
        self.name = "题材周期师"
    
    def analyze(self, theme_name: str, news_list: List[Any], first_mention: datetime = None) -> CycleAnalysis:
        """分析题材所处阶段"""
        # 计算指标
        velocity = self._calc_velocity(news_list)
        sentiment = self._calc_sentiment(news_list)
        stage = self._determine_stage(theme_name, news_list)
        days = self._calc_days(news_list, first_mention)
        warnings = self._detect_warnings(news_list)
        recs = self._generate_recs(stage, warnings)
        
        return CycleAnalysis(
            theme_name=theme_name,
            stage=stage,
            days_in_stage=days,
            news_velocity=velocity,
            sentiment=sentiment,
            warnings=warnings,
            recommendations=recs,
        )
    
    def _calc_velocity(self, news_list: List[Any]) -> float:
        """计算新闻速度"""
        from datetime import timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        count = 0
        for n in news_list:
            pt = getattr(n, 'publish_time', None)
            if pt:
                # 确保时区一致
                if pt.tzinfo is None:
                    pt = pt.replace(tzinfo=timezone.utc)
                if pt > cutoff:
                    count += 1
        return min(count * 12, 100)
    
    def _calc_sentiment(self, news_list: List[Any]) -> float:
        """计算情绪指数"""
        positive = ['利好', '大涨', '爆发', '突破', '看好']
        negative = ['利空', '下跌', '风险', '问题']
        score = 0
        for n in news_list:
            text = f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}"
            score += sum(1 for p in positive if p in text)
            score -= sum(1 for n in negative if n in text)
        return max(-100, min(score * 6, 100))
    
    def _determine_stage(self, theme_name: str, news_list: List[Any]) -> ThemeStage:
        """判断阶段"""
        text = " ".join(f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}" for n in news_list)
        scores = {s: 0 for s in ThemeStage}
        
        for stage, kws in self.STAGE_SIGNALS.items():
            for kw in kws:
                if kw in text:
                    scores[stage] += 1
        
        if self._calc_velocity(news_list) > 70:
            scores[ThemeStage.ERUPTION] += 2
        if self._calc_sentiment(news_list) > 70:
            scores[ThemeStage.SPECULATION] += 2
        if self._calc_velocity(news_list) < 30:
            scores[ThemeStage.COOLDOWN] += 2
        
        return max(scores, key=scores.get)
    
    def _calc_days(self, news_list: List[Any], first_mention: datetime = None) -> int:
        """计算在当前阶段的天数"""
        if first_mention:
            return (datetime.now() - first_mention).days + 1
        
        dates = [getattr(n, 'publish_time', datetime.now()) for n in news_list]
        if dates:
            return (datetime.now() - min(dates)).days + 1
        return 1
    
    def _detect_warnings(self, news_list: List[Any]) -> List[str]:
        """检测预警信号"""
        warnings = []
        for n in news_list:
            text = f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}"
            for kw in self.WARNING_KEYWORDS:
                if kw in text:
                    msg = f"⚠️ {kw}信号"
                    if msg not in warnings:
                        warnings.append(msg)
        return warnings[:3]
    
    def _generate_recs(self, stage: ThemeStage, warnings: List[str]) -> List[str]:
        """生成建议"""
        recs = [f"阶段建议: {stage.action}"]
        
        if stage == ThemeStage.GERMINATION:
            recs.append("• 题材初期，适合提前布局")
        elif stage == ThemeStage.ERUPTION:
            recs.append("• 积极参与但控制仓位")
        elif stage == ThemeStage.SPECULATION:
            recs.append("• 谨慎追高，注意回调")
        elif stage == ThemeStage.COOLDOWN:
            recs.append("• 逐步减仓或观望")
        else:
            recs.append("• 题材已过，建议回避")
        
        return recs
    
    def generate_report(self, analyses: List[CycleAnalysis]) -> str:
        """生成周期报告"""
        if not analyses:
            return "🔄 题材周期师报告\n\n暂无分析数据"
        
        parts = ["🔄 题材周期师报告", "=" * 40]
        
        for a in analyses:
            parts.append(f"\n📌 【{a.theme_name}】")
            parts.append(f"├ 阶段: {a.stage.emoji}{a.stage.value}")
            parts.append(f"├ 在此阶段: {a.days_in_stage}天")
            parts.append(f"├ 新闻热度: {a.news_velocity:.0f}")
            parts.append(f"├ 情绪指数: {a.sentiment:.0f}")
            
            if a.warnings:
                parts.append(f"└ 预警: {', '.join(a.warnings)}")
            else:
                parts.append(f"└ 建议: {a.recommendations[0]}")
        
        return "\n".join(parts)
