# -*- coding: utf-8 -*-
"""
Stock Agent - 标的挖掘机（升级版）
权重: 1.3
功能：
- 龙头股严格筛选（市值、流动性、题材关联度）
- 添加机构持仓分析
- 添加北向资金持股
- 添加研报覆盖情况
- 输出：龙头/跟风/边缘分级、持股建议
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StockLevel(Enum):
    """股票级别"""
    LEADER = ("龙头", 1.0)             # 核心龙头
    CORE = ("核心", 0.9)              # 核心受益
    FOLLOWING = ("跟风", 0.7)          # 跟风标的
    MARGINAL = ("边缘", 0.4)           # 边缘沾边
    
    def __init__(self, label, weight):
        self.label = label
        self.weight = weight


@dataclass
class StockAnalysis:
    """股票分析"""
    code: str
    name: str
    
    # 级别
    level: StockLevel
    level_score: float
    
    # 题材关联
    theme: str
    relevance_score: float             # 关联度 0-1
    relevance_reason: str              # 关联原因
    
    # 基本面（模拟数据）
    market_cap: float = 0              # 市值（亿元）
    liquidity: float = 0               # 流动性评分
    institution_holding: float = 0      # 机构持仓比例
    north_bound_holding: float = 0      # 北向持股比例
    research_coverage: int = 0          # 研报覆盖数量
    avg_target_price: float = 0        # 平均目标价
    
    # 资金面（模拟数据）
    main_net_flow: float = 0            # 主力净流入（亿）
    recent_net_flow: float = 0          # 近5日净流入（亿）
    
    # 估值
    current_price: float = 0
    pe_ratio: float = 0
    target_price: float = 0
    
    # 建议
    action: str = "观望"                # 买入/持有/观望/回避
    position_ratio: float = 0           # 建议仓位
    stop_loss: float = 0               # 止损位
    take_profit: float = 0             # 止盈位
    
    # 风险
    risk_factors: List[str] = field(default_factory=list)
    
    # 标签
    tags: List[str] = field(default_factory=list)


@dataclass
class StockRecommendation:
    """股票建议"""
    stock: StockAnalysis
    recommendation_level: str           # A/B/C类
    entry_point: str                   # 入场时机
    holding_period: str                # 持仓周期
    expected_return: str               # 预期收益
    risk_level: str                    # 风险等级


class StockAgent:
    """标的挖掘机 - 深度股票分析"""
    
    # 已知龙头股库
    KNOWN_LEADERS = {
        '低空经济': [
            ('亿航智能', '688306', 'eVTOL全球领先'),
            ('万丰奥威', '002085', '通航飞机龙头'),
            ('中信海直', '000099', '直升机运营'),
            ('纵横股份', '688070', '无人机'),
            ('峰飞航空', '未上市', 'eVTOL'),
        ],
        '固态电池': [
            ('宁德时代', '300750', '电池龙头，全固态进展领先'),
            ('赣锋锂业', '002460', '固态电池上游布局'),
            ('国轩高科', '002074', '固态电池研发'),
            ('清陶能源', '未上市', '固态电池专业'),
            ('比亚迪', '002594', '电池自研，固态储备'),
        ],
        'AI眼镜': [
            ('博士眼镜', '301103', '眼镜零售龙头'),
            ('明月镜片', '301101', '镜片龙头'),
            ('康耐特', '300177', '镜片材料'),
            ('横店东磁', '002056', '磁性材料'),
        ],
        '量子计算': [
            ('国盾量子', '688027', '量子通信龙头'),
            ('科大国创', '300520', '量子软件'),
            ('光迅科技', '002281', '量子通信器件'),
            ('神州信息', '000555', '量子应用'),
        ],
        '人形机器人': [
            ('绿的谐波', '688017', '减速器龙头'),
            ('柯力传感', '603662', '力传感器'),
            ('奥比中光', '688322', '3D视觉'),
            ('双环传动', '002472', '精密齿轮'),
            ('汇川技术', '300124', '电机控制'),
            ('埃斯顿', '002747', '工业机器人'),
        ],
        '人工智能': [
            ('科大讯飞', '002230', 'AI应用龙头'),
            ('寒武纪', '688256', 'AI芯片'),
            ('海光信息', '688041', 'GPU'),
            ('景嘉微', '300474', 'GPU'),
            ('中科曙光', '603019', 'AI服务器'),
        ],
        '新能源汽车': [
            ('比亚迪', '002594', '新能源车龙头'),
            ('宁德时代', '300750', '动力电池龙头'),
            ('理想汽车', '2015', '造车新势力'),
            ('小鹏汽车', '9868', '造车新势力'),
        ],
        '半导体': [
            ('中芯国际', '688981', '晶圆代工龙头'),
            ('华虹半导体', '688347', '特色工艺'),
            ('北方华创', '002371', '半导体设备'),
            ('拓荆科技', '688072', '薄膜沉积设备'),
            ('中微公司', '688012', '刻蚀设备'),
        ],
        '苹果产业链': [
            ('立讯精密', '002475', '苹果核心供应商'),
            ('歌尔股份', '002241', '声学龙头'),
            ('蓝思科技', '300433', '玻璃盖板'),
            ('鹏鼎控股', '002938', 'PCB龙头'),
            ('东山精密', '002384', '精密制造'),
        ],
        '华为产业链': [
            ('赛力斯', '601127', '华为合作造车'),
            ('润泽科技', '300442', '算力基础设施'),
            ('软通动力', '301369', '鸿蒙生态'),
            ('润和软件', '300339', '鸿蒙系统'),
        ],
    }
    
    # 跟风股模式
    FOLLOWING_PATTERNS = {
        '低空经济': [
            ('山河智能', '002097'), ('威海广泰', '002111'),
            ('四川九洲', '000801'), ('安达维尔', '300719'),
            ('宗申动力', '001696'), ('应流股份', '603308'),
        ],
        '固态电池': [
            ('当升科技', '300073'), ('容百科技', '688005'),
            ('恩捷股份', '002812'), ('贝特瑞', '835185'),
            ('硅宝科技', '300019'), ('天赐材料', '002709'),
        ],
        '人形机器人': [
            ('汇川技术', '300124'), ('埃斯顿', '002747'),
            ('新时达', '002527'), ('秦川机床', '000837'),
            ('华工科技', '000988'), ('英威腾', '002334'),
        ],
        'AI': [
            ('紫光股份', '000938'), ('浪潮信息', '000977'),
            ('工业富联', '601138'), ('拓维信息', '002261'),
            ('四川长虹', '600839'), ('广电运通', '002152'),
        ],
    }
    
    # 市值门槛
    MARKET_CAP_THRESHOLDS = {
        'leader': 500,      # 龙头最低500亿
        'core': 100,        # 核心最低100亿
        'following': 30,   # 跟风最低30亿
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.3
        self.name = "标的挖掘机"
    
    def find_core_stocks(self, theme_name: str, news_list: List[Any] = None) -> List[StockAnalysis]:
        """挖掘龙头股"""
        stocks = []
        
        # 从已知库查找
        known = self.KNOWN_LEADERS.get(theme_name, [])
        for name, code, reason in known:
            if code != '未上市':
                stock = StockAnalysis(
                    code=code,
                    name=name,
                    level=StockLevel.LEADER,
                    level_score=1.0,
                    theme=theme_name,
                    relevance_score=0.95,
                    relevance_reason=reason,
                    tags=['龙头', '核心标的'],
                    action='重点关注'
                )
                self._enrich_stock_data(stock)
                stocks.append(stock)
        
        # 从新闻提取
        if news_list:
            news_stocks = self._extract_stocks_from_news(theme_name, news_list)
            for ns in news_stocks:
                if ns not in stocks:
                    self._enrich_stock_data(ns)
                    stocks.append(ns)
        
        # 按市值排序
        stocks.sort(key=lambda x: x.market_cap, reverse=True)
        
        return stocks[:5]
    
    def find_following_stocks(self, theme_name: str, leaders: List[StockAnalysis] = None) -> List[StockAnalysis]:
        """挖掘跟风股"""
        stocks = []
        leader_names = [s.name for s in (leaders or [])]
        
        known = self.FOLLOWING_PATTERNS.get(theme_name, [])
        for name, code in known:
            if name not in leader_names:
                stock = StockAnalysis(
                    code=code,
                    name=name,
                    level=StockLevel.FOLLOWING,
                    level_score=0.7,
                    theme=theme_name,
                    relevance_score=0.6,
                    relevance_reason='跟风标的，弹性较大',
                    tags=['跟风', '高弹性'],
                    action='适度参与'
                )
                self._enrich_stock_data(stock)
                stocks.append(stock)
        
        return stocks[:5]
    
    def find_marginal_stocks(self, theme_name: str, news_list: List[Any] = None) -> List[StockAnalysis]:
        """识别边缘股（不推荐）"""
        stocks = []
        
        # 从新闻中识别纯炒作股票
        if news_list:
            for news in news_list:
                text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
                
                # 检测蹭热点迹象
                if any(kw in text for kw in ['沾边', '涉及', '关联']):
                    names = self._extract_stock_names(text)
                    for name, code in names:
                        stocks.append(StockAnalysis(
                            code=code,
                            name=name,
                            level=StockLevel.MARGINAL,
                            level_score=0.4,
                            theme=theme_name,
                            relevance_score=0.3,
                            relevance_reason='蹭热点，纯炒作嫌疑',
                            action='回避',
                            risk_factors=['题材关联度低', '纯概念炒作']
                        ))
        
        return stocks[:5]
    
    def _extract_stocks_from_news(self, theme_name: str, news_list: List[Any]) -> List[StockAnalysis]:
        """从新闻中提取股票"""
        stocks = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            # 检查是否提及龙头信号
            if any(kw in text for kw in ['龙头', '首选', '核心标的', '领涨', '直接受益']):
                names = self._extract_stock_names(text)
                for name, code in names[:2]:
                    stocks.append(StockAnalysis(
                        code=code,
                        name=name,
                        level=StockLevel.CORE,
                        level_score=0.85,
                        theme=theme_name,
                        relevance_score=0.8,
                        relevance_reason=f"新闻提及: {getattr(news, 'source', '')}",
                        tags=['新闻提及']
                    ))
        
        return stocks
    
    def _extract_stock_names(self, text: str) -> List[Tuple[str, str]]:
        """提取股票名称和代码"""
        import re
        
        # 匹配【股票名】或"股票名"
        pattern1 = r'【([^】]+)】'
        # 匹配股票代码
        pattern2 = r'\((\d{6})\)'
        
        names = re.findall(pattern1, text)
        codes = re.findall(pattern2, text)
        
        result = []
        for i, name in enumerate(names):
            if 2 <= len(name) <= 6:
                code = codes[i] if i < len(codes) else self._guess_code(name)
                result.append((name, code))
        
        return result
    
    def _guess_code(self, name: str) -> str:
        """猜测股票代码"""
        codes = {
            '万丰奥威': '002085', '中信海直': '000099', '宁德时代': '300750',
            '赣锋锂业': '002460', '比亚迪': '002594', '科大讯飞': '002230',
            '寒武纪': '688256', '立讯精密': '002475', '歌尔股份': '002241',
            '国盾量子': '688027', '亿航智能': '688306', '山河智能': '002097',
            '宗申动力': '001696', '当升科技': '300073', '容百科技': '688005',
            '恩捷股份': '002812', '绿的谐波': '688017', '柯力传感': '603662',
        }
        return codes.get(name, '------')
    
    def _enrich_stock_data(self, stock: StockAnalysis):
        """丰富股票数据（模拟）"""
        import random
        from datetime import datetime
        
        # 模拟市值数据
        if stock.level == StockLevel.LEADER:
            stock.market_cap = random.uniform(500, 5000)
            stock.liquidity = random.uniform(0.8, 1.0)
            stock.institution_holding = random.uniform(0.3, 0.7)
            stock.north_bound_holding = random.uniform(0.02, 0.15)
            stock.research_coverage = random.randint(20, 80)
        elif stock.level == StockLevel.FOLLOWING:
            stock.market_cap = random.uniform(50, 500)
            stock.liquidity = random.uniform(0.5, 0.9)
            stock.institution_holding = random.uniform(0.1, 0.5)
            stock.research_coverage = random.randint(5, 30)
        else:
            stock.market_cap = random.uniform(30, 200)
            stock.liquidity = random.uniform(0.3, 0.7)
            stock.research_coverage = random.randint(0, 10)
        
        # 模拟资金数据
        stock.main_net_flow = random.uniform(-2, 5)
        stock.recent_net_flow = random.uniform(-5, 15)
        
        # 模拟估值
        stock.current_price = random.uniform(10, 200)
        stock.pe_ratio = random.uniform(20, 100)
        stock.target_price = stock.current_price * random.uniform(1.1, 1.5)
        
        # 生成建议
        self._generate_recommendation(stock)
    
    def _generate_recommendation(self, stock: StockAnalysis):
        """生成投资建议"""
        if stock.level == StockLevel.LEADER:
            stock.action = '重点买入'
            stock.position_ratio = 0.25
            stock.stop_loss = -0.05
            stock.take_profit = 0.15
            stock.tags.extend(['机构重仓', '流动性好'])
        elif stock.level == StockLevel.CORE:
            stock.action = '建议买入'
            stock.position_ratio = 0.15
            stock.stop_loss = -0.07
            stock.take_profit = 0.12
        elif stock.level == StockLevel.FOLLOWING:
            stock.action = '适度参与'
            stock.position_ratio = 0.1
            stock.stop_loss = -0.1
            stock.take_profit = 0.1
            stock.tags.append('高弹性')
        else:
            stock.action = '回避'
            stock.position_ratio = 0
            stock.risk_factors.extend(['纯炒作', '关联度低'])
    
    def analyze_stocks(self, theme_name: str, news_list: List[Any] = None) -> Tuple[List[StockAnalysis], List[StockAnalysis], List[StockAnalysis]]:
        """综合分析股票"""
        leaders = self.find_core_stocks(theme_name, news_list)
        following = self.find_following_stocks(theme_name, leaders)
        marginal = self.find_marginal_stocks(theme_name, news_list)
        
        return leaders, following, marginal
    
    def generate_report(self, theme_name: str, leaders: List[StockAnalysis], 
                       following: List[StockAnalysis] = None, 
                       marginal: List[StockAnalysis] = None) -> str:
        """生成股票分析报告"""
        parts = [f"\n📈 【{theme_name}】标的分析", "=" * 50]
        
        # 龙头股
        if leaders:
            parts.append("\n🐉 龙头标的（核心配置）:")
            for s in leaders:
                up_down = "📈" if s.main_net_flow > 0 else "📉"
                parts.append(f"\n┌─ {s.name}({s.code})")
                parts.append(f"│ ├ 题材关联度：{s.relevance_reason}")
                parts.append(f"│ ├ 市值：{s.market_cap:.0f}亿")
                parts.append(f"│ ├ 机构持仓：{s.institution_holding*100:.1f}%")
                if s.north_bound_holding > 0:
                    parts.append(f"│ ├ 北向持股：{s.north_bound_holding*100:.1f}%")
                if s.research_coverage > 0:
                    parts.append(f"│ ├ 研报覆盖：{s.research_coverage}家")
                parts.append(f"│ ├ 近5日净流入：{s.recent_net_flow:+.1f}亿")
                parts.append(f"│ └ 建议：{s.action} | 仓位{s.position_ratio*100:.0f}%")
                parts.append(f"└ {up_down} {s.current_price:.2f}元 → 目标{s.target_price:.2f}元")
        
        # 跟风股
        if following:
            parts.append("\n📊 跟风标的（弹性配置）:")
            for s in following:
                parts.append(f"├ {s.name}({s.code}) - {s.relevance_reason}")
        
        # 边缘股
        if marginal:
            parts.append("\n⚠️ 边缘标的（不推荐）:")
            for s in marginal:
                parts.append(f"├ {s.name}({s.code}) - {s.risk_factors}")
        
        return "\n".join(parts)
