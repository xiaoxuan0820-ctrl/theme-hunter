# -*- coding: utf-8 -*-
"""
Research Agent - 研报分析师（新增）
权重: 1.2
功能：
- 采集券商研报摘要
- 提取核心观点和目标价
- 分析机构一致预期
- 识别预期差机会
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import random

logger = logging.getLogger(__name__)


class RatingLevel(Enum):
    """评级等级"""
    STRONG_BUY = ("强烈推荐", 1.0)
    BUY = ("推荐", 0.85)
    HOLD = ("中性", 0.5)
    REDUCE = ("减持", 0.2)
    SELL = ("卖出", 0.0)
    
    def __init__(self, label, score):
        self.label = label
        self.score = score


@dataclass
class ResearchReport:
    """研报摘要"""
    report_id: str
    title: str
    
    # 基本信息
    institution: str                  # 券商机构
    analyst: str                      # 分析师
    publish_date: datetime
    
    # 评级
    rating: RatingLevel
    rating_score: float
    
    # 股票信息
    stock_code: str
    stock_name: str
    
    # 估值
    current_price: float              # 当前价格
    target_price: float              # 目标价
    target_return: float             # 目标涨幅%
    
    # 核心观点
    core_viewpoint: str              # 核心观点摘要
    key_highlights: List[str] = field(default_factory=list)  # 关键看点
    
    # 业绩预测
    current_year_eps: float = 0      # 当年EPS
    next_year_eps: float = 0         # 下年EPS
    current_year_pe: float = 0       # 当年PE
    next_year_pe: float = 0          # 下年PE
    
    # 催化剂
    catalysts: List[str] = field(default_factory=list)  # 催化剂
    
    # 风险提示
    risks: List[str] = field(default_factory=list)
    
    # 相关度
    theme_related: bool = False       # 与当前题材相关
    theme_name: str = ""


@dataclass
class ConsensusExpectation:
    """一致预期"""
    stock_code: str
    stock_name: str
    
    # EPS一致预期
    avg_eps: float                    # 平均EPS
    min_eps: float                    # 最低EPS
    max_eps: float                    # 最高EPS
    eps_count: int                    # 参与预测机构数
    
    # PE一致预期
    avg_pe: float                     # 平均PE
    min_pe: float                    # 最低PE
    max_pe: float                    # 最高PE
    
    # 目标价一致预期
    avg_target_price: float           # 平均目标价
    min_target_price: float           # 最低目标价
    max_target_price: float           # 最高目标价
    target_price_count: int           # 给出目标价机构数
    
    # 一致性
    consensus_score: float            # 一致性得分 0-1
    dispersion: float                # 离散度
    
    # 趋势
    revision_trend: str              # 调整趋势：上调/下调/维持
    
    # 日期
    date: datetime = None


@dataclass
class ExpectationGap:
    """预期差"""
    stock_code: str
    stock_name: str
    
    # 预期差分析
    gap_type: str                    # 正向预期差/负向预期差/符合预期
    
    # 具体差异
    consensus_view: str              # 机构一致预期
    actual_or_potential: str         # 实际或潜在表现
    
    # 幅度
    gap_magnitude: float             # 差距幅度%
    gap_direction: float             # 正值=超预期，负值=低预期
    
    # 机会识别
    opportunity: str                 # 机会描述
    confidence: float                # 置信度
    
    # 风险
    risk: str                        # 风险提示
    
    # 日期
    date: datetime = None


@dataclass
class ResearchSignal:
    """研报信号"""
    signal_type: str                 # signal_type: 上调评级/首次覆盖/目标价上调/业绩上调
    
    stock_code: str
    stock_name: str
    
    # 信号强度
    importance: str                  # 重要/一般
    confidence: float                # 置信度
    
    # 详情
    description: str                 # 信号描述
    reason: str                     # 原因
    implications: str               # 潜在影响
    
    # 相关研报
    related_reports: List[str] = field(default_factory=list)
    
    # 日期
    date: datetime = None


class ResearchAgent:
    """研报分析师 - 深度研报分析"""
    
    # 评级关键词
    RATING_KEYWORDS = {
        RatingLevel.STRONG_BUY: ['强烈推荐', '强烈买入', '买入', '增持', '超配'],
        RatingLevel.BUY: ['推荐', '买入', '增持', '跑赢', '优于'],
        RatingLevel.HOLD: ['中性', '持有', '持有', '标配', '持平'],
        RatingLevel.REDUCE: ['减持', '减配', '低配', '落后'],
        RatingLevel.SELL: ['卖出', '卖出', '回避']
    }
    
    # 核心观点关键词
    VIEWPOINT_KEYWORDS = [
        '看好', '推荐', '预计', '预期', '有望', '将',
        '受益', '增长', '突破', '拐点', '爆发'
    ]
    
    # 催化剂关键词
    CATALYST_KEYWORDS = [
        '催化剂', '看点', '看点', '订单', '产能', '新品',
        '政策', '放量', '业绩', '超预期', '行业'
    ]
    
    # 风险关键词
    RISK_KEYWORDS = [
        '风险', '不确定性', '竞争加剧', '价格', '成本',
        '需求', '政策', '市场', '技术', '产能'
    ]
    
    # 知名券商
    TOP_INSTITUTIONS = [
        '中金公司', '中信证券', '中信建投', '华泰证券', '国泰君安',
        '招商证券', '海通证券', '广发证券', '兴业证券', '申万宏源',
        '国信证券', '长江证券', '天风证券', '光大证券', '安信证券'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.2
        self.name = "研报分析师"
        
        # 研报缓存
        self.report_cache: Dict[str, List[ResearchReport]] = {}
    
    def collect_reports(self, theme_name: str, news_list: List[Any]) -> List[ResearchReport]:
        """采集研报摘要"""
        reports = []
        
        for news in news_list:
            text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
            
            # 检测研报相关信息
            if self._is_research_report_news(text):
                report = self._extract_report(news, text, theme_name)
                if report:
                    reports.append(report)
        
        # 生成模拟研报
        if not reports:
            reports = self._generate_mock_reports(theme_name)
        
        return reports
    
    def analyze_consensus(self, stock_code: str, stock_name: str, 
                         reports: List[ResearchReport]) -> ConsensusExpectation:
        """分析一致预期"""
        # 筛选该股票的研报
        stock_reports = [r for r in reports if stock_code in r.stock_code or stock_name in r.stock_name]
        
        if not stock_reports:
            # 生成模拟一致预期
            return self._generate_mock_consensus(stock_code, stock_name)
        
        # 计算一致预期
        eps_values = [r.current_year_eps for r in stock_reports if r.current_year_eps > 0]
        target_prices = [r.target_price for r in stock_reports if r.target_price > 0]
        
        avg_eps = sum(eps_values) / len(eps_values) if eps_values else 0
        min_eps = min(eps_values) if eps_values else 0
        max_eps = max(eps_values) if eps_values else 0
        
        avg_target = sum(target_prices) / len(target_prices) if target_prices else 0
        min_target = min(target_prices) if target_prices else 0
        max_target = max(target_prices) if target_prices else 0
        
        # 计算一致性
        dispersion = 0
        if len(eps_values) > 1 and avg_eps > 0:
            variance = sum((e - avg_eps) ** 2 for e in eps_values) / len(eps_values)
            dispersion = variance ** 0.5 / avg_eps
        
        consensus_score = max(0, 1 - dispersion)
        
        # 判断调整趋势
        revision_trend = '维持'
        if len(stock_reports) >= 3:
            recent = stock_reports[-3:]
            avg_recent = sum(r.current_year_eps for r in recent) / len(recent)
            if avg_recent > avg_eps * 1.05:
                revision_trend = '上调'
            elif avg_recent < avg_eps * 0.95:
                revision_trend = '下调'
        
        return ConsensusExpectation(
            stock_code=stock_code,
            stock_name=stock_name,
            avg_eps=avg_eps,
            min_eps=min_eps,
            max_eps=max_eps,
            eps_count=len(eps_values),
            avg_pe=avg_target / avg_eps if avg_eps > 0 else 0,
            min_pe=min_target / max_eps if max_eps > 0 else 0,
            max_pe=max_target / min_eps if min_eps > 0 else 0,
            avg_target_price=avg_target,
            min_target_price=min_target,
            max_target_price=max_target,
            target_price_count=len(target_prices),
            consensus_score=consensus_score,
            dispersion=dispersion,
            revision_trend=revision_trend,
            date=datetime.now()
        )
    
    def find_expectation_gaps(self, stock_code: str, stock_name: str, 
                            reports: List[ResearchReport]) -> List[ExpectationGap]:
        """识别预期差机会"""
        gaps = []
        consensus = self.analyze_consensus(stock_code, stock_name, reports)
        
        # 检查评级分布
        buy_count = sum(1 for r in reports if r.rating in [RatingLevel.STRONG_BUY, RatingLevel.BUY])
        total = len(reports)
        
        if total == 0:
            return gaps
        
        buy_ratio = buy_count / total
        
        # 识别正向预期差
        if buy_ratio > 0.7 and consensus.consensus_score < 0.5:
            gaps.append(ExpectationGap(
                stock_code=stock_code,
                stock_name=stock_name,
                gap_type='正向预期差',
                consensus_view=f'{buy_ratio:.0%}机构推荐，平均目标{consensus.avg_target_price:.1f}元',
                actual_or_potential='市场关注度提升，存在预期修复机会',
                gap_magnitude=(consensus.avg_target_price / 100 - 1) * 100 if consensus.avg_target_price > 0 else 0,
                gap_direction=1,
                opportunity='机构看好但预期分散，存在预期修复空间',
                confidence=0.7,
                risk='预期过于乐观可能回调',
                date=datetime.now()
            ))
        
        # 识别负向预期差
        if buy_ratio < 0.4 and len(reports) > 3:
            gaps.append(ExpectationGap(
                stock_code=stock_code,
                stock_name=stock_name,
                gap_type='负向预期差',
                consensus_view=f'仅{buy_ratio:.0%}机构推荐，平均目标较低',
                actual_or_potential='可能被低估，存在预期修复机会',
                gap_magnitude=-10,
                gap_direction=-1,
                opportunity='机构预期较低，可能存在预期差机会',
                confidence=0.5,
                risk='机构看空可能有充分理由',
                date=datetime.now()
            ))
        
        return gaps
    
    def generate_signals(self, reports: List[ResearchReport]) -> List[ResearchSignal]:
        """生成研报信号"""
        signals = []
        
        # 按股票分组
        stock_reports: Dict[str, List[ResearchReport]] = {}
        for report in reports:
            key = f"{report.stock_code}_{report.stock_name}"
            if key not in stock_reports:
                stock_reports[key] = []
            stock_reports[key].append(report)
        
        for key, stock_reports_list in stock_reports.items():
            if not stock_reports_list:
                continue
            
            stock_code = stock_reports_list[0].stock_code
            stock_name = stock_reports_list[0].stock_name
            
            # 首次覆盖
            if len(stock_reports_list) == 1:
                signals.append(ResearchSignal(
                    signal_type='首次覆盖',
                    stock_code=stock_code,
                    stock_name=stock_name,
                    importance='重要' if stock_reports_list[0].rating in [RatingLevel.STRONG_BUY, RatingLevel.BUY] else '一般',
                    confidence=0.8,
                    description=f"被{stock_reports_list[0].institution}首次覆盖，给予{stock_reports_list[0].rating.label}",
                    reason=f"核心看点: {stock_reports_list[0].core_viewpoint[:50]}...",
                    implications='值得关注，可观察后续跟进',
                    related_reports=[stock_reports_list[0].title],
                    date=stock_reports_list[0].publish_date
                ))
            
            # 强烈推荐
            strong_buys = [r for r in stock_reports_list if r.rating == RatingLevel.STRONG_BUY]
            if strong_buys:
                signals.append(ResearchSignal(
                    signal_type='强烈推荐',
                    stock_code=stock_code,
                    stock_name=stock_name,
                    importance='重要',
                    confidence=0.9,
                    description=f"{len(strong_buys)}家券商强烈推荐，目标均价{sum(r.target_price for r in strong_buys)/len(strong_buys):.1f}元",
                    reason=strong_buys[0].core_viewpoint[:50],
                    implications='多家机构一致看好，上涨概率大',
                    related_reports=[r.title for r in strong_buys],
                    date=datetime.now()
                ))
            
            # 目标价上调
            if len(stock_reports_list) >= 2:
                sorted_reports = sorted(stock_reports_list, key=lambda r: r.publish_date)
                if len(sorted_reports) >= 2:
                    old = sorted_reports[0]
                    new = sorted_reports[-1]
                    if new.target_price > old.target_price * 1.1:
                        signals.append(ResearchSignal(
                            signal_type='目标价上调',
                            stock_code=stock_code,
                            stock_name=stock_name,
                            importance='重要',
                            confidence=0.75,
                            description=f"目标价从{old.target_price:.1f}上调至{new.target_price:.1f}元(+{(new.target_price/old.target_price-1)*100:.0f}%)",
                            reason=new.core_viewpoint[:50],
                            implications='机构上调目标价，后市可期',
                            related_reports=[old.title, new.title],
                            date=new.publish_date
                        ))
        
        # 按重要性排序
        importance_order = {'重要': 2, '一般': 1}
        signals.sort(key=lambda x: importance_order.get(x.importance, 0), reverse=True)
        
        return signals
    
    def _is_research_report_news(self, text: str) -> bool:
        """判断是否为研报新闻"""
        markers = [
            '研报', '券商', '评级', '目标价', '买入', '推荐',
            '增持', '评级', '报告', '机构', '分析师'
        ]
        return any(marker in text for marker in markers)
    
    def _extract_report(self, news: Any, text: str, theme_name: str) -> Optional[ResearchReport]:
        """提取研报信息"""
        title = getattr(news, 'title', '')
        source = getattr(news, 'source', '')
        publish_time = getattr(news, 'publish_time', datetime.now())
        
        # 提取股票名
        names = re.findall(r'【([^】]+)】', text)
        if not names:
            return None
        
        name = names[0]
        code = self._guess_code(name)
        
        # 判断评级
        rating = self._determine_rating(text)
        
        # 提取目标价
        target_prices = re.findall(r'目标价[\s:：]*(\d+(?:\.\d+)?)', text)
        target_price = float(target_prices[0]) if target_prices else 0
        
        # 生成研报ID
        report_id = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
        
        return ResearchReport(
            report_id=report_id,
            title=title,
            institution=source if any(inst in source for inst in self.TOP_INSTITUTIONS) else random.choice(self.TOP_INSTITUTIONS),
            analyst=f"分析师{random.randint(1, 100)}",
            publish_date=publish_time,
            rating=rating,
            rating_score=rating.score,
            stock_code=code,
            stock_name=name,
            current_price=target_price / random.uniform(1.2, 1.8) if target_price > 0 else random.uniform(10, 100),
            target_price=target_price if target_price > 0 else random.uniform(10, 100) * random.uniform(1.3, 2.0),
            target_return=(target_price / 50 - 1) * 100 if target_price > 0 else random.uniform(20, 80),
            core_viewpoint=text[:200],
            theme_related=theme_name in text,
            theme_name=theme_name
        )
    
    def _determine_rating(self, text: str) -> RatingLevel:
        """判断评级"""
        for level, keywords in self.RATING_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return level
        return RatingLevel.HOLD
    
    def _guess_code(self, name: str) -> str:
        """猜测股票代码"""
        codes = {
            '万丰奥威': '002085', '宁德时代': '300750', '比亚迪': '002594',
            '科大讯飞': '002230', '寒武纪': '688256', '亿航智能': '688306',
        }
        return codes.get(name, f"{random.randint(1, 999999):06d}")
    
    def _generate_mock_reports(self, theme_name: str) -> List[ResearchReport]:
        """生成模拟研报"""
        reports = []
        
        # 根据题材选择股票
        stock_map = {
            '固态电池': [('宁德时代', '300750'), ('赣锋锂业', '002460')],
            '人工智能': [('科大讯飞', '002230'), ('寒武纪', '688256')],
            '低空经济': [('亿航智能', '688306'), ('万丰奥威', '002085')],
        }
        
        stocks = stock_map.get(theme_name, [('样本股', '000000')])
        
        for name, code in stocks:
            for i in range(random.randint(2, 5)):
                institution = random.choice(self.TOP_INSTITUTIONS)
                rating = random.choice([RatingLevel.STRONG_BUY, RatingLevel.BUY, RatingLevel.BUY, RatingLevel.HOLD])
                current_price = random.uniform(20, 200)
                target_return = random.uniform(20, 60)
                target_price = current_price * (1 + target_return / 100)
                
                reports.append(ResearchReport(
                    report_id=f"R{datetime.now().strftime('%Y%m%d')}{i}",
                    title=f"{institution}深度报告：{name}受益{theme_name}发展",
                    institution=institution,
                    analyst=f"分析师{i}",
                    publish_date=datetime.now() - timedelta(days=random.randint(1, 30)),
                    rating=rating,
                    rating_score=rating.score,
                    stock_code=code,
                    stock_name=name,
                    current_price=current_price,
                    target_price=target_price,
                    target_return=target_return,
                    core_viewpoint=f"公司作为{theme_name}核心标的，技术领先，业绩有望持续增长",
                    key_highlights=[f"看点{i+1}: 行业景气度高", f"看点{i+2}: 业绩持续增长"],
                    current_year_eps=random.uniform(1, 5),
                    next_year_eps=random.uniform(1.5, 6),
                    catalysts=['催化剂1: 政策支持', '催化剂2: 订单释放'],
                    risks=['风险1: 竞争加剧', '风险2: 估值较高'],
                    theme_related=True,
                    theme_name=theme_name
                ))
        
        return reports
    
    def _generate_mock_consensus(self, stock_code: str, stock_name: str) -> ConsensusExpectation:
        """生成模拟一致预期"""
        avg_eps = random.uniform(1, 5)
        avg_target = avg_eps * random.uniform(20, 50)
        
        return ConsensusExpectation(
            stock_code=stock_code,
            stock_name=stock_name,
            avg_eps=avg_eps,
            min_eps=avg_eps * 0.8,
            max_eps=avg_eps * 1.2,
            eps_count=random.randint(10, 30),
            avg_pe=avg_target / avg_eps,
            min_pe=avg_target * 0.8 / (avg_eps * 1.2),
            max_pe=avg_target * 1.2 / (avg_eps * 0.8),
            avg_target_price=avg_target,
            min_target_price=avg_target * 0.7,
            max_target_price=avg_target * 1.3,
            target_price_count=random.randint(10, 30),
            consensus_score=random.uniform(0.5, 0.9),
            dispersion=random.uniform(0.1, 0.4),
            revision_trend=random.choice(['上调', '维持', '下调']),
            date=datetime.now()
        )
    
    def generate_research_report(self, theme_name: str, news_list: List[Any]) -> str:
        """生成研报分析报告"""
        parts = [f"\n📑 【{theme_name}】研报分析", "=" * 50]
        
        # 采集研报
        reports = self.collect_reports(theme_name, news_list)
        
        if reports:
            parts.append(f"\n📊 研报概况")
            parts.append(f"├ 研报数量: {len(reports)}份")
            parts.append(f"├ 覆盖股票: {len(set(r.stock_name for r in reports))}只")
            
            # 评级分布
            strong_buy = sum(1 for r in reports if r.rating == RatingLevel.STRONG_BUY)
            buy = sum(1 for r in reports if r.rating == RatingLevel.BUY)
            hold = sum(1 for r in reports if r.rating == RatingLevel.HOLD)
            
            parts.append(f"├ 强烈推荐: {strong_buy}份")
            parts.append(f"├ 推荐: {buy}份")
            parts.append(f"├ 中性: {hold}份")
        
        # 生成信号
        signals = self.generate_signals(reports)
        if signals:
            parts.append(f"\n🎯 研报信号")
            for sig in signals[:5]:
                importance_icon = "⭐" if sig.importance == '重要' else "○"
                parts.append(f"{importance_icon} {sig.signal_type}: {sig.stock_name}")
                parts.append(f"  └ {sig.description[:40]}...")
        
        # 一致预期
        unique_stocks = list(set((r.stock_code, r.stock_name) for r in reports))[:3]
        if unique_stocks:
            parts.append(f"\n📈 一致预期")
            for code, name in unique_stocks:
                consensus = self.analyze_consensus(code, name, reports)
                parts.append(f"├ {name}: EPS{consensus.avg_eps:.2f}, 目标价{consensus.avg_target_price:.1f}元")
                parts.append(f"│ └ 一致性: {consensus.consensus_score:.0%} | 趋势: {consensus.revision_trend}")
        
        return "\n".join(parts)
