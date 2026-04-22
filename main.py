# -*- coding: utf-8 -*-
"""
ThemeHunter 主程序
A股题材挖掘和预期管理系统
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.collector import NewsCollector
from core.analyzer import ThemeAnalyzer
from core.predictor import ThemePredictor
from core.evolution import ThemeEvolutionChain
from core.freshness import ThemeFreshnessManager
from agents.policy_agent import PolicyAgent
from agents.news_agent import NewsAgent
from agents.stock_agent import StockAgent
from agents.cycle_agent import CycleAgent

logger = logging.getLogger(__name__)


class ThemeHunter:
    """ThemeHunter 主类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化各模块
        self.collector = NewsCollector()
        self.analyzer = ThemeAnalyzer()
        self.predictor = ThemePredictor()
        self.evolution = ThemeEvolutionChain()
        self.freshness = ThemeFreshnessManager()
        
        # Agent
        self.policy_agent = PolicyAgent()
        self.news_agent = NewsAgent()
        self.stock_agent = StockAgent()
        self.cycle_agent = CycleAgent()
        
        self.logger.info("ThemeHunter 初始化完成")
    
    def run_morning_report(self) -> str:
        """生成早报"""
        self.logger.info("生成早报...")
        
        # 1. 采集新闻
        news = self.collector.collect()
        self.logger.info(f"采集到 {len(news)} 条新闻")
        
        # 2. 发现新题材
        new_themes = self.freshness.discover_new_themes(news)
        if new_themes:
            self.logger.info(f"发现新题材: {', '.join(new_themes)}")
        
        # 3. 过滤新题材
        themes = self.analyzer.extract_themes(news)
        theme_names = [t.name for t in themes]
        filtered_names = self.freshness.filter_new_themes(theme_names)
        filtered_themes = [t for t in themes if t.name in filtered_names]
        
        # 4. 分析
        cycle_analyses = []
        stock_reports = []
        opportunities = []
        
        for theme in filtered_themes:
            # 更新新鲜度
            self.freshness.update_theme(theme.name, theme.news_count, theme.stage.value)
            
            # 周期分析
            cycle = self.cycle_agent.analyze(theme.name, news, theme.first_appearance)
            cycle_analyses.append(cycle)
            
            # 标的挖掘
            leaders = self.stock_agent.find_core_stocks(theme.name, news)
            following = self.stock_agent.find_following_stocks(theme.name, leaders)
            stock_reports.append(self.stock_agent.generate_report(theme.name, leaders, following))
            
            # 机会预测
            opp = self.predictor.predict_opportunity(theme)
            opportunities.append(opp)
        
        # 5. 生成报告
        return self._format_morning_report(filtered_themes, cycle_analyses, stock_reports, opportunities)
    
    def run_scan(self) -> str:
        """快速扫描"""
        self.logger.info("执行快速扫描...")
        
        news = self.collector.collect()
        themes = self.analyzer.extract_themes(news)
        filtered = [t for t in themes if t.name in self.freshness.filter_new_themes([t.name for t in themes])]
        
        return self._format_scan_report(filtered)
    
    def query_theme(self, theme_name: str) -> str:
        """查询特定题材"""
        self.logger.info(f"查询题材: {theme_name}")
        
        news = self.collector.get_cached_news()
        
        # 分析该题材
        themes = self.analyzer.extract_themes(news)
        theme = next((t for t in themes if t.name == theme_name), None)
        
        if not theme:
            return f"未找到题材: {theme_name}"
        
        # 获取新鲜度
        record = self.freshness.get_theme_status(theme_name)
        
        # 周期分析
        cycle = self.cycle_agent.analyze(theme_name, news, theme.first_appearance)
        
        # 标的
        leaders = self.stock_agent.find_core_stocks(theme_name, news)
        following = self.stock_agent.find_following_stocks(theme_name, leaders)
        
        # 机会
        opp = self.predictor.predict_opportunity(theme)
        
        return self._format_theme_report(theme, cycle, leaders, following, opp, record)
    
    def _format_morning_report(self, themes, cycles, stocks, opportunities) -> str:
        """格式化早报"""
        date = datetime.now().strftime('%Y-%m-%d')
        
        parts = [
            f"🎯 ThemeHunter 早报 | {date}",
            "=" * 50,
            "\n🆕 新题材发现",
        ]
        
        # 按得分排序
        sorted_opps = sorted(zip(opportunities, themes, cycles, stocks), 
                           key=lambda x: x[0].score, reverse=True)
        
        for opp, theme, cycle, stock_report in sorted_opps:
            if opp.score < 60:
                continue
            
            stars = "⭐" * min(int(opp.score / 20), 5)
            
            parts.append(f"\n📌 【{theme.name}】得分 {opp.score:.0f} {stars}🆕")
            parts.append(f"├ 阶段: {cycle.stage.emoji}{cycle.stage.value}")
            parts.append(f"├ 活跃: {cycle.days_in_stage}天")
            parts.append(f"├ 热度: {cycle.news_velocity:.0f}")
            
            if opp.catalyst:
                parts.append(f"├ 催化剂: {opp.catalyst[:40]}")
            
            if opp.recommended_stocks:
                parts.append(f"├ 龙头: {', '.join(opp.recommended_stocks[:3])}")
            
            parts.append(f"└ 建议: {opp.action}")
        
        # 旧题材过滤提示
        old = self.freshness.get_old_themes()
        if old:
            parts.append(f"\n📦 已过滤旧题材: {', '.join([t.name for t in old[:5]])}")
        
        parts.append("\n" + "=" * 50)
        parts.append("⚠️ 本报告仅供参考，不构成投资建议")
        
        return "\n".join(parts)
    
    def _format_scan_report(self, themes) -> str:
        """格式化扫描报告"""
        parts = ["🔍 ThemeHunter 快速扫描", "=" * 40]
        
        for theme in themes[:10]:
            parts.append(f"\n📌 {theme.name}: {theme.heat_score:.0f}分")
            parts.append(f"   {theme.stage.value} | {theme.news_count}条新闻")
        
        return "\n".join(parts)
    
    def _format_theme_report(self, theme, cycle, leaders, following, opp, record) -> str:
        """格式化题材详情"""
        parts = [
            f"📊 【{theme.name}】专题分析",
            "=" * 50,
            f"\n📍 阶段: {cycle.stage.emoji}{cycle.stage.value}",
            f"├ 活跃天数: {cycle.days_in_stage}天",
            f"├ 新闻热度: {cycle.news_velocity:.0f}",
            f"├ 情绪指数: {cycle.sentiment:.0f}",
            f"├ 综合评分: {opp.score:.0f}/100",
        ]
        
        if cycle.warnings:
            parts.append(f"├ 预警: {', '.join(cycle.warnings)}")
        
        if opp.catalyst:
            parts.append(f"\n🔑 催化剂: {opp.catalyst}")
        
        if leaders:
            parts.append(f"\n🐉 龙头标的:")
            for s in leaders[:3]:
                parts.append(f"  • {s.name}({s.code}) - {s.reason}")
        
        if following:
            parts.append(f"\n📈 跟风标的:")
            for s in following[:3]:
                parts.append(f"  • {s.name}({s.code})")
        
        parts.append(f"\n💡 建议: {opp.notes}")
        parts.append("\n" + "=" * 50)
        
        return "\n".join(parts)


def main():
    """主入口"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    hunter = ThemeHunter()
    
    # 生成早报
    report = hunter.run_morning_report()
    print(report)


if __name__ == "__main__":
    main()
