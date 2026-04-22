# -*- coding: utf-8 -*-
"""
ThemeHunter - A股题材挖掘和预期管理系统

专注于新题材发现和分析，帮助投资者提前布局
"""

__version__ = '1.0.0'
__author__ = 'ThemeHunter Team'

from .core.collector import NewsCollector, News
from .core.analyzer import ThemeAnalyzer, Theme, ThemeStage
from .core.predictor import ThemePredictor, Opportunity, Signal
from .core.evolution import ThemeEvolutionChain, ThemeChain
from .core.freshness import ThemeFreshnessManager, ThemeRecord

__all__ = [
    'NewsCollector',
    'News',
    'ThemeAnalyzer',
    'Theme',
    'ThemeStage',
    'ThemePredictor',
    'Opportunity',
    'Signal',
    'ThemeEvolutionChain',
    'ThemeChain',
    'ThemeFreshnessManager',
    'ThemeRecord',
]
