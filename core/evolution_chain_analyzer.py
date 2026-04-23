# -*- coding: utf-8 -*-
"""
演化链分析器（Evolution Chain Analyzer）
核心目标：识别题材间的因果关系和启动顺序
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import re

logger = logging.getLogger(__name__)


@dataclass
class EvolutionNode:
    """演化节点"""
    theme_name: str
    stage: str                    # 萌芽/爆发/高潮/退潮
    start_day: int                # 开始天数
    duration: int                 # 持续天数
    intensity: float             # 强度 0-1
    trigger: str = ""            # 触发因素
    is_root: bool = False        # 是否为源头


@dataclass
class EvolutionLink:
    """演化链接"""
    from_theme: str
    to_theme: str
    correlation: float           # 相关性 0-1
    delay_days: int             # 延迟天数
    cause: str                  # 原因
    strength: str               # 强度: strong/medium/weak


@dataclass
class EvolutionChain:
    """演化链"""
    root_theme: str             # 源头题材
    chain: List[EvolutionNode]   # 演化节点
    links: List[EvolutionLink]   # 演化链接
    current_position: str        # 当前所处位置
    remaining_days: int         # 预计剩余天数
    confidence: float           # 置信度
    

class EvolutionChainAnalyzer:
    """演化链分析器"""
    
    # 已知的演化链
    KNOWN_CHAINS = {
        "油价上涨": {
            "trigger": "地缘政治/供给收缩",
            "chain": ["油价", "黄金", "白银", "通胀"],
            "links": [
                {"from": "油价", "to": "黄金", "delay": 1, "cause": "通胀预期+避险"},
                {"from": "油价", "to": "白银", "delay": 2, "cause": "工业属性+金融属性"},
                {"from": "黄金", "to": "白银", "delay": 1, "cause": "金银联动"},
            ]
        },
        "新能源车爆发": {
            "trigger": "销量大增/政策支持",
            "chain": ["新能源车", "锂电", "碳酸锂", "储能"],
            "links": [
                {"from": "新能源车", "to": "锂电", "delay": 7, "cause": "电池需求增加"},
                {"from": "锂电", "to": "碳酸锂", "delay": 14, "cause": "锂矿涨价"},
                {"from": "新能源车", "to": "储能", "delay": 30, "cause": "配储需求"},
            ]
        },
        "AI革命": {
            "trigger": "技术突破/产品发布",
            "chain": ["AI大模型", "算力", "AI应用", "数据要素"],
            "links": [
                {"from": "AI大模型", "to": "算力", "delay": 7, "cause": "算力需求爆发"},
                {"from": "AI大模型", "to": "AI应用", "delay": 14, "cause": "应用落地"},
                {"from": "AI应用", "to": "数据要素", "delay": 21, "cause": "数据需求增加"},
            ]
        },
        "低空政策": {
            "trigger": "政策开放",
            "chain": ["低空政策", "低空经济", "无人机", "eVTOL"],
            "links": [
                {"from": "低空政策", "to": "低空经济", "delay": 7, "cause": "政策落地"},
                {"from": "低空政策", "to": "无人机", "delay": 14, "cause": "产业规划"},
                {"from": "低空经济", "to": "eVTOL", "delay": 30, "cause": "商业化"},
            ]
        },
        "固态电池突破": {
            "trigger": "技术突破/量产公告",
            "chain": ["固态电池", "新能源车", "储能", "新材料"],
            "links": [
                {"from": "固态电池", "to": "新能源车", "delay": 14, "cause": "车企配套"},
                {"from": "固态电池", "to": "储能", "delay": 30, "cause": "储能升级"},
                {"from": "固态电池", "to": "新材料", "delay": 7, "cause": "材料需求"},
            ]
        }
    }
    
    # 题材关键词映射
    THEME_KEYWORDS = {
        "油价": ["油价", "石油", "原油", "WTI", "布伦特"],
        "黄金": ["黄金", "金价", "伦敦金", "COMEX"],
        "白银": ["白银", "银价"],
        "新能源车": ["新能源车", "电动车", "新能源汽车"],
        "锂电": ["锂电池", "动力电池", "锂电"],
        "碳酸锂": ["碳酸锂", "锂盐", "锂矿"],
        "AI大模型": ["AI大模型", "大模型", "ChatGPT", "LLM"],
        "算力": ["算力", "GPU", "AI服务器"],
        "AI应用": ["AI应用", "人工智能应用"],
        "低空政策": ["低空政策", "空域开放"],
        "低空经济": ["低空经济", "低空"],
        "无人机": ["无人机", "UAV"],
        "eVTOL": ["eVTOL", "飞行汽车", "空中出行"],
        "固态电池": ["固态电池", "全固态"],
        "储能": ["储能", "电化学储能"],
    }
    
    # 启动顺序关键词
    TRIGGER_KEYWORDS = [
        "地缘", "冲突", "战争", "制裁", "封锁",
        "突破", "量产", "发布", "政策", "规划",
        "数据", "超预期", "大增", "暴涨"
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_chain(self, theme_name: str, news_list: list) -> EvolutionChain:
        """
        分析题材演化链
        
        Args:
            theme_name: 当前题材名称
            news_list: 新闻列表
        
        Returns:
            EvolutionChain: 演化链分析结果
        """
        # 1. 查找匹配的已知演化链
        matched_chain = self._find_matched_chain(theme_name)
        
        if matched_chain:
            return self._build_known_chain(theme_name, matched_chain, news_list)
        
        # 2. 从新闻中提取演化链
        return self._extract_chain_from_news(theme_name, news_list)
    
    def _find_matched_chain(self, theme_name: str) -> Optional[Dict]:
        """查找匹配的已知演化链"""
        for chain_name, chain_data in self.KNOWN_CHAINS.items():
            chain_themes = chain_data["chain"]
            
            # 检查是否在已知链中
            for t in chain_themes:
                if t in theme_name or theme_name in t:
                    return chain_data
            
            # 检查关键词映射
            for t_name, keywords in self.THEME_KEYWORDS.items():
                if any(kw in theme_name for kw in keywords):
                    if t_name in chain_themes:
                        return chain_data
        
        return None
    
    def _build_known_chain(self, theme_name: str, chain_data: Dict, 
                          news_list: list) -> EvolutionChain:
        """构建已知演化链"""
        chain_themes = chain_data["chain"]
        links_data = chain_data["links"]
        
        # 找到当前位置
        current_idx = -1
        for i, t in enumerate(chain_themes):
            if t in theme_name or theme_name in t:
                current_idx = i
                break
        
        if current_idx < 0:
            current_idx = 0
        
        # 构建节点
        nodes = []
        for i, t in enumerate(chain_themes):
            node = EvolutionNode(
                theme_name=t,
                stage=self._guess_stage(t, news_list),
                start_day=i * 7,  # 假设每7天一个阶段
                duration=14,
                intensity=1.0 - (i * 0.15),
                trigger=chain_data["trigger"] if i == 0 else "",
                is_root=(i == 0)
            )
            nodes.append(node)
        
        # 构建链接
        links = []
        for link_data in links_data:
            link = EvolutionLink(
                from_theme=link_data["from"],
                to_theme=link_data["to"],
                correlation=0.8,
                delay_days=link_data["delay"],
                cause=link_data["cause"],
                strength="strong" if link_data["delay"] <= 7 else "medium"
            )
            links.append(link)
        
        # 剩余天数
        remaining = sum(14 for i in range(current_idx, len(nodes)))
        
        return EvolutionChain(
            root_theme=chain_themes[0],
            chain=nodes,
            links=links,
            current_position=chain_themes[current_idx],
            remaining_days=remaining,
            confidence=0.8
        )
    
    def _extract_chain_from_news(self, theme_name: str, 
                                news_list: list) -> EvolutionChain:
        """从新闻中提取演化链"""
        # 分析新闻中的题材关联
        related_themes = self._find_related_themes(theme_name, news_list)
        
        # 确定源头
        root_theme = self._identify_root(related_themes, news_list)
        
        # 排序
        sorted_themes = self._sort_by_trigger(related_themes, news_list)
        
        # 构建节点
        nodes = []
        for i, (t, trigger, delay) in enumerate(sorted_themes):
            node = EvolutionNode(
                theme_name=t,
                stage=self._guess_stage(t, news_list),
                start_day=delay,
                duration=14,
                intensity=0.8 - (i * 0.1),
                trigger=trigger,
                is_root=(t == root_theme)
            )
            nodes.append(node)
        
        return EvolutionChain(
            root_theme=root_theme,
            chain=nodes,
            links=[],
            current_position=theme_name,
            remaining_days=14 * max(1, len(nodes) - 1),
            confidence=0.5
        )
    
    def _find_related_themes(self, theme_name: str, news_list: list) -> List[Tuple[str, str, int]]:
        """查找相关题材"""
        related = []
        
        # 加载龙头股映射获取题材列表
        try:
            mapping_path = Path(__file__).parent.parent / "config" / "theme_leaders.yaml"
            with open(mapping_path, 'r', encoding='utf-8') as f:
                import yaml
                data = yaml.safe_load(f)
                all_themes = list(data.get('theme_leaders', {}).keys())
        except:
            all_themes = list(self.KNOWN_CHAINS.keys())
        
        # 从新闻中匹配
        text_all = " ".join(f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}" 
                           for n in news_list)
        
        for theme in all_themes:
            keywords = self.THEME_KEYWORDS.get(theme, [theme])
            
            for kw in keywords:
                if kw in text_all and kw != theme_name:
                    # 提取触发因素
                    trigger = self._extract_trigger(text_all, kw)
                    delay = self._estimate_delay(text_all, kw)
                    
                    related.append((theme, trigger, delay))
                    break
        
        return related
    
    def _identify_root(self, related_themes: List[Tuple[str, str, int]], 
                      news_list: list) -> str:
        """识别源头题材"""
        if not related_themes:
            return ""
        
        # 找触发关键词最多的
        text_all = " ".join(f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}" 
                           for n in news_list)
        
        scores = {}
        for theme, _, _ in related_themes:
            score = sum(1 for kw in self.TRIGGER_KEYWORDS if kw in text_all)
            scores[theme] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return related_themes[0][0] if related_themes else ""
    
    def _sort_by_trigger(self, related_themes: List[Tuple[str, str, int]], 
                        news_list: list) -> List[Tuple[str, str, int]]:
        """按触发顺序排序"""
        text_all = " ".join(f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}" 
                           for n in news_list)
        
        # 按触发关键词出现位置排序
        def sort_key(item):
            theme, trigger, delay = item
            keywords = self.THEME_KEYWORDS.get(theme, [theme])
            
            # 找最早出现的位置
            min_pos = len(text_all)
            for kw in keywords:
                pos = text_all.find(kw)
                if pos >= 0:
                    min_pos = min(min_pos, pos)
            
            return min_pos
        
        return sorted(related_themes, key=sort_key)
    
    def _extract_trigger(self, text: str, keyword: str) -> str:
        """提取触发因素"""
        for trigger_kw in self.TRIGGER_KEYWORDS:
            if trigger_kw in text:
                return trigger_kw
        return "未知"
    
    def _estimate_delay(self, text: str, keyword: str) -> int:
        """估算延迟"""
        # 检查时间相关关键词
        if "立即" in text or "当天" in text:
            return 0
        elif "一周" in text or "7天" in text:
            return 7
        elif "两周" in text or "14天" in text:
            return 14
        elif "一个月" in text:
            return 30
        return 7  # 默认7天
    
    def _guess_stage(self, theme_name: str, news_list: list) -> str:
        """猜测题材阶段"""
        text_all = " ".join(f"{getattr(n, 'title', '')} {getattr(n, 'content', '')}" 
                           for n in news_list)
        
        # 检查关键词
        if any(kw in text_all for kw in ["首次", "突破", "首款"]):
            return "萌芽"
        elif any(kw in text_all for kw in ["爆发", "涨停", "暴涨"]):
            return "爆发"
        elif any(kw in text_all for kw in ["连板", "妖股", "疯狂"]):
            return "高潮"
        elif any(kw in text_all for kw in ["回落", "退潮"]):
            return "退潮"
        
        return "爆发"  # 默认
    
    def generate_chain_report(self, chain: EvolutionChain) -> str:
        """生成演化链报告"""
        parts = [f"\n🔗 演化链分析"]
        parts.append(f"{'━' * 40}")
        
        parts.append(f"\n📍 源头题材: {chain.root_theme}")
        
        # 演化路径
        parts.append(f"\n📈 演化路径:")
        path = " → ".join(n.theme_name for n in chain.chain)
        parts.append(f"   {path}")
        
        # 当前阶段
        parts.append(f"\n🎯 当前所处: {chain.current_position}")
        
        # 各阶段信息
        for node in chain.chain:
            emoji = "🌱" if node.stage == "萌芽" else \
                    "🔥" if node.stage == "爆发" else \
                    "⚡" if node.stage == "高潮" else \
                    "💧" if node.stage == "退潮" else "❓"
            
            parts.append(f"\n{emoji} {node.theme_name}")
            parts.append(f"   阶段: {node.stage} | 持续: {node.duration}天")
            if node.trigger:
                parts.append(f"   触发: {node.trigger}")
        
        # 链接信息
        if chain.links:
            parts.append(f"\n⏰ 时序关系:")
            for link in chain.links[:3]:
                delay_str = "立即" if link.delay_days == 0 else f"{link.delay_days}天后"
                parts.append(f"   {link.from_theme} → {link.to_theme} ({delay_str})")
                parts.append(f"      原因: {link.cause}")
        
        # 剩余空间
        parts.append(f"\n⏳ 预计剩余空间: {chain.remaining_days}天")
        parts.append(f"   置信度: {chain.confidence:.0%}")
        
        return "\n".join(parts)
    
    def find_derivative_opportunities(self, theme_name: str, 
                                     current_day: int) -> List[Tuple[str, int]]:
        """
        查找衍生机会
        
        Args:
            theme_name: 当前题材
            current_day: 当前是第几天
        
        Returns:
            List[Tuple[题材名, 距今天数]]: 即将启动的衍生题材
        """
        opportunities = []
        
        for chain_name, chain_data in self.KNOWN_CHAINS.items():
            chain_themes = chain_data["chain"]
            links_data = chain_data["links"]
            
            # 检查是否在链中
            if theme_name not in chain_themes:
                continue
            
            idx = chain_themes.index(theme_name)
            
            # 查找后续题材
            for link in links_data:
                if link["from"] == theme_name:
                    remaining = link["delay"]
                    
                    # 只推荐即将启动的（7天内）
                    if remaining <= 7:
                        opportunities.append((link["to"], remaining))
        
        return sorted(opportunities, key=lambda x: x[1])


# 添加 List 类型提示需要的导入
from typing import Optional
