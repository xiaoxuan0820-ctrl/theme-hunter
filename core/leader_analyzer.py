# -*- coding: utf-8 -*-
"""
龙头股分析器（Leader Analyzer）
核心目标：找出题材龙头股，提供埋伏建议
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import yaml
import random

logger = logging.getLogger(__name__)


class RelevanceLevel(Enum):
    """关联度等级"""
    CORE = ("核心", 1.0)      # 直接受益，主营业务占比高
    HIGH = ("高度", 0.7)      # 产业链相关，有明确受益逻辑
    LOW = ("边缘", 0.4)       # 名称沾边，实际关联弱
    
    def __init__(self, label, score):
        self.label = label
        self.score = score


class LeaderLevel(Enum):
    """龙头等级"""
    S = (1, "S级", "核心龙头")  # 最核心、最先启动
    A = (2, "A级", "强势龙头")  # 强势跟风
    B = (3, "B级", "跟风标的")  # 跟风
    C = (4, "C级", "边缘标的")  # 不推荐
    
    def __init__(self, order, label, description):
        self._order = order
        self._label = label
        self._description = description
    
    @property
    def label(self):
        return self._label
    
    @property
    def description(self):
        return self._description


@dataclass
class LeaderStock:
    """龙头股"""
    code: str
    name: str
    
    # 角色定位
    role: str                       # 角色描述
    relevance: RelevanceLevel        # 关联度
    position: float                 # 建议仓位%
    
    # 价格信息
    current_price: float = 0        # 当前价格
    target_price: float = 0         # 目标价格
    stop_loss: float = 0           # 止损位
    
    # 基本面
    market_cap: float = 0          # 市值（亿）
    north_bound_holding: float = 0  # 北向持股%
    research_coverage: int = 0      # 研报数量
    
    # 资金面
    recent_inflow: float = 0        # 近5日净流入（亿）
    first_board_day: int = 0       # 首板天数（题材爆发后第几天）
    
    # 建议
    action: str = "重点关注"
    buy_strategy: str = ""          # 买入策略
    expected_return: str = ""       # 预期收益
    
    # 风险
    risk_factors: List[str] = field(default_factory=list)
    
    @property
    def level(self) -> LeaderLevel:
        """判断龙头等级"""
        if self.relevance == RelevanceLevel.CORE and self.position >= 25:
            return LeaderLevel.S
        elif self.relevance == RelevanceLevel.CORE or self.position >= 20:
            return LeaderLevel.A
        elif self.relevance == RelevanceLevel.HIGH:
            return LeaderLevel.B
        else:
            return LeaderLevel.C


@dataclass
class ThemeLeaders:
    """题材龙头分析结果"""
    theme_name: str
    theme_level: LeaderLevel        # 题材等级
    
    # 龙头股
    s_leaders: List[LeaderStock] = field(default_factory=list)   # S级龙头
    a_leaders: List[LeaderStock] = field(default_factory=list)   # A级龙头
    b_followers: List[LeaderStock] = field(default_factory=list) # B级跟风
    
    # 催化剂
    catalysts: List[str] = field(default_factory=list)
    catalyst_dates: List[datetime] = field(default_factory=list)
    
    # 埋伏时机
    ambush_window: str = ""
    best_entry: str = ""
    reason: str = ""
    
    # 风险
    risk_level: str = "low"
    max_position: float = 0.5       # 最大仓位


class LeaderAnalyzer:
    """龙头股分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载龙头股映射库
        leaders_path = Path(__file__).parent.parent / "config" / "theme_leaders.yaml"
        with open(leaders_path, 'r', encoding='utf-8') as f:
            self.theme_leaders = yaml.safe_load(f)
        
        self.leaders_map = self.theme_leaders.get('theme_leaders', {})
        self.evolution_chains = self.theme_leaders.get('evolution_chains', [])
    
    def find_leaders(self, theme_name: str, news_list: list = None) -> ThemeLeaders:
        """
        查找题材龙头股
        
        Args:
            theme_name: 题材名称
            news_list: 新闻列表（可选，用于实时分析）
        
        Returns:
            ThemeLeaders: 题材龙头分析结果
        """
        # 查找匹配的题材
        matched_theme = self._find_matching_theme(theme_name)
        
        if not matched_theme:
            # 没有预定义，通过规则识别
            return self._identify_leaders_by_rules(theme_name, news_list)
        
        theme_data = self.leaders_map[matched_theme]
        
        # 构建龙头股
        leaders = self._build_leaders(theme_data)
        
        # 获取题材等级
        theme_level_str = theme_data.get('theme_level', 'A')
        theme_level_map = {'S': LeaderLevel.S, 'A': LeaderLevel.A, 'B': LeaderLevel.B, 'C': LeaderLevel.C}
        theme_level = theme_level_map.get(theme_level_str, LeaderLevel.A)
        
        # 分类
        s_leaders = [s for s in leaders if s.position >= 25]
        a_leaders = [s for s in leaders if 15 <= s.position < 25]
        b_followers = [s for s in leaders if s.position < 15]
        
        # 催化剂
        catalysts = theme_data.get('catalysts', [])
        
        # 埋伏时机
        ambush_window, best_entry, reason = self._calculate_ambush_timing(
            leaders, catalysts, theme_data.get('trigger', '')
        )
        
        # 风险评估
        risk_level, max_position = self._assess_risk(leaders)
        
        return ThemeLeaders(
            theme_name=theme_name,
            theme_level=theme_level,
            s_leaders=s_leaders,
            a_leaders=a_leaders,
            b_followers=b_followers,
            catalysts=catalysts,
            catalyst_dates=[datetime.now() + timedelta(days=random.randint(1, 30)) for _ in catalysts],
            ambush_window=ambush_window,
            best_entry=best_entry,
            reason=reason,
            risk_level=risk_level,
            max_position=max_position
        )
    
    def _find_matching_theme(self, theme_name: str) -> Optional[str]:
        """查找匹配的题材"""
        theme_lower = theme_name.lower()
        
        # 精确匹配
        if theme_name in self.leaders_map:
            return theme_name
        
        # 关键词匹配
        for theme_key in self.leaders_map:
            keywords = theme_key.split('/')
            for kw in keywords:
                if kw in theme_name or theme_name in kw:
                    return theme_key
        
        return None
    
    def _build_leaders(self, theme_data: dict) -> List[LeaderStock]:
        """构建龙头股"""
        leaders = []
        
        # S级龙头
        for leader_data in theme_data.get('leaders', []):
            leader = self._create_leader(leader_data, 'S')
            if leader:
                leaders.append(leader)
        
        # 跟风股
        for follower_data in theme_data.get('followers', []):
            follower = self._create_leader(follower_data, 'B')
            if follower:
                leaders.append(follower)
        
        return leaders
    
    def _create_leader(self, stock_data: dict, default_level: str) -> Optional[LeaderStock]:
        """创建龙头股对象"""
        code = stock_data.get('code', '')
        name = stock_data.get('name', '')
        
        if not code or not name:
            return None
        
        # 解析关联度
        relevance_str = stock_data.get('relevance', 'high')
        relevance_map = {'core': RelevanceLevel.CORE, 'high': RelevanceLevel.HIGH, 'low': RelevanceLevel.LOW}
        relevance = relevance_map.get(relevance_str.lower(), RelevanceLevel.HIGH)
        
        # 生成价格（模拟）
        current_price = random.uniform(10, 200)
        
        leader = LeaderStock(
            code=code,
            name=name,
            role=stock_data.get('role', ''),
            relevance=relevance,
            position=stock_data.get('position', 20),
            current_price=current_price,
            target_price=current_price * random.uniform(1.1, 1.5),
            stop_loss=current_price * random.uniform(0.92, 0.97),
            market_cap=random.uniform(100, 5000),
            north_bound_holding=random.uniform(2, 15),
            research_coverage=random.randint(5, 50),
            recent_inflow=random.uniform(-2, 10),
            first_board_day=random.randint(0, 3),
            buy_strategy=f"回调至{current_price * 0.98:.1f}-{current_price:.1f}元",
            expected_return=f"{(current_price * 1.2 / current_price - 1) * 100:.0f}-{(current_price * 1.4 / current_price - 1) * 100:.0f}%"
        )
        
        # 设置操作建议
        if leader.level == LeaderLevel.S:
            leader.action = "重点买入"
        elif leader.level == LeaderLevel.A:
            leader.action = "建议买入"
        elif leader.level == LeaderLevel.B:
            leader.action = "适度参与"
        else:
            leader.action = "不推荐"
        
        return leader
    
    def _calculate_ambush_timing(self, leaders: List[LeaderStock], 
                                  catalysts: List[str], trigger: str) -> Tuple[str, str, str]:
        """计算埋伏时机"""
        # 检查龙头股状态
        s_leaders = [s for s in leaders if s.level == LeaderLevel.S]
        
        if not s_leaders:
            return "等待龙头股启动", "观望", "龙头股尚未启动"
        
        # 检查首板时间
        first_board_days = [s.first_board_day for s in s_leaders]
        avg_first_board = sum(first_board_days) / len(first_board_days)
        
        if avg_first_board <= 1:
            # 龙头刚启动，立即埋伏
            ambush_window = "现在！"
            best_entry = "今日尾盘或明日开盘"
            reason = "龙头刚启动，预期差最大"
        elif avg_first_board <= 3:
            # 龙头启动3天内，仍有空间
            ambush_window = "催化剂前3-5天"
            best_entry = "回调时买入"
            reason = "龙头已启动，寻找回调机会"
        elif catalysts:
            # 有催化剂，提前布局
            ambush_window = "催化剂前7天"
            best_entry = "催化剂前分批建仓"
            reason = "催化剂驱动，提前埋伏"
        else:
            # 持续炒作
            ambush_window = "持续关注"
            best_entry = "回调低吸"
            reason = "题材持续，逢低参与"
        
        return ambush_window, best_entry, reason
    
    def _assess_risk(self, leaders: List[LeaderStock]) -> Tuple[str, float]:
        """评估风险"""
        if not leaders:
            return "medium", 0.3
        
        # 检查龙头股涨幅
        avg_return = sum((s.target_price / s.current_price - 1) for s in leaders) / len(leaders)
        
        # 检查资金流入
        avg_inflow = sum(s.recent_inflow for s in leaders) / len(leaders)
        
        # 风险判断
        if avg_return > 0.5:
            risk_level = "high"
            max_position = 0.3
        elif avg_return > 0.3:
            risk_level = "medium"
            max_position = 0.4
        else:
            risk_level = "low"
            max_position = 0.5
        
        # 资金流出增加风险
        if avg_inflow < 0:
            risk_level = "high"
            max_position = 0.2
        
        return risk_level, max_position
    
    def _identify_leaders_by_rules(self, theme_name: str, 
                                   news_list: list = None) -> ThemeLeaders:
        """通过规则识别龙头股"""
        # 从新闻中提取股票
        stocks = []
        
        if news_list:
            for news in news_list:
                text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
                
                # 提取股票名
                import re
                names = re.findall(r'【([^】]+)】', text)
                
                for name in names[:3]:
                    code = self._guess_code(name)
                    
                    # 判断关联度
                    if any(kw in text for kw in ['龙头', '首选', '核心', '直接受益']):
                        relevance = RelevanceLevel.CORE
                        position = 25
                    elif any(kw in text for kw in ['相关', '受益', '涉及']):
                        relevance = RelevanceLevel.HIGH
                        position = 15
                    else:
                        relevance = RelevanceLevel.LOW
                        position = 5
                    
                    stocks.append(LeaderStock(
                        code=code,
                        name=name,
                        role=f"新闻提及龙头",
                        relevance=relevance,
                        position=position,
                        current_price=random.uniform(10, 200),
                        target_price=random.uniform(10, 200) * 1.2,
                        stop_loss=random.uniform(10, 200) * 0.95,
                        buy_strategy="回调买入"
                    ))
        
        return ThemeLeaders(
            theme_name=theme_name,
            theme_level=LeaderLevel.A,
            s_leaders=[],
            a_leaders=stocks[:3],
            b_followers=stocks[3:],
            catalysts=[],
            ambush_window="待确认",
            best_entry="观望",
            reason="题材刚发现，需进一步确认",
            risk_level="medium",
            max_position=0.3
        )
    
    def _guess_code(self, name: str) -> str:
        """猜测股票代码"""
        codes = {
            '中国石油': '601857', '中国石化': '600028', '中海油服': '601808',
            '紫金矿业': '601899', '山东黄金': '600547', '西部矿业': '601168',
            '隆基绿能': '601012', '通威股份': '600438', '晶澳科技': '002459',
            '宁德时代': '300750', '比亚迪': '002594', '赣锋锂业': '002460',
            '科大讯飞': '002230', '寒武纪': '688256', '海光信息': '688041',
            '浪潮信息': '000977', '中科曙光': '603019', '工业富联': '601138',
            '中芯国际': '688981', '北方华创': '002371', '中微公司': '688012',
            '亿航智能': '688306', '万丰奥威': '002085', '中信海直': '000099',
            '绿的谐波': '688017', '柯力传感': '603662', '汇川技术': '300124',
            '立讯精密': '002475', '歌尔股份': '002241', '蓝思科技': '300433',
            '赛力斯': '601127', '拓维信息': '002261', '软通动力': '301369',
            '牧原股份': '002714', '温氏股份': '300498', '新希望': '000876',
            '中远海控': '601919', '招商轮船': '601872'
        }
        return codes.get(name, '------')
    
    def generate_leader_report(self, theme_name: str, news_list: list = None) -> str:
        """生成龙头股报告"""
        leaders = self.find_leaders(theme_name, news_list)
        
        parts = [f"\n🎯 【{theme_name}】龙头埋伏机会"]
        parts.append(f"{'━' * 50}")
        
        # 题材状态
        parts.append(f"\n📌 题材等级: {leaders.theme_level.label}级")
        parts.append(f"├ 催化剂: {', '.join(leaders.catalysts[:3]) if leaders.catalysts else '待确认'}")
        parts.append(f"├ 埋伏窗口: {leaders.ambush_window}")
        parts.append(f"├ 最佳买点: {leaders.best_entry}")
        parts.append(f"├ 风险等级: {leaders.risk_level.upper()}")
        parts.append(f"└ 最大仓位: {leaders.max_position*100:.0f}%")
        
        # S级龙头
        if leaders.s_leaders:
            parts.append(f"\n💰 【S级龙头】核心配置")
            for i, stock in enumerate(leaders.s_leaders):
                rank_emoji = ['🥇', '🥈', '🥉'][i] if i < 3 else '▫️'
                parts.append(f"\n{rank_emoji} {stock.name}({stock.code})")
                parts.append(f"┌──────────────────────────────────────┐")
                parts.append(f"│ 角色: {stock.role[:30]}")
                parts.append(f"│ 关联度: {stock.relevance.label}")
                parts.append(f"│ 当前价: {stock.current_price:.2f}元")
                parts.append(f"│ 建议买入: {stock.buy_strategy}")
                parts.append(f"│ 止损位: {stock.stop_loss:.2f}元 ({(stock.stop_loss/stock.current_price-1)*100:.0f}%)")
                parts.append(f"│ 止盈位: {stock.target_price:.2f}元 ({(stock.target_price/stock.current_price-1)*100:.0f}%)")
                parts.append(f"└ 预期收益: {stock.expected_return}")
        
        # A级龙头
        if leaders.a_leaders:
            parts.append(f"\n📊 【A级龙头】强势配置")
            for stock in leaders.a_leaders[:3]:
                parts.append(f"├ {stock.name}({stock.code}) | 仓位{stock.position}%")
                parts.append(f"│ └ {stock.action}")
        
        # B级跟风
        if leaders.b_followers:
            parts.append(f"\n📈 【B级跟风】弹性配置")
            for stock in leaders.b_followers[:3]:
                parts.append(f"├ {stock.name}({stock.code}) | 仓位{stock.position}%")
        
        # 理由
        parts.append(f"\n💡 埋伏逻辑")
        parts.append(f"└ {leaders.reason}")
        
        return "\n".join(parts)


from datetime import timedelta
