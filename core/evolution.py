# -*- coding: utf-8 -*-
"""
题材演化链追踪系统
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Stage:
    name: str
    keywords: List[str]
    duration_range: str
    next_signal: str
    related_sectors: List[str] = field(default_factory=list)
    typical_stocks: List[str] = field(default_factory=list)
    estimated_days: Tuple[int, int] = (7, 30)
    
    def to_dict(self) -> Dict:
        return self.__dict__


@dataclass
class ThemeChain:
    chain_id: str
    root_event: str
    chain_type: str
    stages: List[Stage]
    current_stage_index: int = 0
    evolution_probability: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)
    
    @property
    def current_stage(self) -> Optional[Stage]:
        if 0 <= self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None
    
    @property
    def next_stage(self) -> Optional[Stage]:
        idx = self.current_stage_index + 1
        if idx < len(self.stages):
            return self.stages[idx]
        return None
    
    def to_dict(self) -> Dict:
        return {
            'chain_id': self.chain_id,
            'root_event': self.root_event,
            'chain_type': self.chain_type,
            'stages': [s.to_dict() for s in self.stages],
            'current_stage_index': self.current_stage_index,
            'evolution_probability': self.evolution_probability,
            'last_update': self.last_update.isoformat(),
        }


@dataclass
class TransitionSignal:
    from_stage: str
    to_stage: str
    signal_keywords: List[str]
    detected_keywords: List[str]
    confidence: float = 0.0
    news_count: int = 0
    detected_at: datetime = field(default_factory=datetime.now)
    
    @property
    def probability(self) -> float:
        if not self.signal_keywords:
            return 0.0
        return min(len(self.detected_keywords) / len(self.signal_keywords) * self.confidence * 1.5, 0.95)


class ThemeEvolutionChain:
    """题材演化链追踪器"""
    
    def __init__(self, patterns_path: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if patterns_path is None:
            patterns_path = Path(__file__).parent.parent / "config" / "evolution_patterns.yaml"
        
        with open(patterns_path, 'r', encoding='utf-8') as f:
            self.patterns = yaml.safe_load(f)
        
        self.chains_dir = Path(__file__).parent.parent / "data" / "themes" / "chains"
        self.chains_dir.mkdir(parents=True, exist_ok=True)
        self.chains: Dict[str, ThemeChain] = {}
        self._load_chains()
    
    def _load_chains(self):
        for chain_file in self.chains_dir.glob("*.json"):
            try:
                with open(chain_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['stages'] = [Stage(**s) for s in data.get('stages', [])]
                    data['last_update'] = datetime.fromisoformat(data.get('last_update', datetime.now().isoformat()))
                    self.chains[data['root_event']] = ThemeChain(**{k: v for k, v in data.items() if k in ThemeChain.__dataclass_fields__})
            except Exception as e:
                self.logger.warning(f"加载演化链失败: {e}")
    
    def identify_chain_position(self, theme_name: str, news_list: List[Any] = None) -> Optional[ThemeChain]:
        """识别题材在演化链中的位置"""
        matched_chain = None
        matched_idx = -1
        
        for chain_type, config in self.patterns.get('evolution_patterns', {}).items():
            stages = config.get('chain', [])
            for idx, stage in enumerate(stages):
                keywords = stage.get('keywords', [])
                for kw in keywords:
                    if kw in theme_name or theme_name in kw:
                        if idx > matched_idx:
                            matched_idx = idx
                            matched_chain = self._build_chain(theme_name, chain_type, stages, idx)
                        break
        
        return matched_chain
    
    def _build_chain(self, theme: str, chain_type: str, stages: List[Dict], idx: int) -> ThemeChain:
        stage_objs = [Stage(
            name=s['stage'],
            keywords=s.get('keywords', []),
            duration_range=s.get('duration', '未知'),
            next_signal=s.get('next_signal', ''),
            related_sectors=s.get('related_sectors', []),
            typical_stocks=s.get('typical_stocks', []),
        ) for s in stages]
        
        if theme not in self.chains:
            chain = ThemeChain(
                chain_id=f"chain_{theme}_{datetime.now().strftime('%Y%m%d')}",
                root_event=theme,
                chain_type=chain_type,
                stages=stage_objs,
                current_stage_index=idx,
            )
            self.chains[theme] = chain
        else:
            chain = self.chains[theme]
            chain.current_stage_index = idx
            chain.last_update = datetime.now()
        
        return chain
    
    def predict_next_stage(self, chain: ThemeChain) -> Optional[Dict]:
        nxt = chain.next_stage
        if not nxt:
            return None
        
        return {
            'next_stage_name': nxt.name,
            'keywords': nxt.keywords,
            'probability': chain.evolution_probability or 0.5,
            'estimated_days': nxt.estimated_days,
            'typical_stocks': nxt.typical_stocks,
            'next_signal': nxt.next_signal,
        }
    
    def generate_report(self, chains: List[ThemeChain] = None) -> str:
        if not chains:
            chains = list(self.chains.values())
        
        if not chains:
            return "🔗 题材演化链追踪\n\n暂无活跃的题材演化链"
        
        parts = ["🔗 题材演化链追踪", "=" * 50]
        
        for chain in chains:
            curr = chain.current_stage
            nxt = chain.next_stage
            if not curr:
                continue
            
            parts.append(f"\n📌 【{chain.root_event}】")
            parts.append(f"├ 当前: {curr.name}")
            if nxt:
                prob = chain.evolution_probability * 100
                parts.append(f"├ 下一: {nxt.name}（概率{prob:.0f}%）")
                if curr.typical_stocks:
                    parts.append(f"├ 当前标的: {', '.join(curr.typical_stocks[:3])}")
                if nxt.typical_stocks:
                    parts.append(f"└ 下一阶段: {', '.join(nxt.typical_stocks[:3])}")
        
        return "\n".join(parts)
