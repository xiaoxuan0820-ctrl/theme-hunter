# -*- coding: utf-8 -*-
"""
Tech Agent - 技术前瞻者（升级版）
权重: 1.2
功能：
- 技术成熟度评估（TRL 1-9级）
- 产业化时间表预测
- 技术壁垒分析
- 输出：技术成熟度、产业化时间、竞争格局
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TechnologyReadinessLevel(Enum):
    """技术成熟度等级（TRL）"""
    TRL1 = (1, "basic_principles", "基本原理发现", "基础研究阶段")
    TRL2 = (2, "concept_formulation", "技术概念形成", "基础研究阶段")
    TRL3 = (3, "key_function_test", "关键功能验证", "实验阶段")
    TRL4 = (4, "lab_verification", "实验室验证", "实验阶段")
    TRL5 = (5, "relevant_env_test", "相关环境验证", "工程化阶段")
    TRL6 = (6, "relevant_system_demo", "相关系统演示", "工程化阶段")
    TRL7 = (7, "prototype_demo", "系统原型演示", "商业化前期")
    TRL8 = (8, "system_complete", "系统完成并验证", "商业化前期")
    TRL9 = (9, "successful_operation", "实际系统成功运行", "商业化阶段")
    
    def __init__(self, level, code, description, phase):
        self._level = level
        self._code = code
        self.description = description
        self.phase = phase
    
    @property
    def level(self):
        return self._level
    
    @property
    def name_code(self):
        return self._code


@dataclass
class TechInsight:
    """技术洞察"""
    tech_name: str
    theme_name: str
    
    # 成熟度
    trl_level: TechnologyReadinessLevel
    trl_score: int                   # 0-100
    
    # 产业化预测
    industrialization_timeline: str   # 时间表描述
    estimated_industrialization_date: datetime
    confidence: float                # 置信度
    
    # 壁垒分析
    technical_barriers: List[str]     # 技术壁垒
    barrier_level: str               # high/medium/low
    
    # 竞争格局
    leading_players: List[str]        # 领先玩家
    competition_intensity: str         # 竞争强度
    china_capability: str             # 中国能力
    
    # 催化剂
    catalysts: List[str] = field(default_factory=list)
    
    # 风险
    risks: List[str] = field(default_factory=list)


@dataclass
class IndustrializationPrediction:
    """产业化预测"""
    phase: str                        # 当前阶段
    duration_to_next: int             # 到下一阶段的月数
    next_phase: str                   # 下一阶段
    probability: float                # 预测概率
    key_indicators: List[str]         # 关键指标


class TechAgent:
    """技术前瞻者 - 深度技术分析"""
    
    # 技术成熟度信号
    TRL_SIGNALS = {
        TechnologyReadinessLevel.TRL1: ['理论', '原理', '概念', '发现'],
        TechnologyReadinessLevel.TRL2: ['概念', '假设', '理论验证'],
        TechnologyReadinessLevel.TRL3: ['关键功能', '验证', '实验'],
        TechnologyReadinessLevel.TRL4: ['实验室', '样品', '原型'],
        TechnologyReadinessLevel.TRL5: ['环境验证', '相关环境', '测试'],
        TechnologyReadinessLevel.TRL6: ['系统演示', '原型系统', '模拟'],
        TechnologyReadinessLevel.TRL7: ['系统原型', '演示', '预商业'],
        TechnologyReadinessLevel.TRL8: ['系统验证', '完成', '定型'],
        TechnologyReadinessLevel.TRL9: ['量产', '商业化', '批量生产', '大规模应用']
    }
    
    # 产业化时间参考（月）
    INDUSTRIALIZATION_TIMELINE = {
        '固态电池': {'trl5_to_trl7': 12, 'trl7_to_trl9': 24, 'confidence': 0.7},
        '氢燃料电池': {'trl5_to_trl7': 18, 'trl7_to_trl9': 36, 'confidence': 0.65},
        '脑机接口': {'trl5_to_trl7': 24, 'trl7_to_trl9': 48, 'confidence': 0.5},
        '人形机器人': {'trl5_to_trl7': 12, 'trl7_to_trl9': 24, 'confidence': 0.75},
        '量子计算': {'trl5_to_trl7': 36, 'trl7_to_trl9': 60, 'confidence': 0.4},
        'eVTOL': {'trl5_to_trl7': 6, 'trl7_to_trl9': 18, 'confidence': 0.8},
        'AI大模型': {'trl5_to_trl7': 3, 'trl7_to_trl9': 12, 'confidence': 0.85},
    }
    
    # 技术壁垒关键词
    BARRIER_KEYWORDS = {
        'high': ['专利壁垒', '核心专利', '技术封锁', '卡脖子', '垄断', '独占'],
        'medium': ['技术积累', 'know-how', '工艺', '经验'],
        'low': ['门槛低', '易模仿', '开源']
    }
    
    # 关键技术跟踪
    TECH_KEYWORDS = {
        '固态电池': ['固态电解质', '锂金属负极', '硫化物', '氧化物', '叠片'],
        '氢能': ['质子交换膜', '催化剂', '碳纸', '储氢'],
        'AI': ['大模型', 'Transformer', '注意力机制', '预训练'],
        '半导体': ['3nm', '2nm', 'GAA', 'FinFET', 'EUV'],
        '人形机器人': ['灵巧手', '关节电机', '力控', '视觉', '具身智能'],
        'eVTOL': ['多旋翼', '倾转旋翼', '复合翼', '自动驾驶'],
        '光通信': ['CPO', '硅光', 'LPO', '800G', '1.6T']
    }
    
    # 领先玩家库
    LEADING_PLAYERS = {
        '固态电池': ['宁德时代', '赣锋锂业', '比亚迪', '三星SDI', '松下', 'QuantumScape', 'Solid Power'],
        '氢能': ['亿华通', '重塑能源', '巴拉德', '普拉格', 'Plug Power'],
        'AI': ['OpenAI', 'Google', '百度', '阿里', '字节跳动', '科大讯飞'],
        '半导体': ['台积电', '三星', 'Intel', '中芯国际', '华虹半导体'],
        '人形机器人': ['波士顿动力', 'Tesla(Optimus)', 'Figure', '宇树科技', '智元机器人'],
        'eVTOL': ['亿航智能', '峰飞航空', 'Lilium', 'Joby', 'Archer'],
        '光通信': ['中际旭创', '光迅科技', '新易盛', 'Intel', 'Cisco']
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.2
        self.name = "技术前瞻者"
    
    def analyze(self, theme_name: str, news_list: List[Any]) -> List[TechInsight]:
        """分析技术信息"""
        insights = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            # 检查是否与技术相关
            if not self._is_tech_news(text, theme_name):
                continue
            
            insight = self._extract_tech_info(theme_name, news, text)
            if insight:
                insights.append(insight)
        
        return insights
    
    def _is_tech_news(self, text: str, theme_name: str) -> bool:
        """判断是否为技术新闻"""
        tech_markers = [
            '技术', '突破', '研发', '量产', '测试', '验证',
            '专利', '发明', '创新', '工艺', '材料', '性能'
        ]
        
        # 主题相关技术关键词
        related_techs = self.TECH_KEYWORDS.get(theme_name, [])
        
        return any(marker in text for marker in tech_markers) or \
               any(tech in text for tech in related_techs)
    
    def _extract_tech_info(self, theme_name: str, news: Any, text: str) -> Optional[TechInsight]:
        """提取技术信息"""
        # 评估TRL等级
        trl = self._assess_trl(text)
        
        # 预测产业化时间
        timeline, ind_date = self._predict_industrialization(theme_name, trl)
        
        # 分析技术壁垒
        barriers, barrier_level = self._analyze_barriers(text)
        
        # 识别领先玩家
        leaders = self._identify_leaders(text, theme_name)
        
        # 评估竞争格局
        competition = self._assess_competition(text, theme_name)
        
        # 中国能力评估
        china_cap = self._assess_china_capability(text, theme_name)
        
        # 提取催化剂
        catalysts = self._extract_catalysts(text)
        
        # 识别风险
        risks = self._identify_tech_risks(text, trl)
        
        return TechInsight(
            tech_name=theme_name,
            theme_name=theme_name,
            trl_level=trl,
            trl_score=trl.level * 11,
            industrialization_timeline=timeline,
            estimated_industrialization_date=ind_date,
            confidence=self._calculate_confidence(trl, barriers, leaders),
            technical_barriers=barriers,
            barrier_level=barrier_level,
            leading_players=leaders,
            competition_intensity=competition,
            china_capability=china_cap,
            catalysts=catalysts,
            risks=risks
        )
    
    def _assess_trl(self, text: str) -> TechnologyReadinessLevel:
        """评估技术成熟度"""
        scores = {trl: 0 for trl in TechnologyReadinessLevel}
        
        for trl, signals in self.TRL_SIGNALS.items():
            for signal in signals:
                if signal in text:
                    scores[trl] += 1
        
        # 特殊信号
        if any(kw in text for kw in ['量产', '批量生产', '规模化']):
            scores[TechnologyReadinessLevel.TRL9] += 3
        
        if any(kw in text for kw in ['中试', '试产', '试制']):
            scores[TechnologyReadinessLevel.TRL7] += 2
        
        if any(kw in text for kw in ['研发', '在研', '开发中']):
            scores[TechnologyReadinessLevel.TRL4] += 1
        
        max_score = max(scores.values())
        if max_score == 0:
            return TechnologyReadinessLevel.TRL4
        
        for trl, score in scores.items():
            if score == max_score:
                return trl
        
        return TechnologyReadinessLevel.TRL4
    
    def _predict_industrialization(self, theme_name: str, 
                                   current_trl: TechnologyReadinessLevel) -> Tuple[str, datetime]:
        """预测产业化时间"""
        timeline_ref = self.INDUSTRIALIZATION_TIMELINE.get(theme_name, {})
        
        if not timeline_ref:
            # 默认预测
            months_to_industry = (9 - current_trl.level) * 12
            if months_to_industry < 0:
                months_to_industry = 0
        else:
            if current_trl.level < 5:
                months_to_industry = timeline_ref.get('trl5_to_trl7', 24)
            elif current_trl.level < 7:
                months_to_industry = timeline_ref.get('trl7_to_trl9', 24)
            else:
                months_to_industry = 6
        
        future_date = datetime.now() + timedelta(days=months_to_industry * 30)
        
        timeline_map = {
            'lab': '实验室阶段',
            'verification': '验证阶段',
            'pilot': '中试阶段',
            'preproduction': '试产阶段',
            'production': '量产阶段'
        }
        
        if current_trl.level <= 4:
            phase = 'lab'
        elif current_trl.level <= 6:
            phase = 'verification'
        elif current_trl.level <= 7:
            phase = 'pilot'
        elif current_trl.level <= 8:
            phase = 'preproduction'
        else:
            phase = 'production'
        
        return timeline_map[phase], future_date
    
    def _analyze_barriers(self, text: str) -> Tuple[List[str], str]:
        """分析技术壁垒"""
        barriers = []
        barrier_level = 'medium'
        
        for level, keywords in self.BARRIER_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    barriers.append(kw)
                    barrier_level = level
        
        if not barriers:
            barriers = ['技术积累要求高']
        
        return list(set(barriers)), barrier_level
    
    def _identify_leaders(self, text: str, theme_name: str) -> List[str]:
        """识别领先玩家"""
        leaders = []
        known_leaders = self.LEADING_PLAYERS.get(theme_name, [])
        
        for leader in known_leaders:
            if leader in text:
                leaders.append(leader)
        
        return leaders[:5]
    
    def _assess_competition(self, text: str, theme_name: str) -> str:
        """评估竞争格局"""
        if any(kw in text for kw in ['一家独大', '垄断', '绝对领先']):
            return '低烈度'
        elif any(kw in text for kw in ['竞争激烈', '群雄逐鹿', '百家争鸣']):
            return '高烈度'
        elif any(kw in text for kw in ['头部集中', '主要玩家']):
            return '中等'
        return '中等'
    
    def _assess_china_capability(self, text: str, theme_name: str) -> str:
        """评估中国能力"""
        if any(kw in text for kw in ['国际领先', '世界先进', '全球首创', '打破垄断']):
            return '国际领先'
        elif any(kw in text for kw in ['国产替代', '自主可控', '国内领先']):
            return '国内领先'
        elif any(kw in text for kw in ['追赶中', '逐步缩小', '还有差距']):
            return '追赶中'
        elif any(kw in text for kw in ['依赖进口', '受制于人', '卡脖子']):
            return '受制于人'
        return '未知'
    
    def _extract_catalysts(self, text: str) -> List[str]:
        """提取技术催化剂"""
        catalysts = []
        
        catalyst_markers = [
            '发布会', '量产', '订单', '合作', '认证', '验收',
            '产业化', '商业化', '规模化', '产能释放'
        ]
        
        for marker in catalyst_markers:
            if marker in text:
                catalysts.append(marker)
        
        return catalysts[:5]
    
    def _identify_tech_risks(self, text: str, trl: TechnologyReadinessLevel) -> List[str]:
        """识别技术风险"""
        risks = []
        
        if trl.level < 5:
            risks.append('技术不成熟，产业化风险大')
        
        if any(kw in text for kw in ['成本高', '成本难降', '降本压力大']):
            risks.append('成本控制挑战')
        
        if any(kw in text for kw in ['良率', '成品率', '合格率']):
            risks.append('量产良率挑战')
        
        if any(kw in text for kw in ['专利', '知识产权', '侵权']):
            risks.append('知识产权风险')
        
        return risks
    
    def _calculate_confidence(self, trl: TechnologyReadinessLevel, 
                             barriers: List[str], leaders: List[str]) -> float:
        """计算置信度"""
        base = 0.5
        
        # TRL等级加成
        base += trl.level * 0.05
        
        # 壁垒明确加成
        if barriers:
            base += 0.1
        
        # 领先玩家明确加成
        if leaders:
            base += 0.15
        
        return min(base, 1.0)
    
    def generate_tech_report(self, insights: List[TechInsight]) -> str:
        """生成技术分析报告"""
        if not insights:
            return "🔬 暂无技术相关信息"
        
        parts = ["\n🔬 技术分析报告", "=" * 40]
        
        for insight in insights[:3]:
            parts.append(f"\n📊 {insight.tech_name}")
            parts.append(f"├ TRL等级: {insight.trl_level.level}级 ({insight.trl_level.name})")
            parts.append(f"├ 当前阶段: {insight.industrialization_timeline}")
            parts.append(f"├ 预计产业化: {insight.estimated_industrialization_date.strftime('%Y年%m月')}")
            parts.append(f"├ 技术壁垒: {insight.barrier_level} ({', '.join(insight.technical_barriers[:2])})")
            parts.append(f"├ 竞争格局: {insight.competition_intensity}")
            parts.append(f"├ 中国能力: {insight.china_capability}")
            
            if insight.leading_players:
                parts.append(f"└ 领先玩家: {', '.join(insight.leading_players[:3])}")
        
        return "\n".join(parts)
