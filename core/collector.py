# -*- coding: utf-8 -*-
"""
数据采集引擎
负责从多个数据源采集财经新闻和资讯
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

import requests
from bs4 import BeautifulSoup
import feedparser

logger = logging.getLogger(__name__)


@dataclass
class News:
    """新闻数据模型"""
    id: str
    title: str
    content: str
    source: str
    url: str
    publish_time: datetime
    collected_time: datetime = field(default_factory=datetime.now)
    category: str = ""  # fast_news, finance_news, policy_news, tech_news
    tags: List[str] = field(default_factory=list)
    sentiment: float = 0.0  # -1 to 1
    related_themes: List[str] = field(default_factory=list)
    is_hot: bool = False
    
    def __post_init__(self):
        """生成唯一ID"""
        if not self.id:
            content = f"{self.title}{self.publish_time}".encode('utf-8')
            self.id = hashlib.md5(content).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        d = asdict(self)
        d['publish_time'] = self.publish_time.isoformat()
        d['collected_time'] = self.collected_time.isoformat()
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'News':
        """从字典创建"""
        d['publish_time'] = datetime.fromisoformat(d['publish_time'])
        d['collected_time'] = datetime.fromisoformat(d['collected_time'])
        return cls(**d)


class NewsCollector:
    """
    新闻采集器
    
    从多个数据源采集财经新闻，支持：
    - 财联社电报（实时快讯）
    - 同花顺资讯
    - 东方财富研报
    - 新浪财经
    - 证券时报
    - 政府官网政策
    
    Features:
    - 多源并行采集
    - 请求限流
    - 失败重试
    - 缓存去重
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化采集器
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.sources = self._parse_sources()
        self.session = requests.Session()
        self.session.headers.update(self.config.get('request', {}).get('headers', {}))
        
        # 缓存目录
        self.cache_dir = Path(__file__).parent.parent / "data" / "news"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 已采集的新闻ID集合
        self.seen_ids: set = set()
        self._load_seen_ids()
    
    def _parse_sources(self) -> Dict[str, List[Dict]]:
        """解析数据源配置"""
        sources = {}
        for category, source_list in self.config.get('sources', {}).items():
            sources[category] = [
                s for s in source_list 
                if s.get('enabled', True)
            ]
        return sources
    
    def _load_seen_ids(self):
        """加载已采集的新闻ID"""
        cache_file = self.cache_dir / "seen_ids.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.seen_ids = set(data.get('ids', []))
            except Exception as e:
                self.logger.warning(f"加载缓存失败: {e}")
    
    def _save_seen_ids(self):
        """保存已采集的新闻ID"""
        cache_file = self.cache_dir / "seen_ids.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'ids': list(self.seen_ids)}, f, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"保存缓存失败: {e}")
    
    def collect(self, categories: List[str] = None) -> List[News]:
        """
        采集所有启用的数据源
        
        Args:
            categories: 要采集的类别列表，None表示全部
            
        Returns:
            采集到的新闻列表
        """
        all_news = []
        target_categories = categories or list(self.sources.keys())
        
        for category in target_categories:
            if category not in self.sources:
                continue
            
            for source in self.sources[category]:
                try:
                    news_list = self._collect_from_source(source, category)
                    all_news.extend(news_list)
                    self.logger.info(f"从 {source['name']} 采集到 {len(news_list)} 条新闻")
                except Exception as e:
                    self.logger.error(f"从 {source['name']} 采集失败: {e}")
        
        # 去重
        all_news = [n for n in all_news if n.id not in self.seen_ids]
        
        # 更新已见ID
        for news in all_news:
            self.seen_ids.add(news.id)
        
        self._save_seen_ids()
        
        # 保存到缓存
        self._cache_news(all_news)
        
        return all_news
    
    def _collect_from_source(self, source: Dict, category: str) -> List[News]:
        """从单个数据源采集"""
        source_type = source.get('type', 'web')
        
        if source_type == 'rss':
            return self._collect_rss(source, category)
        elif source_type == 'web':
            return self._collect_web(source, category)
        elif source_type == 'api':
            return self._collect_api(source, category)
        else:
            self.logger.warning(f"未知数据源类型: {source_type}")
            return []
    
    def _collect_rss(self, source: Dict, category: str) -> List[News]:
        """采集RSS源"""
        news_list = []
        try:
            feed = feedparser.parse(source['url'])
            
            for entry in feed.entries[:20]:  # 限制数量
                news = News(
                    id="",
                    title=entry.get('title', ''),
                    content=entry.get('summary', entry.get('description', '')),
                    source=source['name'],
                    url=entry.get('link', ''),
                    publish_time=self._parse_time(entry.get('published', '')),
                    category=category
                )
                
                # 过滤无效新闻
                if news.title and len(news.title) > 5:
                    news_list.append(news)
                    
        except Exception as e:
            self.logger.error(f"RSS采集失败 {source['name']}: {e}")
        
        return news_list
    
    def _collect_web(self, source: Dict, category: str) -> List[News]:
        """采集网页"""
        news_list = []
        try:
            timeout = self.config.get('request', {}).get('timeout', 30)
            response = self.session.get(source['url'], timeout=timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 使用配置的CSS选择器
            selector = source.get('css_selector', '.news-item, .article')
            items = soup.select(selector)
            
            for item in items[:20]:
                title_elem = item.select_one('a, .title, h3, h2')
                if title_elem:
                    news = News(
                        id="",
                        title=title_elem.get_text(strip=True),
                        content=item.get_text(strip=True),
                        source=source['name'],
                        url=title_elem.get('href', source['url']),
                        publish_time=datetime.now(),
                        category=category
                    )
                    
                    if news.title and len(news.title) > 5:
                        # 处理相对URL
                        if news.url and not news.url.startswith('http'):
                            from urllib.parse import urljoin
                            news.url = urljoin(source['url'], news.url)
                        news_list.append(news)
                        
        except Exception as e:
            self.logger.error(f"网页采集失败 {source['name']}: {e}")
        
        return news_list
    
    def _collect_api(self, source: Dict, category: str) -> List[News]:
        """采集API源"""
        # API采集逻辑，具体实现根据API而定
        # 这里预留接口，具体实现可扩展
        self.logger.info(f"API采集 {source['name']} - 预留接口")
        return []
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str.replace('GMT', '+0000'), fmt)
            except ValueError:
                continue
        
        return datetime.now()
    
    def _cache_news(self, news_list: List[News]):
        """缓存新闻到本地"""
        if not news_list:
            return
        
        date_str = datetime.now().strftime('%Y%m%d')
        cache_file = self.cache_dir / f"news_{date_str}.json"
        
        # 读取现有缓存
        existing_news = []
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    existing_news = [News.from_dict(n) for n in json.load(f)]
            except Exception as e:
                self.logger.warning(f"读取缓存失败: {e}")
        
        # 合并并去重
        all_news = {n.id: n for n in existing_news}
        for news in news_list:
            all_news[news.id] = news
        
        # 保存
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [n.to_dict() for n in all_news.values()],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")
    
    def get_cached_news(self, date: datetime = None) -> List[News]:
        """
        获取缓存的新闻
        
        Args:
            date: 日期，None表示今天
            
        Returns:
            新闻列表
        """
        date = date or datetime.now()
        date_str = date.strftime('%Y%m%d')
        cache_file = self.cache_dir / f"news_{date_str}.json"
        
        if not cache_file.exists():
            return []
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return [News.from_dict(n) for n in json.load(f)]
        except Exception as e:
            self.logger.error(f"读取缓存失败: {e}")
            return []
    
    def filter_by_keywords(self, news: List[News], keywords: Dict[str, List[str]]) -> List[News]:
        """
        根据关键词过滤新闻
        
        Args:
            news: 新闻列表
            keywords: 关键词字典 {题材名: [关键词列表]}
            
        Returns:
            过滤后的新闻
        """
        filtered = []
        
        for n in news:
            n.related_themes = []
            text = f"{n.title} {n.content}".lower()
            
            for theme, kw_list in keywords.items():
                for kw in kw_list:
                    if kw.lower() in text:
                        n.related_themes.append(theme)
                        break
            
            if n.related_themes:
                filtered.append(n)
        
        return filtered


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建采集器
    collector = NewsCollector()
    
    # 采集新闻
    news = collector.collect()
    print(f"采集到 {len(news)} 条新闻")
    
    for n in news[:5]:
        print(f"- [{n.source}] {n.title}")
