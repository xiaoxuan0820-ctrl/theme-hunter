# -*- coding: utf-8 -*-
"""
Cycle Agent - 题材周期师（升级版）
权重: 1.5
功能：
- 更精确的阶段判断算法
- 添加历史同类题材对比
- 添加退潮预警指标
- 输出：阶段、持续天数预测、风险等级
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ThemeStage(Enum):
    """题材阶段"""
    GERMINATION = ("萌芽期", "🌱", "提前布局")
    ERUPTION = ("爆发期", "🔥", "积极参与")
    SPECULATION = ("炒作期", "⚡", "谨慎追高")
    COOLDOWN = ("退潮期", "💧", "逐步减仓")
    DEAD = ("消亡期", "💀", "坚决回避")
    
    def __init__(self, label, emoji, action):
        self.label = label
        self.emoji = emoji
        self.action = action


@dataclass
class StageMetrics:
    """阶段指标"""
    velocity: float                  # 新闻速度 0-100
    sentiment: float                 # 情绪指数 -100到100
    breadth: float                   # 扩散度（多少只股票涨停）
    depth: float                     # 深度（龙头涨幅）
    momentum: float                  # 动量
    
    # 阶段持续时间预测
    days_in_stage: int               # 已持续天数
    predicted_remaining_days: int     # 预计剩余天数
    confidence: float                # 预测置信度
    
    # 预警
    warnings: List[str] = field(default_factory=list)
    risk_level: str = "low"          # low/medium/high


@dataclass
class HistoricalComparison:
    """历史对比"""
    similar_theme: str               # 同类题材
    similarity: float                # 相似度 0-1
    duration: int                     # 持续天数
    peak_leader_return: float        # 龙头峰值涨幅
    stage_durations: Dict[str, int] # 各阶段持续时间
    lessons: str                     # 经验教训
    reference_value: str              # 参考价值


@dataclass
class CooldownWarning:
    """退潮预警"""
    is_warning: bool
    warning_type: str                # 分化/回落/监管/减持
    severity: str                     # 轻度/中度/重度
    indicators: List[str]             # 具体指标
    action: str                       # 建议动作


class CycleAgent:
    """题材周期师 - 深度周期分析"""
    
    # 阶段信号
    STAGE_SIGNALS = {
        ThemeStage.GERMINATION: {
            'keywords': ['首次', '首款', '首创', '突破', '新产品', '新技术', '重大进展'],
            'weight': 1.0
        },
        ThemeStage.ERUPTION: {
            'keywords': ['爆发', '涨停', '暴涨', '引爆', '全民', '抢筹', '连板'],
            'weight': 1.2
        },
        ThemeStage.SPECULATION: {
            'keywords': ['妖股', '连板', '疯狂', '炒作', '全民炒股', '接棒', '补涨'],
            'weight': 1.1
        },
        ThemeStage.COOLDOWN: {
            'keywords': ['回落', '回调', '分化', '退潮', '滞涨', '高位震荡'],
            'weight': 1.0
        },
        ThemeStage.DEAD: {
            'keywords': ['消亡', '过时', '淘汰', '证伪', '证实'],
            'weight': 1.0
        }
    }
    
    # 退潮预警指标
    COOLDOWN_WARNING_SIGNALS = {
        'differentiation': {
            'keywords': ['分化', '个股分化', '涨跌不一', '严重分化'],
            'severity': 'medium'
        },
        'pullback': {
            'keywords': ['回落', '回调', '冲高回落', '炸板'],
            'severity': 'high'
        },
        'regulatory': {
            'keywords': ['监管', '降温', '提示风险', '自查', '停牌核查'],
            'severity': 'high'
        },
        'reduction': {
            'keywords': ['减持', '清仓', '抛售', '大股东'],
            'severity': 'high'
        },
        'overheat': {
            'keywords': ['过热', '泡沫', '估值过高', '透支'],
            'severity': 'medium'
        },
        'momentum_loss': {
            'keywords': ['滞涨', '乏力', '动力不足', '观望'],
            'severity': 'medium'
        }
    }
    
    # 历史同类题材
    HISTORICAL_THEMES = {
        '固态电池': {
            'similar': '锂离子电池',
            'year': 2019,
            'duration': 45,
            'peak_return': 0.5,
            'stages': {'萌芽': 7, '爆发': 20, '炒作': 15, '退潮': 10}
        },
        'AI': {
            'similar': '互联网金融',
            'year': 2015,
            'duration': 60,
            'peak_return': 2.0,
            'stages': {'萌芽': 10, '爆发': 25, '炒作': 20, '退潮': 15}
        },
        '低空经济': {
            'similar': '新能源汽车',
            'year': 2024,
            'duration': 90,
            'peak_return': 0.8,
            'stages': {'萌芽': 14, '爆发': 30, '炒作': 30, '退潮': 20}
        },
        '人形机器人': {
            'similar': '工业机器人',
            'year': 2023,
            'duration': 40,
            'peak_return': 0.6,
            'stages': {'萌芽': 7, '爆发': 18, '炒作': 12, '退潮': 8}
        }
    }
    
    # 阶段持续时间参考
    STAGE_DURATION_REF = {
        ThemeStage.GERMINATION: {'min': 3, 'max': 14, 'typical': 7},
        ThemeStage.ERUPTION: {'min': 5, 'max': 30, 'typical': 14},
        ThemeStage.SPECULATION: {'min': 7, 'max': 45, 'typical': 21},
        ThemeStage.COOLDOWN: {'min': 3, 'max': 14, 'typical': 7},
        ThemeStage.DEAD: {'min': 0, 'max': 0, 'typical': 0}
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.5
        self.name = "题材周期师"
    
    def analyze(self, theme_name: str, news_list: List[Any], 
                first_mention: datetime = None) -> Tuple[ThemeStage, StageMetrics, CooldownWarning]:
        """综合分析题材周期"""
        # 计算各项指标
        velocity = self._calc_velocity(news_list)
        sentiment = self._calc_sentiment(news_list)
        breadth = self._calc_breadth(news_list)
        depth = self._calc_depth(news_list)
        momentum = self._calc_momentum(velocity, sentiment, breadth)
        
        # 判断阶段
        stage = self._determine_stage(theme_name, news_list, velocity, sentiment)
        
        # 计算阶段持续时间
        days_in_stage = self._calc_days(news_list, first_mention)
        predicted_days = self._predict_remaining_days(stage, velocity, momentum)
        
        # 检测退潮预警
        warning = self._detect_cooldown_warning(news_list, stage)
        
        # 构建指标（先生成warnings需要的参数）
        confidence = self._calculate_confidence(stage, warning)
        warnings_text = self._generate_warnings(stage, warning, velocity, sentiment, breadth, momentum, confidence)
        
        metrics = StageMetrics(
            velocity=velocity,
            sentiment=sentiment,
            breadth=breadth,
            depth=depth,
            momentum=momentum,
            days_in_stage=days_in_stage,
            predicted_remaining_days=predicted_days,
            confidence=confidence,
            warnings=warnings_text,
            risk_level=self._assess_risk_level(stage, warning, days_in_stage)
        )
        
        return stage, metrics, warning
    
    def compare_with_history(self, theme_name: str, news_list: List[Any]) -> Optional[HistoricalComparison]:
        """与历史题材对比"""
        # 查找相似题材
        similar_key = None
        max_similarity = 0
        
        for key, data in self.HISTORICAL_THEMES.items():
            if key in theme_name or theme_name in key:
                similarity = 0.9
            else:
                similarity = 0.5
            
            if similarity > max_similarity:
                max_similarity = similarity
                similar_key = key
        
        if not similar_key or max_similarity < 0.3:
            return None
        
        data = self.HISTORICAL_THEMES[similar_key]
        
        # 分析当前与历史的差异
        current_velocity = self._calc_velocity(news_list)
        
        return HistoricalComparison(
            similar_theme=f"{data['similar']}({data['year']}年)",
            similarity=max_similarity,
            duration=data['duration'],
            peak_leader_return=data['peak_return'],
            stage_durations=data['stages'],
            lessons=self._generate_lessons(data),
            reference_value="高" if max_similarity > 0.7 else "中"
        )
    
    def _calc_velocity(self, news_list: List[Any]) -> float:
        """计算新闻速度"""
        from datetime import timezone
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        count = 0
        recent_count = 0
        
        for n in news_list:
            pt = getattr(n, 'publish_time', None)
            if pt:
                if pt.tzinfo is None:
                    pt = pt.replace(tzinfo=timezone.utc)
                if pt > cutoff:
                    recent_count += 1
                count += 1
        
        # 速度 = 24小时内新闻数 * 12，上限100
        velocity = min(recent_count * 12, 100)
        
        return velocity
    
    def _calc_sentiment(self, news_list: List[Any]) -> float:
        """计算情绪指数"""
        positive = ['利好', '大涨', '爆发', '突破', '看好', '涨停', '暴涨', '超预期']
        negative = ['利空', '下跌', '风险', '问题', '减持', '回落', '澄清', '否认']
        
        score = 0
        for n in news_list:
            text = f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}"
            score += sum(1 for p in positive if p in text)
            score -= sum(1 for n in negative if n in text)
        
        return max(-100, min(score * 6, 100))
    
    def _calc_breadth(self, news_list: List[Any]) -> float:
        """计算扩散度"""
        # 统计涉及涨停的股票数量
        limit_up_count = 0
        for n in news_list:
            text = f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}"
            if any(kw in text for kw in ['涨停', '连板', '10cm', '20cm']):
                limit_up_count += 1
        
        # 扩散度 = 涨停相关新闻占比
        if not news_list:
            return 0
        
        return min(limit_up_count / len(news_list) * 100, 100)
    
    def _calc_depth(self, news_list: List[Any]) -> float:
        """计算深度（龙头涨幅）"""
        # 从新闻中提取涨幅信息
        total_return = 0
        count = 0
        
        for n in news_list:
            text = f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}"
            
            # 提取数字
            numbers = re.findall(r'(\d+(?:\.\d+)?)%', text)
            for num_str in numbers:
                try:
                    num = float(num_str)
                    if num > 0 and num < 50:  # 合理涨幅范围
                        total_return += num
                        count += 1
                except:
                    pass
        
        if count == 0:
            return 50  # 默认中等
        
        return min(total_return / count, 100)
    
    def _calc_momentum(self, velocity: float, sentiment: float, breadth: float) -> float:
        """计算动量"""
        # 动量 = 速度(0.3) + 情绪(0.3) + 扩散(0.4)
        momentum = velocity * 0.3 + (sentiment + 100) / 2 * 0.3 + breadth * 0.4
        return min(momentum, 100)
    
    def _determine_stage(self, theme_name: str, news_list: List[Any], 
                        velocity: float, sentiment: float) -> ThemeStage:
        """判断阶段"""
        scores = {stage: 0 for stage in ThemeStage}
        text = " ".join(f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}" for n in news_list)
        
        # 关键词打分
        for stage, signals in self.STAGE_SIGNALS.items():
            for kw in signals['keywords']:
                if kw in text:
                    scores[stage] += signals['weight']
        
        # 速度加成
        if velocity > 70:
            scores[ThemeStage.ERUPTION] += 3
        elif velocity > 50:
            scores[ThemeStage.SPECULATION] += 1
        
        # 情绪加成
        if sentiment > 70:
            scores[ThemeStage.SPECULATION] += 2
        elif sentiment < -30:
            scores[ThemeStage.COOLDOWN] += 2
        
        # 速度低加成退潮
        if velocity < 30 and sentiment > 0:
            scores[ThemeStage.COOLDOWN] += 2
        
        # 特殊处理
        if any(kw in text for kw in ['证伪', '失败', '不存在']):
            scores[ThemeStage.DEAD] += 5
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _calc_days(self, news_list: List[Any], first_mention: datetime = None) -> int:
        """计算已持续天数"""
        if first_mention:
            return (datetime.now() - first_mention).days + 1
        
        dates = [getattr(n, 'publish_time', datetime.now()) for n in news_list]
        if dates:
            return (datetime.now() - min(dates)).days + 1
        return 1
    
    def _predict_remaining_days(self, stage: ThemeStage, velocity: float, 
                               momentum: float) -> int:
        """预测剩余天数"""
        ref = self.STAGE_DURATION_REF[stage]
        base_days = ref['typical']
        
        # 根据速度调整
        if velocity > 80:
            base_days *= 0.7  # 加速，缩短
        elif velocity < 40:
            base_days *= 1.3  # 减速，延长
        
        # 根据动量调整
        if momentum > 80:
            base_days *= 0.8
        elif momentum < 40:
            base_days *= 1.2
        
        return max(1, int(base_days))
    
    def _detect_cooldown_warning(self, news_list: List[Any], 
                                 current_stage: ThemeStage) -> CooldownWarning:
        """检测退潮预警"""
        warnings_found = []
        
        for n in news_list:
            text = f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}"
            
            for wtype, signal in self.COOLDOWN_WARNING_SIGNALS.items():
                if any(kw in text for kw in signal['keywords']):
                    warnings_found.append({
                        'type': wtype,
                        'severity': signal['severity'],
                        'text': getattr(n, 'title', '')[:50]
                    })
        
        if not warnings_found:
            return CooldownWarning(
                is_warning=False,
                warning_type='none',
                severity='none',
                indicators=[],
                action='继续持有或逢低加仓'
            )
        
        # 确定最严重的预警
        severity_order = {'high': 3, 'medium': 2, 'light': 1}
        worst = max(warnings_found, key=lambda x: severity_order.get(x['severity'], 0))
        
        return CooldownWarning(
            is_warning=True,
            warning_type=worst['type'],
            severity=worst['severity'],
            indicators=[w['text'] for w in warnings_found[:3]],
            action=self._get_warning_action(worst['type'])
        )
    
    def _get_warning_action(self, warning_type: str) -> str:
        """获取预警动作"""
        actions = {
            'differentiation': '注意分化，减仓跟风股',
            'pullback': '警惕回落，设定止损',
            'regulatory': '监管降温信号，立即减仓',
            'reduction': '大股东减持，降低仓位',
            'overheat': '注意估值泡沫，逐步止盈',
            'momentum_loss': '动力减弱，观望为主'
        }
        return actions.get(warning_type, '谨慎操作')
    
    def _calculate_confidence(self, stage: ThemeStage, warning: CooldownWarning) -> float:
        """计算预测置信度"""
        base = 0.6
        
        # 阶段越明确置信度越高
        if stage in [ThemeStage.ERUPTION, ThemeStage.DEAD]:
            base += 0.2
        elif stage == ThemeStage.GERMINATION:
            base += 0.1
        
        # 有预警降低置信度
        if warning.is_warning:
            base -= 0.1
        
        return max(0.3, min(base, 0.95))
    
    def _generate_warnings(self, stage: ThemeStage, warning: CooldownWarning,
                          velocity: float, sentiment: float, breadth: float, 
                          momentum: float, confidence: float) -> List[str]:
        """生成预警信息"""
        warnings = []
        
        # 阶段预警
        if stage == ThemeStage.SPECULATION:
            warnings.append("⚡ 处于炒作期，注意追高风险")
        
        if stage == ThemeStage.COOLDOWN:
            warnings.append("💧 处于退潮期，建议减仓")
        
        # 具体预警
        if warning.is_warning:
            warning_text = {
                'differentiation': '⚠️ 出现分化信号',
                'pullback': '⚠️ 出现回落信号',
                'regulatory': '🚨 监管降温信号',
                'reduction': '🚨 大股东减持',
                'overheat': '⚠️ 估值过热',
                'momentum_loss': '⚠️ 动量减弱'
            }
            warnings.append(warning_text.get(warning.warning_type, '⚠️ 存在风险'))
        
        # 持续时间预警
        if momentum > 0.8 and stage in [ThemeStage.ERUPTION, ThemeStage.SPECULATION]:
            warnings.append("⚠️ 动量偏高，注意回调风险")
        
        return warnings[:3]
    
    def _assess_risk_level(self, stage: ThemeStage, warning: CooldownWarning, 
                          days_in_stage: int) -> str:
        """评估风险等级"""
        if warning.severity == 'high':
            return 'high'
        
        if stage in [ThemeStage.SPECULATION, ThemeStage.DEAD]:
            return 'high'
        
        if warning.is_warning:
            return 'medium'
        
        if stage == ThemeStage.ERUPTION and days_in_stage > 14:
            return 'medium'
        
        return 'low'
    
    def _generate_lessons(self, historical: Dict) -> str:
        """生成经验教训"""
        lessons = []
        
        if historical['peak_return'] > 1.0:
            lessons.append("当时泡沫严重，需警惕")
        
        if historical['duration'] < 30:
            lessons.append("持续时间较短，需快进快出")
        else:
            lessons.append("持续时间较长，有反复机会")
        
        return "; ".join(lessons)
    
    def generate_cycle_report(self, theme_name: str, stage: ThemeStage, 
                              metrics: StageMetrics, warning: CooldownWarning,
                              history: HistoricalComparison = None) -> str:
        """生成周期分析报告"""
        parts = [f"\n📊 【{theme_name}】周期分析", "=" * 50]
        
        # 阶段信息
        parts.append(f"\n📍 当前阶段: {stage.emoji}{stage.label}")
        parts.append(f"├ 持续天数: {metrics.days_in_stage}天")
        parts.append(f"├ 新闻速度: {metrics.velocity:.0f}")
        parts.append(f"├ 情绪指数: {metrics.sentiment:.0f}")
        parts.append(f"├ 扩散度: {metrics.breadth:.0f}%")
        parts.append(f"├ 动量: {metrics.momentum:.0f}")
        parts.append(f"├ 预计剩余: {metrics.predicted_remaining_days}天")
        parts.append(f"├ 风险等级: {metrics.risk_level.upper()}")
        
        if metrics.warnings:
            parts.append(f"├ 预警:")
            for w in metrics.warnings:
                parts.append(f"│ └ {w}")
        
        parts.append(f"└ 建议: {stage.action}")
        
        # 退潮预警
        if warning.is_warning:
            parts.append(f"\n🚨 退潮预警")
            parts.append(f"├ 类型: {warning.warning_type}")
            parts.append(f"├ 严重程度: {warning.severity}")
            parts.append(f"└ 动作: {warning.action}")
        
        # 历史对比
        if history:
            parts.append(f"\n📈 历史对比")
            parts.append(f"├ 同类题材: {history.similar_theme}")
            parts.append(f"├ 相似度: {history.similarity:.0%}")
            parts.append(f"├ 持续时间: {history.duration}天")
            parts.append(f"├ 龙头涨幅: {history.peak_leader_return:.0%}")
            parts.append(f"├ 参考价值: {history.reference_value}")
            parts.append(f"└ 经验: {history.lessons}")
        
        return "\n".join(parts)
