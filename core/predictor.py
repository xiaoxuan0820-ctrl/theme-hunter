# -*- coding: utf-8 -*-
"""
预期预测引擎
基于题材分析结果，预测埋伏机会，生成交易信号
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    """机会数据模型"""
    theme_name: str              # 题材名称
    opportunity_type: str        # 机会类型: ambush(埋伏), breakout(突破), follow(跟风)
    
    # 评分
    score: float                  # 综合得分 0-100
    confidence: float             # 置信度 0-1
    
    # 时间
    entry_window_start: datetime  # 最佳入场窗口开始
    entry_window_end: datetime    # 最佳入场窗口结束
    expected_duration: int         # 预期持续天数
    
    # 风险收益
    risk_level: str               # 风险等级: high, medium, low
    expected_return: float        # 预期收益率%
    max_loss: float               # 最大亏损%
    
    # 建议
    action: str                   # 建议动作: buy, watch, caution
    notes: str                    # 备注说明
    
    # 标的
    recommended_stocks: List[str] = field(default_factory=list)
    avoid_stocks: List[str] = field(default_factory=list)
    
    # 催化剂
    catalyst: str = ""            # 主要催化剂
    catalyst_date: datetime = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        d = asdict(self)
        d['entry_window_start'] = self.entry_window_start.isoformat()
        d['entry_window_end'] = self.entry_window_end.isoformat()
        if self.catalyst_date:
            d['catalyst_date'] = self.catalyst_date.isoformat()
        return d


@dataclass
class Signal:
    """交易信号数据模型"""
    signal_id: str
    signal_type: str              # signal_type: entry, exit, warning, monitor
    theme_name: str               # 关联题材
    stock_code: str               # 股票代码
    stock_name: str               # 股票名称
    
    # 信号内容
    action: str                   # buy, sell, hold, watch
    price_target: float = 0       # 目标价
    stop_loss: float = 0         # 止损价
    position_size: float = 0      # 建议仓位%
    
    # 评级
    priority: str = "medium"      # high, medium, low
    confidence: float = 0         # 置信度 0-1
    
    # 时间
    generated_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = None
    
    # 原因
    reason: str = ""             # 信号原因
    risk_warning: str = ""        # 风险提示
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        d = asdict(self)
        d['generated_at'] = self.generated_at.isoformat()
        if self.valid_until:
            d['valid_until'] = self.valid_until.isoformat()
        return d


class ThemePredictor:
    """
    题材预测器
    
    功能：
    - 预测埋伏机会
    - 计算题材得分
    - 生成交易信号
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化预测器
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.threshold = self.config.get('threshold', {})
        
        # Agent权重配置
        self.agent_weights = {
            'policy': 1.3,
            'news': 1.2,
            'tech': 1.1,
            'event': 1.0,
            'stock': 1.2,
            'cycle': 1.4,
        }
    
    def predict_opportunity(self, theme: Any) -> Opportunity:
        """
        预测埋伏机会
        
        Args:
            theme: 题材对象
            
        Returns:
            机会对象
        """
        score = self.calculate_score(theme)
        stage = theme.stage.value if hasattr(theme, 'stage') else 'unknown'
        
        # 根据阶段判断机会类型
        if stage in ['germination', 'eruption']:
            opp_type = 'ambush'
            action = 'buy' if score >= 70 else 'watch'
            risk = 'medium' if score >= 70 else 'low'
        elif stage == 'speculation':
            opp_type = 'breakout'
            action = 'caution'
            risk = 'high'
        else:
            opp_type = 'follow'
            action = 'watch'
            risk = 'high'
        
        # 计算入场窗口
        now = datetime.now()
        catalysts = getattr(theme, 'catalysts', [])
        
        if catalysts:
            # 以第一个催化剂为准
            nearest_catalyst = min(catalysts, key=lambda c: c.expected_date)
            catalyst_date = nearest_catalyst.expected_date
            
            # 埋伏窗口：催化剂前1-7天
            entry_start = catalyst_date - timedelta(days=7)
            entry_end = catalyst_date - timedelta(days=1)
            
            # 如果已经过了催化剂
            if now > catalyst_date:
                entry_start = now
                entry_end = now + timedelta(days=3)
        else:
            catalyst_date = now + timedelta(days=7)
            entry_start = now
            entry_end = now + timedelta(days=5)
        
        # 计算预期收益
        if score >= 85:
            expected_return = 30
            max_loss = 10
        elif score >= 70:
            expected_return = 20
            max_loss = 8
        elif score >= 60:
            expected_return = 15
            max_loss = 6
        else:
            expected_return = 10
            max_loss = 5
        
        opportunity = Opportunity(
            theme_name=theme.name,
            opportunity_type=opp_type,
            score=score,
            confidence=getattr(theme, 'confidence', 0.5),
            entry_window_start=max(now, entry_start),
            entry_window_end=entry_end,
            expected_duration=5,
            risk_level=risk,
            expected_return=expected_return,
            max_loss=max_loss,
            action=action,
            notes=self._generate_notes(theme, score, stage),
            recommended_stocks=getattr(theme, 'leader_stocks', [])[:5],
            catalyst=getattr(catalysts[0], 'title', '') if catalysts else '',
            catalyst_date=catalyst_date,
        )
        
        return opportunity
    
    def calculate_score(self, theme: Any) -> float:
        """
        计算题材综合得分
        
        评分维度：
        - 热度得分 (30%)
        - 催化剂强度 (25%)
        - 阶段加成 (20%)
        - 资金关注度 (15%)
        - 政策支持度 (10%)
        
        Args:
            theme: 题材对象
            
        Returns:
            综合得分 0-100
        """
        # 基础得分
        heat_score = getattr(theme, 'heat_score', 0)
        
        # 催化剂评分
        catalysts = getattr(theme, 'catalysts', [])
        catalyst_score = 0
        for cat in catalysts:
            days_until = cat.days_until()
            if 1 <= days_until <= 7:
                catalyst_score = 100 - (days_until * 5)  # 越近越高
            elif days_until <= 0:
                catalyst_score = 50  # 已过催化剂
            else:
                catalyst_score = 30  # 较远的催化剂
        catalyst_score = min(catalyst_score, 100)
        
        # 阶段加成
        stage = getattr(theme, 'stage', None)
        stage_bonus = 0
        if stage:
            stage_map = {
                'germination': 20,   # 萌芽期加分
                'eruption': 25,      # 爆发期最高加分
                'speculation': 10,   # 炒作期加分少
                'cooldown': -10,     # 退潮期减分
                'dead': -30,         # 消亡期大减分
            }
            stage_bonus = stage_map.get(stage.value, 0)
        
        # 新闻数量加成
        news_count = getattr(theme, 'news_count', 0)
        news_bonus = min(news_count * 2, 20)
        
        # 计算加权得分
        weighted_score = (
            heat_score * 0.30 +
            catalyst_score * 0.25 +
            (50 + stage_bonus + news_bonus) * 0.20 +
            50 * 0.15 +  # 资金关注度，默认中等
            50 * 0.10    # 政策支持度，默认中等
        )
        
        return min(max(weighted_score, 0), 100)
    
    def _generate_notes(self, theme: Any, score: float, stage: str) -> str:
        """生成备注"""
        notes = []
        
        if score >= 85:
            notes.append("⭐⭐⭐⭐⭐ 强烈推荐埋伏机会")
        elif score >= 70:
            notes.append("⭐⭐⭐⭐ 推荐关注")
        elif score >= 60:
            notes.append("⭐⭐⭐ 可选择性埋伏")
        else:
            notes.append("⚠️ 建议观望，等待更好的时机")
        
        if stage == 'speculation':
            notes.append("⚠️ 注意：题材已进入炒作期，追高风险大")
        elif stage == 'cooldown':
            notes.append("⚠️ 注意：题材热度下降，需要等待新催化剂")
        elif stage == 'germination':
            notes.append("💡 提示：题材处于萌芽期，提前布局的好时机")
        
        catalysts = getattr(theme, 'catalysts', [])
        if catalysts:
            nearest = min(catalysts, key=lambda c: c.days_until())
            notes.append(f"📅 关注：{nearest.title[:30]}")
        
        return "\n".join(notes)
    
    def generate_signal(self, theme: Any, stock_code: str = None, stock_name: str = None) -> Signal:
        """
        生成交易信号
        
        Args:
            theme: 题材对象
            stock_code: 股票代码（可选）
            stock_name: 股票名称（可选）
            
        Returns:
            交易信号
        """
        score = self.calculate_score(theme)
        stage = getattr(theme, 'stage', None)
        stage_value = stage.value if stage else 'unknown'
        
        # 判断信号类型
        if score >= self.threshold.get('hot_topic_threshold', 75):
            if stage_value in ['germination', 'eruption']:
                signal_type = 'entry'
                action = 'buy'
                priority = 'high'
            elif stage_value == 'speculation':
                signal_type = 'warning'
                action = 'hold'
                priority = 'medium'
            else:
                signal_type = 'monitor'
                action = 'watch'
                priority = 'low'
        elif score >= self.threshold.get('min_theme_score', 60):
            signal_type = 'entry'
            action = 'buy'
            priority = 'medium'
        else:
            signal_type = 'monitor'
            action = 'watch'
            priority = 'low'
        
        # 风险提示
        risk_warning = ""
        if stage_value == 'speculation':
            risk_warning = "题材已进入炒作期，注意回调风险"
        elif getattr(theme, 'leader_stocks', []):
            risk_warning = "龙头股已有较大涨幅，谨慎追高"
        
        signal = Signal(
            signal_id=f"{theme.name}_{stock_code or 'general'}_{datetime.now().strftime('%Y%m%d%H%M')}",
            signal_type=signal_type,
            theme_name=theme.name,
            stock_code=stock_code or "",
            stock_name=stock_name or "",
            action=action,
            priority=priority,
            confidence=score / 100,
            valid_until=datetime.now() + timedelta(days=3),
            reason=f"题材热度{score:.0f}分，{stage.description if stage else '未知'}阶段" if stage else "",
            risk_warning=risk_warning,
        )
        
        return signal
    
    def rank_opportunities(self, themes: List[Any]) -> List[Opportunity]:
        """
        对题材机会进行排序
        
        Args:
            themes: 题材列表
            
        Returns:
            排序后的机会列表
        """
        opportunities = []
        
        for theme in themes:
            opp = self.predict_opportunity(theme)
            opportunities.append(opp)
        
        # 按得分排序
        opportunities.sort(key=lambda o: o.score, reverse=True)
        
        return opportunities
    
    def get_investment_advice(self, opportunity: Opportunity) -> str:
        """生成投资建议"""
        parts = [
            f"📈 题材: {opportunity.theme_name}",
            f"📊 综合评分: {opportunity.score:.0f}/100",
            f"🎯 机会类型: {opportunity.opportunity_type}",
            f"📅 入场窗口: {opportunity.entry_window_start.strftime('%m-%d')} ~ {opportunity.entry_window_end.strftime('%m-%d')}",
            f"⏰ 预期持续: {opportunity.expected_duration}天",
            f"💰 预期收益: ~{opportunity.expected_return}%",
            f"⚠️ 最大亏损: ~{opportunity.max_loss}%",
        ]
        
        if opportunity.recommended_stocks:
            parts.append(f"🐉 推荐标的: {', '.join(opportunity.recommended_stocks[:3])}")
        
        if opportunity.avoid_stocks:
            parts.append(f"🚫 规避标的: {', '.join(opportunity.avoid_stocks[:3])}")
        
        if opportunity.catalyst:
            parts.append(f"🔑 催化剂: {opportunity.catalyst[:40]}")
        
        parts.append(f"\n💡 建议: {opportunity.notes}")
        
        return "\n".join(parts)


# 示例用法
if __name__ == "__main__":
    from analyzer import ThemeAnalyzer, Theme, ThemeStage, Catalyst
    from datetime import datetime, timedelta
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建预测器
    predictor = ThemePredictor()
    
    # 创建测试题材
    test_theme = Theme(
        name="低空经济",
        keywords=["低空经济", "eVTOL", "飞行汽车"],
        related_sectors=["航空航天", "无人机"],
        sentiment="positive",
        stage=ThemeStage.ERUPTION,
        news_count=10,
        heat_score=85,
        catalysts=[
            Catalyst(
                type="policy",
                title="低空示范区名单公布",
                description="工信部将公布低空经济示范区名单",
                expected_date=datetime.now() + timedelta(days=5),
                confidence=0.8,
                impact_level="high"
            )
        ],
        leader_stocks=["万丰奥威", "中信海直"],
        first_appearance=datetime.now() - timedelta(days=2),
    )
    
    # 预测机会
    opp = predictor.predict_opportunity(test_theme)
    print(predictor.get_investment_advice(opp))
