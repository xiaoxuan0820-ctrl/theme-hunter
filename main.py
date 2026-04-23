# -*- coding: utf-8 -*-
"""
ThemeHunter 主程序（升级版）
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
from core.analyzer import ThemeAnalyzer, ThemeStage, CredibilityAssessment, RiskAssessment
from core.predictor import ThemePredictor
from core.evolution import ThemeEvolutionChain
from core.freshness import ThemeFreshnessManager

# Agent导入（升级版）
from agents.policy_agent import PolicyAgent
from agents.news_agent import NewsAgent
from agents.tech_agent import TechAgent
from agents.event_agent import EventAgent
from agents.stock_agent import StockAgent, StockLevel
from agents.cycle_agent import CycleAgent, ThemeStage as CycleStage
from agents.fund_agent import FundAgent
from agents.research_agent import ResearchAgent

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
        
        # Agent（升级版）
        self.policy_agent = PolicyAgent()
        self.news_agent = NewsAgent()
        self.tech_agent = TechAgent()
        self.event_agent = EventAgent()
        self.stock_agent = StockAgent()
        self.cycle_agent = CycleAgent()
        self.fund_agent = FundAgent()
        self.research_agent = ResearchAgent()
        
        self.logger.info("ThemeHunter 升级版初始化完成")
    
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
        analyses = []
        
        for theme in filtered_themes:
            # 更新新鲜度
            self.freshness.update_theme(theme.name, theme.news_count, theme.stage.value)
            
            # 综合分析
            analysis = self._comprehensive_analysis(theme.name, news)
            analyses.append(analysis)
        
        # 5. 生成报告
        return self._format_deep_report(filtered_themes, analyses)
    
    def _comprehensive_analysis(self, theme_name: str, news: list) -> dict:
        """综合分析"""
        analysis = {}
        
        # 1. 政策解读
        policy_insights = self.policy_agent.analyze(news)
        analysis['policy'] = policy_insights[:3] if policy_insights else []
        
        # 2. 新闻分析
        news_insights = self.news_agent.analyze(news, self.analyzer.theme_keywords)
        analysis['news'] = news_insights[:5] if news_insights else []
        
        # 3. 技术前瞻
        tech_insights = self.tech_agent.analyze(theme_name, news)
        analysis['tech'] = tech_insights[:2] if tech_insights else []
        
        # 4. 事件分析
        event_insights = self.event_agent.analyze(news)
        analysis['events'] = event_insights[:3] if event_insights else []
        
        # 5. 资金追踪
        fund_signals = self.fund_agent.generate_signals(theme_name, news)
        analysis['fund'] = fund_signals[:5] if fund_signals else []
        
        # 6. 研报分析
        reports = self.research_agent.collect_reports(theme_name, news)
        analysis['research'] = reports[:5] if reports else []
        
        # 7. 标的分析
        leaders = self.stock_agent.find_core_stocks(theme_name, news)
        following = self.stock_agent.find_following_stocks(theme_name, leaders)
        marginal = self.stock_agent.find_marginal_stocks(theme_name, news)
        analysis['stocks'] = {
            'leaders': leaders[:5],
            'following': following[:5],
            'marginal': marginal[:3]
        }
        
        # 8. 周期分析
        stage, metrics, warning = self.cycle_agent.analyze(theme_name, news)
        history = self.cycle_agent.compare_with_history(theme_name, news)
        analysis['cycle'] = {
            'stage': stage,
            'metrics': metrics,
            'warning': warning,
            'history': history
        }
        
        return analysis
    
    def _format_deep_report(self, themes: list, analyses: list) -> str:
        """生成深度分析报告"""
        date = datetime.now().strftime('%Y-%m-%d')
        
        parts = [
            f"🎯 ThemeHunter 深度分析报告",
            f"{'━' * 50}",
            f"\n📅 生成时间: {date}",
            f"📊 监测题材: {len(themes)}个"
        ]
        
        # 按综合得分排序
        sorted_themes = sorted(
            zip(themes, analyses),
            key=lambda x: self._calculate_composite_score(x[0], x[1]),
            reverse=True
        )
        
        for theme, analysis in sorted_themes[:10]:
            # 跳过低分题材
            composite = self._calculate_composite_score(theme, analysis)
            if composite < 50:
                continue
            
            stars = "⭐" * min(int(composite / 20), 5)
            
            parts.append(f"\n{'━' * 50}")
            parts.append(f"\n📌 【{theme.name}】综合得分 {composite:.0f}/100 {stars}")
            parts.append(f"\n{'━' * 10} 基础信息 {'━' * 10}")
            parts.append(f"├ 题材类型: {theme.theme_type or '综合类'}")
            parts.append(f"├ 首次发现: {theme.first_appearance.strftime('%Y-%m-%d') if theme.first_appearance else '未知'}")
            parts.append(f"├ 当前阶段: {theme.stage.emoji}{theme.stage.description}")
            parts.append(f"├ 下阶段预测: {self._predict_next_stage(analysis)}")
            
            # 可信度评估
            if theme.credibility:
                parts.append(f"\n{'━' * 10} 可信度评估 {'━' * 10}")
                parts.append(f"├ 政策级别: {theme.credibility.policy_level or '未明确'}")
                parts.append(f"├ 媒体权威性: {theme.credibility.get_stars()} ({theme.credibility.media_authority_score:.0f}/100)")
                parts.append(f"├ 信息一致性: {theme.credibility.validation_count}源验证")
                parts.append(f"├ 可信度得分: {theme.credibility.total_score:.0f}/100")
            
            # 催化剂分析
            if theme.catalysts:
                parts.append(f"\n{'━' * 10} 催化剂分析 {'━' * 10}")
                for i, cat in enumerate(theme.catalysts[:3]):
                    cat_level = {'短期': '⚡', '中期': '📅', '长期': '🎯'}.get(cat.catalyst_level, '•')
                    parts.append(f"├ {cat_level} {cat.title[:30]}")
                    parts.append(f"│  └ 预计: {cat.expected_date.strftime('%m月%d日')} | 置信度: {cat.confidence:.0%}")
            
            # 风险评估
            if theme.risk:
                parts.append(f"\n{'━' * 10} 风险评估 {'━' * 10}")
                parts.append(f"├ 炒作天数: {theme.risk.trading_days}天")
                parts.append(f"├ 龙头涨幅: {theme.risk.leader_return:.0f}%")
                parts.append(f"├ 资金动向: {'分化' if theme.risk.capital_divergence > 0.5 else '正常'}")
                parts.append(f"├ 风险等级: {theme.risk.get_stars()}")
                if theme.risk.warnings:
                    parts.append(f"├ 预警信息:")
                    for w in theme.risk.warnings[:3]:
                        parts.append(f"│ └ {w}")
            
            # 标的分析
            stocks = analysis.get('stocks', {})
            leaders = stocks.get('leaders', [])
            following = stocks.get('following', [])
            
            if leaders:
                parts.append(f"\n{'━' * 10} 标的分析 {'━' * 10}")
                parts.append(f"\n【龙头股】（核心标的）")
                for s in leaders[:3]:
                    parts.append(f"┌──────────────────────────────────────┐")
                    parts.append(f"│ {s.name}({s.code})")
                    parts.append(f"│ ├ 题材关联度: {s.relevance_reason[:20]}")
                    if s.north_bound_holding > 0:
                        parts.append(f"│ ├ 北向持股: {s.north_bound_holding*100:.1f}%")
                    if s.research_coverage > 0:
                        parts.append(f"│ ├ 研报覆盖: {s.research_coverage}家券商")
                    parts.append(f"│ └ 建议: {s.action} | 仓位{s.position_ratio*100:.0f}%")
                    parts.append(f"└──────────────────────────────────────┘")
                
                if following:
                    parts.append(f"\n【跟风股】（弹性标的）")
                    for s in following[:3]:
                        parts.append(f"├ {s.name}({s.code}) - {s.relevance_reason[:15]}")
            
            # 周期分析
            cycle = analysis.get('cycle', {})
            if cycle:
                stage = cycle.get('stage')
                metrics = cycle.get('metrics')
                if stage and metrics:
                    parts.append(f"\n{'━' * 10} 周期研判 {'━' * 10}")
                    parts.append(f"├ 阶段: {stage.emoji}{stage.label} ({stage.action})")
                    parts.append(f"├ 持续天数: {metrics.days_in_stage}天")
                    parts.append(f"├ 预计剩余: {metrics.predicted_remaining_days}天")
                    parts.append(f"├ 新闻速度: {metrics.velocity:.0f}")
                    parts.append(f"├ 情绪指数: {metrics.sentiment:.0f}")
                    parts.append(f"└ 风险等级: {metrics.risk_level.upper()}")
            
            # 操作建议
            parts.append(f"\n{'━' * 10} 操作建议 {'━' * 10}")
            if leaders:
                best = leaders[0]
                parts.append(f"├ 操作级别: {self._get_operation_level(composite)}")
                parts.append(f"├ 核心标的: {best.name}")
                parts.append(f"├ 建仓策略: 龙头优先，分批建仓")
                parts.append(f"├ 止损位: {best.stop_loss*100:.0f}%（题材证伪或龙头破位）")
                parts.append(f"├ 止盈位: {best.take_profit*100:.0f}%")
                parts.append(f"├ 持仓周期: {self._estimate_holding_period(metrics)}")
                parts.append(f"└ 预期收益: {best.take_profit*100:.0f}-{best.take_profit*200:.0f}%")
        
        # 历史对比
        if analyses and analyses[0].get('cycle', {}).get('history'):
            history = analyses[0]['cycle']['history']
            parts.append(f"\n{'━' * 50}")
            parts.append(f"\n📈 历史对比参考")
            parts.append(f"├ 同类题材: {history.similar_theme}")
            parts.append(f"├ 相似度: {history.similarity:.0%}")
            parts.append(f"├ 历史走势: 龙头涨幅{history.peak_leader_return:.0%}，持续{history.duration}天")
            parts.append(f"└ 参考价值: {history.reference_value}")
        
        # 风险提示
        parts.append(f"\n{'━' * 50}")
        parts.append(f"\n⚠️ 风险提示")
        parts.append("• 本报告仅供参考，不构成投资建议")
        parts.append("• 题材炒作风险极高，请严格止损")
        parts.append("• 注意催化剂不及预期风险")
        parts.append("• 关注龙头股走势，破位及时止损")
        
        return "\n".join(parts)
    
    def _calculate_composite_score(self, theme, analysis: dict) -> float:
        """计算综合得分"""
        score = theme.heat_score * 0.3
        
        # 可信度加成
        if theme.credibility:
            score += theme.credibility.total_score * 0.2
        
        # 风险调整
        if theme.risk:
            risk_penalty = theme.risk.risk_score * 0.1
            score -= risk_penalty
        
        # 催化剂加成
        if theme.catalysts:
            catalyst_bonus = sum(c.confidence * 10 for c in theme.catalysts[:3])
            score += min(catalyst_bonus, 15)
        
        # 资金信号加成
        fund_signals = analysis.get('fund', [])
        if fund_signals:
            score += sum(s.intensity * 5 for s in fund_signals[:3])
        
        # 研报支持加成
        reports = analysis.get('research', [])
        if reports:
            strong_buy = sum(1 for r in reports if r.rating_score >= 0.85)
            score += strong_buy * 2
        
        return min(score, 100)
    
    def _predict_next_stage(self, analysis: dict) -> str:
        """预测下一阶段"""
        cycle = analysis.get('cycle', {})
        metrics = cycle.get('metrics')
        
        if not metrics:
            return "未知"
        
        stage = cycle.get('stage')
        if not stage:
            return "未知"
        
        # 基于当前阶段和动量预测
        stage_order = {
            CycleStage.GERMINATION: 1,
            CycleStage.ERUPTION: 2,
            CycleStage.SPECULATION: 3,
            CycleStage.COOLDOWN: 4,
            CycleStage.DEAD: 5
        }
        
        current = stage_order.get(stage, 1)
        
        if metrics.momentum > 80 and current < 3:
            next_stage = CycleStage.ERUPTION
            prob = 75
        elif metrics.momentum > 50 and current < 4:
            next_stage = CycleStage.SPECULATION
            prob = 65
        elif metrics.risk_level == 'high':
            next_stage = CycleStage.COOLDOWN
            prob = 70
        else:
            next_stage = CycleStage.COOLDOWN if current < 4 else CycleStage.DEAD
            prob = 50
        
        return f"{next_stage.label}（概率{prob}%，预计{(metrics.days_in_stage + metrics.predicted_remaining_days) // 7}周内）"
    
    def _get_operation_level(self, score: float) -> str:
        """获取操作级别"""
        if score >= 80:
            return "A类（强烈推荐）"
        elif score >= 65:
            return "B类（推荐）"
        elif score >= 50:
            return "C类（谨慎参与）"
        else:
            return "D类（不推荐）"
    
    def _estimate_holding_period(self, metrics) -> str:
        """估算持仓周期"""
        if not metrics:
            return "5-15天"
        
        remaining = metrics.predicted_remaining_days
        if remaining <= 7:
            return "3-7天"
        elif remaining <= 14:
            return "5-15天"
        else:
            return "10-30天"
    
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
        
        # 综合分析
        analysis = self._comprehensive_analysis(theme_name, news)
        
        # 生成报告
        return self._format_theme_report(theme, analysis)
    
    def _format_theme_report(self, theme, analysis: dict) -> str:
        """格式化题材详情报告"""
        parts = [
            f"📊 【{theme.name}】深度分析报告",
            f"{'━' * 50}",
        ]
        
        # 基础信息
        parts.append(f"\n📍 基础信息")
        parts.append(f"├ 题材类型: {theme.theme_type or '综合类'}")
        parts.append(f"├ 当前阶段: {theme.stage.emoji}{theme.stage.description}")
        parts.append(f"├ 新闻数量: {theme.news_count}条")
        parts.append(f"├ 热度得分: {theme.heat_score:.0f}")
        
        # 可信度
        if theme.credibility:
            parts.append(f"\n📋 可信度评估: {theme.credibility.total_score:.0f}/100 {theme.credibility.get_stars()}")
            parts.append(f"├ 政策级别: {theme.credibility.policy_level}")
            parts.append(f"├ 媒体权威: {theme.credibility.get_stars()}")
            parts.append(f"└ 多源验证: {theme.credibility.validation_count}个来源")
        
        # 风险
        if theme.risk:
            parts.append(f"\n⚠️ 风险评估: {theme.risk.get_stars()}")
            parts.append(f"├ 炒作天数: {theme.risk.trading_days}天")
            parts.append(f"├ 龙头涨幅: {theme.risk.leader_return:.0f}%")
            if theme.risk.warnings:
                for w in theme.risk.warnings:
                    parts.append(f"├ {w}")
        
        # 催化剂
        if theme.catalysts:
            parts.append(f"\n🎯 催化剂")
            for cat in theme.catalysts[:3]:
                parts.append(f"├ {cat.title[:30]}")
                parts.append(f"│  └ {cat.expected_date.strftime('%m月%d日')} | {cat.catalyst_level}")
        
        # 标的
        stocks = analysis.get('stocks', {})
        if stocks.get('leaders'):
            parts.append(f"\n📈 龙头标的")
            for s in stocks['leaders'][:3]:
                parts.append(f"├ {s.name}({s.code}) | {s.action}")
        
        # 周期
        cycle = analysis.get('cycle', {})
        if cycle:
            stage = cycle.get('stage')
            metrics = cycle.get('metrics')
            if stage and metrics:
                parts.append(f"\n📊 周期状态")
                parts.append(f"├ {stage.emoji}{stage.label}")
                parts.append(f"├ 已持续: {metrics.days_in_stage}天")
                parts.append(f"├ 预计剩余: {metrics.predicted_remaining_days}天")
                parts.append(f"└ {stage.action}")
        
        return "\n".join(parts)
    
    def _format_scan_report(self, themes) -> str:
        """格式化扫描报告"""
        parts = ["🔍 ThemeHunter 快速扫描", "=" * 40]
        
        for theme in themes[:10]:
            stars = "⭐" * min(int(theme.heat_score / 20), 5)
            
            parts.append(f"\n📌 {theme.name}: {theme.heat_score:.0f}分 {stars}")
            parts.append(f"   {theme.stage.emoji}{theme.stage.description} | {theme.news_count}条新闻")
            
            if theme.credibility:
                parts.append(f"   可信度: {theme.credibility.get_stars()}")
        
        return "\n".join(parts)
    
    def generate_technical_report(self, theme_name: str) -> str:
        """生成技术分析专题报告"""
        news = self.collector.get_cached_news()
        analysis = self._comprehensive_analysis(theme_name, news)
        
        parts = [f"\n🔬 【{theme_name}】技术专题分析", "=" * 50]
        
        # 技术分析
        tech = analysis.get('tech', [])
        if tech:
            parts.append(f"\n📊 技术成熟度")
            for t in tech:
                parts.append(f"├ TRL等级: {t.trl_level.level}级 ({t.trl_level.name})")
                parts.append(f"├ 当前阶段: {t.industrialization_timeline}")
                parts.append(f"├ 预计产业化: {t.estimated_industrialization_date.strftime('%Y年%m月')}")
                parts.append(f"├ 技术壁垒: {t.barrier_level}")
                parts.append(f"├ 中国能力: {t.china_capability}")
                if t.leading_players:
                    parts.append(f"└ 领先玩家: {', '.join(t.leading_players[:3])}")
        
        # 事件分析
        events = analysis.get('events', [])
        if events:
            parts.append(f"\n📅 重要事件")
            for e in events[:3]:
                parts.append(f"├ {e.level.label}: {e.event_name[:30]}")
                parts.append(f"│  └ {e.gap_direction} | {e.certainty.label}")
        
        return "\n".join(parts)


def main():
    """主函数"""
    hunter = ThemeHunter()
    
    # 生成早报
    report = hunter.run_morning_report()
    print(report)
    
    return report


if __name__ == "__main__":
    main()
