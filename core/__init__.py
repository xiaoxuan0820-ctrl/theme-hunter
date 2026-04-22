# -*- coding: utf-8 -*-
"""
ThemeHunter - A股题材挖掘和预期管理系统
核心模块初始化
"""

from .collector import NewsCollector, News
from .analyzer import ThemeAnalyzer, Theme, ThemeStage, Catalyst
from .predictor import ThemePredictor, Opportunity, Signal
from .tracker import ThemeTracker, TrackingStatus

__all__ = [
    'NewsCollector',
    'News',
    'ThemeAnalyzer',
    'Theme',
    'ThemeStage',
    'Catalyst',
    'ThemePredictor',
    'Opportunity',
    'Signal',
    'ThemeTracker',
    'TrackingStatus',
]

__version__ = '1.0.0'
