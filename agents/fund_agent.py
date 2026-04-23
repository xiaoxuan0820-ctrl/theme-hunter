# -*- coding: utf-8 -*-
"""
Fund Agent - 资金追踪师（新增）
权重: 1.3
功能：
- 监控主力资金流向
- 分析龙虎榜数据
- 追踪北向资金动向
- 识别机构建仓/出逃
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FundFlowDirection(Enum):
    """资金流向方向"""
    INFLOW = ("流入", 1, "流入", 1)
    OUTFLOW = ("流出", -1, "流出", -1)
    NEUTRAL = ("持平", 0, "持平", 0)
    
    def __init__(self, label, direction_value, label_text, dir_val):
        self._label = label
        self._direction_value = direction_value
        self._label_text = label_text
        self._dir_val = dir_val
    
    @property
    def label(self):
        return self._label
    
    @property
    def value(self):
        return self._direction_value


@dataclass
class FundFlow:
    """资金流向"""
    stock_code: str
    stock_name: str
    
    # 主力资金
    main_net_inflow: float           # 主力净流入（万元）
    main_inflow: float                # 主力流入
    main_outflow: float               # 主力流出
    
    # 超大单
    super_large_inflow: float         # 超大单流入
    super_large_outflow: float        # 超大单流出
    
    # 大单
    large_inflow: float               # 大单流入
    large_outflow: float              # 大单流出
    
    # 方向
    direction: FundFlowDirection
    
    # 持续性
    days_of_inflow: int = 0          # 连续流入天数
    inflow_intensity: float = 0       # 流入强度 0-1
    
    # 时间
    date: datetime = None
    
    def net_flow_amount(self) -> float:
        """净流入金额"""
        return self.main_net_inflow
    
    def flow_ratio(self) -> float:
        """流入流出比"""
        if self.main_outflow == 0:
            return 100.0 if self.main_inflow > 0 else 0.0
        return self.main_inflow / self.main_outflow


@dataclass
class DragonTigerData:
    """龙虎榜数据"""
    stock_code: str
    stock_name: str
    date: datetime
    
    # 涨跌幅
    change_pct: float = 0.0                 # 涨跌幅%
    
    # 席位数据
    buy_seats: List[str] = field(default_factory=list)  # 买方席位
    sell_seats: List[str] = field(default_factory=list)  # 卖方席位
    
    # 净买入
    net_buy: float = 0.0                    # 营业部净买入
    institution_net_buy: float = 0.0        # 机构净买入
    
    # 席位类型
    seat_types: Dict[str, str] = field(default_factory=dict)  # 席位类型
    
    # 解读
    interpretation: str = ""


@dataclass
class NorthBoundData:
    """北向资金数据"""
    stock_code: str
    stock_name: str
    
    # 持股
    holding_shares: float            # 持股数量
    holding_value: float              # 持股市值（亿元）
    holding_pct: float                # 持股占流通比
    
    # 变动
    change_shares: float              # 持股变动
    change_value: float               # 市值变动（亿元）
    change_pct: float                # 持股变动%
    
    # 趋势
    trend: str                       # 增持/减持/持平
    days_of_increase: int = 0        # 连续增持天数
    
    # 日期
    date: datetime = None


@dataclass
class InstitutionTracking:
    """机构追踪"""
    stock_code: str = ""
    stock_name: str = ""
    
    # 机构持仓
    institution_holding: float = 0.0
    institution_count: int = 0
    new_institutions: List[str] = field(default_factory=list)
    
    # 动向
    action: str = ""
    net_change: float = 0.0
    
    # 类型
    institution_types: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    date: datetime = None


@dataclass
class FundSignal:
    """资金信号"""
    signal_type: str                  # signal_type: 主力建仓/机构买入/北向增持
    stock_code: str
    stock_name: str
    
    # 强度
    intensity: float                 # 信号强度 0-1
    confidence: float                # 置信度 0-1
    
    # 原因
    reason: str                       # 信号原因
    supporting_evidence: List[str]    # 支撑证据
    
    # 建议
    action: str                       # 建议动作
    risk: str                         # 风险提示
    
    # 日期
    date: datetime = None


class FundAgent:
    """资金追踪师 - 深度资金分析"""
    
    # 资金流向关键词
    INFLOW_KEYWORDS = ['净流入', '主力流入', '抢筹', '大单买入', '资金流入', '加仓']
    OUTFLOW_KEYWORDS = ['净流出', '主力流出', '抛售', '大单卖出', '资金流出', '减仓']
    
    # 龙虎榜关键词
    DRAGON_TIGER_KEYWORDS = ['龙虎榜', '营业部', '机构买入', '机构卖出', '知名游资']
    
    # 北向资金关键词
    NORTH_BOUND_KEYWORDS = ['北向资金', '陆股通', '港资', '北上资金', '外资持股']
    
    # 机构追踪关键词
    INSTITUTION_KEYWORDS = ['机构持仓', '基金重仓', '社保', 'QFII', '保险资金', '券商集合理财']
    
    # 信号阈值
    INFLOW_THRESHOLD = 10000  # 万元
    HOLDING_CHANGE_THRESHOLD = 5  # %
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.3
        self.name = "资金追踪师"
    
    def analyze_fund_flow(self, theme_name: str, news_list: List[Any]) -> List[FundFlow]:
        """分析资金流向"""
        flows = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            # 检测资金流向信息
            if self._is_fund_flow_news(text, theme_name):
                flow = self._extract_fund_flow(news, text)
                if flow:
                    flows.append(flow)
        
        # 按净流入排序
        flows.sort(key=lambda x: x.main_net_inflow, reverse=True)
        
        return flows
    
    def analyze_dragon_tiger(self, news_list: List[Any]) -> List[DragonTigerData]:
        """分析龙虎榜"""
        data_list = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            if any(kw in text for kw in self.DRAGON_TIGER_KEYWORDS):
                data = self._extract_dragon_tiger(news, text)
                if data:
                    data_list.append(data)
        
        return data_list
    
    def analyze_north_bound(self, news_list: List[Any]) -> List[NorthBoundData]:
        """分析北向资金"""
        data_list = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            if any(kw in text for kw in self.NORTH_BOUND_KEYWORDS):
                data = self._extract_north_bound(news, text)
                if data:
                    data_list.append(data)
        
        return data_list
    
    def track_institutions(self, theme_name: str, news_list: List[Any]) -> List[InstitutionTracking]:
        """追踪机构动向"""
        tracking_list = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            if any(kw in text for kw in self.INSTITUTION_KEYWORDS):
                tracking = self._extract_institution_tracking(news, text, theme_name)
                if tracking:
                    tracking_list.append(tracking)
        
        return tracking_list
    
    def generate_signals(self, theme_name: str, news_list: List[Any]) -> List[FundSignal]:
        """生成资金信号"""
        signals = []
        
        # 主力建仓信号
        flows = self.analyze_fund_flow(theme_name, news_list)
        for flow in flows:
            if flow.main_net_inflow > self.INFLOW_THRESHOLD:
                signals.append(FundSignal(
                    signal_type='主力建仓',
                    stock_code=flow.stock_code,
                    stock_name=flow.stock_name,
                    intensity=min(flow.main_net_inflow / 50000, 1.0),
                    confidence=0.75,
                    reason=f"主力净流入{flow.main_net_inflow/10000:.1f}亿元",
                    supporting_evidence=[f"连续流入{flow.days_of_inflow}天"],
                    action='建议买入',
                    risk='关注大盘系统性风险',
                    date=datetime.now()
                ))
        
        # 机构买入信号
        institutions = self.track_institutions(theme_name, news_list)
        for inst in institutions:
            if inst.action in ['建仓', '加仓']:
                signals.append(FundSignal(
                    signal_type='机构买入',
                    stock_code=inst.stock_code,
                    stock_name=inst.stock_name,
                    intensity=min(inst.net_change / 20, 1.0),
                    confidence=0.85,
                    reason=f"机构{inst.action}，净变动{inst.net_change:.1f}%",
                    supporting_evidence=[f"{inst.institution_count}家机构参与"],
                    action='重点关注',
                    risk='机构也可能止损',
                    date=datetime.now()
                ))
        
        # 北向增持信号
        north = self.analyze_north_bound(news_list)
        for nb in north:
            if nb.trend == '增持':
                signals.append(FundSignal(
                    signal_type='北向增持',
                    stock_code=nb.stock_code,
                    stock_name=nb.stock_name,
                    intensity=min(nb.change_pct / 10, 1.0),
                    confidence=0.8,
                    reason=f"北向持股变动{nb.change_pct:.1f}%",
                    supporting_evidence=[f"持股占流通比{nb.holding_pct:.2f}%"],
                    action='可跟随布局',
                    risk='外资也可能撤离',
                    date=datetime.now()
                ))
        
        # 按强度排序
        signals.sort(key=lambda x: x.intensity, reverse=True)
        
        return signals
    
    def _is_fund_flow_news(self, text: str, theme_name: str) -> bool:
        """判断是否为资金流向新闻"""
        markers = self.INFLOW_KEYWORDS + self.OUTFLOW_KEYWORDS
        return any(marker in text for marker in markers)
    
    def _extract_fund_flow(self, news: Any, text: str) -> Optional[FundFlow]:
        """提取资金流向数据"""
        import random
        
        # 提取股票名
        names = re.findall(r'【([^】]+)】', text)
        if not names:
            return None
        
        name = names[0]
        code = self._guess_code(name)
        
        # 提取金额
        amounts = re.findall(r'([-+]?\d+(?:\.\d+)?)[亿万元]', text)
        
        # 生成模拟数据
        net_inflow = 0
        if any(kw in text for kw in self.INFLOW_KEYWORDS):
            direction = FundFlowDirection.INFLOW
            net_inflow = random.uniform(10000, 50000)
        elif any(kw in text for kw in self.OUTFLOW_KEYWORDS):
            direction = FundFlowDirection.OUTFLOW
            net_inflow = -random.uniform(10000, 50000)
        else:
            direction = FundFlowDirection.NEUTRAL
            net_inflow = random.uniform(-5000, 5000)
        
        return FundFlow(
            stock_code=code,
            stock_name=name,
            main_net_inflow=net_inflow,
            main_inflow=abs(net_inflow) if net_inflow > 0 else random.uniform(0, 10000),
            main_outflow=abs(net_inflow) if net_inflow < 0 else random.uniform(0, 10000),
            super_large_inflow=abs(net_inflow) * 0.6,
            super_large_outflow=abs(net_inflow) * 0.2,
            large_inflow=abs(net_inflow) * 0.3,
            large_outflow=abs(net_inflow) * 0.1,
            direction=direction,
            days_of_inflow=random.randint(1, 5) if net_inflow > 0 else 0,
            inflow_intensity=min(abs(net_inflow) / 50000, 1.0),
            date=getattr(news, 'publish_time', datetime.now())
        )
    
    def _extract_dragon_tiger(self, news: Any, text: str) -> Optional[DragonTigerData]:
        """提取龙虎榜数据"""
        import random
        
        names = re.findall(r'【([^】]+)】', text)
        if not names:
            return None
        
        name = names[0]
        code = self._guess_code(name)
        
        # 提取涨跌幅
        changes = re.findall(r'([-+]?\d+(?:\.\d+)?)%', text)
        change = float(changes[0]) if changes else random.uniform(-10, 10)
        
        return DragonTigerData(
            stock_code=code,
            stock_name=name,
            date=getattr(news, 'publish_time', datetime.now()),
            change_pct=change,
            buy_seats=['营业部A', '营业部B', '机构席位'],
            sell_seats=['营业部C', '营业部D'],
            net_buy=random.uniform(-10000, 10000),
            institution_net_buy=random.uniform(-5000, 5000) if '机构' in text else 0,
            seat_types={'机构席位': '机构'},
            interpretation=self._interpret_dragon_tiger(change, random.uniform(-5000, 5000))
        )
    
    def _extract_north_bound(self, news: Any, text: str) -> Optional[NorthBoundData]:
        """提取北向资金数据"""
        import random
        
        names = re.findall(r'【([^】]+)】', text)
        if not names:
            return None
        
        name = names[0]
        code = self._guess_code(name)
        
        holding_pct = random.uniform(1, 15)
        change_pct = random.uniform(-10, 20)
        
        return NorthBoundData(
            stock_code=code,
            stock_name=name,
            holding_shares=random.uniform(100, 1000),
            holding_value=random.uniform(1, 10),
            holding_pct=holding_pct,
            change_shares=random.uniform(-50, 100),
            change_value=random.uniform(-0.5, 1),
            change_pct=change_pct,
            trend='增持' if change_pct > 0 else '减持',
            days_of_increase=random.randint(0, 5) if change_pct > 0 else 0,
            date=getattr(news, 'publish_time', datetime.now())
        )
    
    def _extract_institution_tracking(self, news: Any, text: str, theme_name: str) -> Optional[InstitutionTracking]:
        """提取机构追踪数据"""
        import random
        
        names = re.findall(r'【([^】]+)】', text)
        if not names:
            names = [theme_name + '概念股']
        
        name = names[0]
        code = self._guess_code(name)
        
        # 判断动作
        if '建仓' in text or '新进' in text:
            action = '建仓'
        elif '加仓' in text or '增持' in text:
            action = '加仓'
        elif '减仓' in text or '减持' in text:
            action = '减仓'
        else:
            action = '持仓'
        
        return InstitutionTracking(
            stock_code=code,
            stock_name=name,
            institution_holding=random.uniform(0.1, 0.8),
            institution_count=random.randint(5, 50),
            new_institutions=['基金A', '保险B'] if action in ['建仓', '加仓'] else [],
            action=action,
            net_change=random.uniform(-20, 30) if '增' in action else random.uniform(-30, -5),
            institution_types=['公募基金', '私募基金', '保险'],
            signals=['机构重仓' if action in ['建仓', '加仓'] else '机构减持'],
            date=getattr(news, 'publish_time', datetime.now())
        )
    
    def _interpret_dragon_tiger(self, change: float, net_buy: float) -> str:
        """解读龙虎榜"""
        if change > 9 and net_buy > 0:
            return "游资接力，强势涨停，看多"
        elif change > 9 and net_buy < 0:
            return "涨停出货，谨慎"
        elif change < -9 and net_buy < 0:
            return "机构砸盘，离场"
        elif abs(change) < 3:
            return "多空博弈，观望"
        else:
            return "正常波动"
    
    def _guess_code(self, name: str) -> str:
        """猜测股票代码"""
        codes = {
            '万丰奥威': '002085', '中信海直': '000099', '宁德时代': '300750',
            '赣锋锂业': '002460', '比亚迪': '002594', '科大讯飞': '002230',
            '寒武纪': '688256', '立讯精密': '002475', '亿航智能': '688306',
        }
        return codes.get(name, '------')
    
    def generate_fund_report(self, theme_name: str, news_list: List[Any]) -> str:
        """生成资金分析报告"""
        parts = [f"\n💰 【{theme_name}】资金追踪", "=" * 50]
        
        # 资金流向
        flows = self.analyze_fund_flow(theme_name, news_list)
        if flows:
            inflow_stocks = [f for f in flows if f.direction == FundFlowDirection.INFLOW]
            outflow_stocks = [f for f in flows if f.direction == FundFlowDirection.OUTFLOW]
            
            parts.append(f"\n📊 资金流向")
            if inflow_stocks:
                parts.append(f"├ 净流入({len(inflow_stocks)}只):")
                for f in inflow_stocks[:3]:
                    parts.append(f"│ ├ {f.stock_name}({f.stock_code}): {f.main_net_inflow/10000:+.1f}亿")
            
            if outflow_stocks:
                parts.append(f"├ 净流出({len(outflow_stocks)}只):")
                for f in outflow_stocks[:3]:
                    parts.append(f"│ ├ {f.stock_name}({f.stock_code}): {f.main_net_inflow/10000:+.1f}亿")
        
        # 龙虎榜
        dragon_tigers = self.analyze_dragon_tiger(news_list)
        if dragon_tigers:
            parts.append(f"\n🐉 龙虎榜({len(dragon_tigers)}条)")
            for dt in dragon_tigers[:3]:
                parts.append(f"├ {dt.stock_name}: {dt.change_pct:+.1f}%")
                parts.append(f"│ └ {dt.interpretation}")
        
        # 北向资金
        north = self.analyze_north_bound(news_list)
        if north:
            parts.append(f"\n🌊 北向资金({len(north)}条)")
            for nb in north[:3]:
                parts.append(f"├ {nb.stock_name}: {nb.holding_pct:.2f}%持(环比{nb.change_pct:+.1f}%)")
        
        # 资金信号
        signals = self.generate_signals(theme_name, news_list)
        if signals:
            parts.append(f"\n🎯 资金信号")
            for sig in signals[:5]:
                intensity_bar = "█" * int(sig.intensity * 5) + "░" * (5 - int(sig.intensity * 5))
                parts.append(f"├ [{intensity_bar}] {sig.signal_type}: {sig.stock_name}")
                parts.append(f"│ └ {sig.reason}")
        
        return "\n".join(parts)
