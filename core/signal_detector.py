# -*- coding: utf-8 -*-
"""
演化信号检测器
检测题材阶段转换信号
"""

import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SignalIndicator:
    """信号指标"""
    keyword: str
    hit_count: int = 0
    last_seen: datetime = None
    trend: str = "stable"  # rising, falling


@dataclass
class EvolutionPrediction:
    """演化预测"""
    from_stage: str
    to_stage: str
    probability: float
    estimated_days: Tuple[int, int]
    indicators: List[SignalIndicator]
    recommendation: str


class EvolutionSignalDetector:
    """演化信号识别器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def detect_transition(self, current_kw: List[str], next_kw: List[str],
                          news_list: List[Any]) -> List[EvolutionPrediction]:
        """检测阶段转换信号"""
        predictions = []
        
        # 分析当前阶段信号
        current_signals = self._analyze_kw(current_kw, news_list)
        
        # 分析下一阶段信号
        next_signals = self._analyze_kw(next_kw, news_list)
        
        if not next_signals:
            return predictions
        
        # 计算演化概率
        prob = self._calc_probability(current_signals, next_signals)
        
        prediction = EvolutionPrediction(
            from_stage="当前阶段",
            to_stage="下一阶段",
            probability=prob,
            estimated_days=self._estimate_timeline(prob),
            indicators=next_signals,
            recommendation=self._gen_rec(prob),
        )
        predictions.append(prediction)
        
        return predictions
    
    def _analyze_kw(self, keywords: List[str], news_list: List[Any]) -> List[SignalIndicator]:
        """分析关键词信号"""
        indicators = []
        
        for kw in keywords:
            ind = SignalIndicator(keyword=kw, hit_count=0)
            for n in news_list:
                text = f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}"
                if kw in text:
                    ind.hit_count += 1
                    pt = getattr(n, 'publish_time', datetime.now())
                    if not ind.last_seen or pt > ind.last_seen:
                        ind.last_seen = pt
            
            if ind.hit_count > 0:
                indicators.append(ind)
        
        return self._analyze_trend(indicators)
    
    def _analyze_trend(self, indicators: List[SignalIndicator]) -> List[SignalIndicator]:
        """分析趋势"""
        sorted_ind = sorted([i for i in indicators if i.last_seen], key=lambda x: x.last_seen)
        
        if len(sorted_ind) >= 2:
            mid = len(sorted_ind) // 2
            recent = sum(i.hit_count for i in sorted_ind[-mid:])
            old = sum(i.hit_count for i in sorted_ind[:mid])
            
            for ind in indicators:
                if ind.hit_count > 0:
                    ind.trend = "rising" if recent > old * 1.5 else "falling" if recent < old * 0.5 else "stable"
        
        return indicators
    
    def _calc_probability(self, current: List[SignalIndicator], next: List[SignalIndicator]) -> float:
        """计算演化概率"""
        if not next:
            return 0.0
        
        hit_rate = len(next) / max(len(next), 1)
        intensity = min(sum(s.hit_count for s in next) / 10, 1.0)
        rising = sum(1 for s in next if s.trend == "rising") / max(len(next), 1) * 0.3
        
        recent = sum(1 for s in next if s.last_seen and s.last_seen > datetime.now() - timedelta(hours=24))
        recency = recent / max(len(next), 1) * 0.2
        
        prob = hit_rate * 0.3 + intensity * 0.3 + rising + recency
        return min(max(prob, 0.0), 0.95)
    
    def _estimate_timeline(self, prob: float) -> Tuple[int, int]:
        """估计时间线"""
        if prob >= 0.7:
            return (3, 7)
        elif prob >= 0.5:
            return (7, 14)
        elif prob >= 0.3:
            return (14, 30)
        return (30, 90)
    
    def _gen_rec(self, prob: float) -> str:
        """生成建议"""
        if prob >= 0.7:
            return "⚡ 强烈建议提前布局"
        elif prob >= 0.5:
            return "📈 密切关注，可小仓试探"
        elif prob >= 0.3:
            return "👀 持续观察，等待信号"
        return "⏳ 耐心等待"
    
    def generate_report(self, predictions: List[EvolutionPrediction]) -> str:
        """生成报告"""
        if not predictions:
            return "📡 演化信号检测\n\n未检测到明显演化信号"
        
        parts = ["📡 演化信号检测", "=" * 40]
        
        high = [p for p in predictions if p.probability >= 0.5]
        if high:
            parts.append("\n🔔 高概率演化信号:")
            for p in high:
                parts.append(f"\n• {p.from_stage} → {p.to_stage}")
                parts.append(f"  概率: {p.probability * 100:.0f}%")
                parts.append(f"  预计: {p.estimated_days[0]}-{p.estimated_days[1]}天")
                parts.append(f"  💡 {p.recommendation}")
        
        return "\n".join(parts)
