# -*- coding: utf-8 -*-
"""
标的挖掘机 Agent
权重: 1.2 - 挖掘龙头股和跟风股
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Stock:
    """股票信息"""
    code: str
    name: str
    stock_type: str = "leader"  # leader, following
    theme: str = ""
    reason: str = ""
    tags: List[str] = field(default_factory=list)


class StockAgent:
    """标的挖掘机 - 专注龙头股和跟风股识别"""
    
    # 已知龙头股库
    KNOWN_LEADERS = {
        '低空经济': ['万丰奥威', '中信海直', '纵横股份', '亿航智能'],
        '固态电池': ['宁德时代', '赣锋锂业', '国轩高科', '清陶能源'],
        'AI眼镜': ['博士眼镜', '明月镜片', '康耐特', '横店东磁'],
        '量子计算': ['国盾量子', '科大国创', '光迅科技', '神州信息'],
        '人形机器人': ['绿的谐波', '柯力传感', '奥比中光', '双环传动'],
        'AI': ['科大讯飞', '寒武纪', '海光信息', '景嘉微'],
        '新能源': ['比亚迪', '宁德时代', '隆基绿能', '阳光电源'],
        '半导体': ['中芯国际', '华虹半导体', '北方华创', '拓荆科技'],
        '消费电子': ['立讯精密', '歌尔股份', '蓝思科技', '鹏鼎控股'],
    }
    
    # 跟风股模式
    FOLLOWING_PATTERNS = {
        '低空经济': ['山河智能', '威海广泰', '四川九洲', '安达维尔', '宗申动力'],
        '固态电池': ['当升科技', '容百科技', '恩捷股份', '贝特瑞', '硅宝科技'],
        'AI眼镜': ['天键股份', '亿道信息', '卓翼科技', '龙旗科技'],
        '量子计算': ['国科微', '东方通', '飞天诚信', '浩丰科技'],
        '人形机器人': ['汇川技术', '埃斯顿', '新时达', '秦川机床'],
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.weight = 1.2
        self.name = "标的挖掘机"
    
    def find_core_stocks(self, theme_name: str, news_list: List[Any] = None) -> List[Stock]:
        """挖掘龙头股"""
        leaders = []
        
        # 从已知库查找
        known = self.KNOWN_LEADERS.get(theme_name, [])
        for name in known:
            leaders.append(Stock(
                code=self._guess_code(name),
                name=name,
                stock_type='leader',
                theme=theme_name,
                reason='行业龙头，技术领先，市占率高',
                tags=['龙头', '核心标的']
            ))
        
        # 从新闻提取
        if news_list:
            for news in news_list:
                text = f"{getattr(news, 'title', '')} {getattr(news, 'content', '')}"
                if any(kw in text for kw in ['龙头', '首选', '核心标的', '领涨']):
                    names = self._extract_names(text)
                    for name in names[:2]:
                        if name not in [s.name for s in leaders]:
                            leaders.append(Stock(
                                code=self._guess_code(name),
                                name=name,
                                stock_type='leader',
                                theme=theme_name,
                                reason=f'新闻提及: {getattr(news, "source", "")}',
                                tags=['新闻提及']
                            ))
        
        return leaders[:5]
    
    def find_following_stocks(self, theme_name: str, leaders: List[Stock] = None) -> List[Stock]:
        """挖掘跟风股"""
        following = []
        
        known = self.FOLLOWING_PATTERNS.get(theme_name, [])
        leader_names = [s.name for s in (leaders or [])]
        
        for name in known:
            if name not in leader_names:
                following.append(Stock(
                    code=self._guess_code(name),
                    name=name,
                    stock_type='following',
                    theme=theme_name,
                    reason='跟风标的，弹性较大',
                    tags=['跟风', '高弹性']
                ))
        
        return following[:5]
    
    def _extract_names(self, text: str) -> List[str]:
        """提取股票名称"""
        import re
        pattern = r'【([^】]+)】|\(([^)]+)\)|《([^》]+)》'
        matches = re.findall(pattern, text)
        names = []
        for match in matches:
            for g in match:
                if g and 2 <= len(g) <= 6 and g not in names:
                    names.append(g)
        return names
    
    def _guess_code(self, name: str) -> str:
        """猜测股票代码"""
        codes = {
            '万丰奥威': '002085', '中信海直': '000099', '纵横股份': '688070',
            '宁德时代': '300750', '赣锋锂业': '002460', '比亚迪': '002594',
            '科大讯飞': '002230', '寒武纪': '688256', '立讯精密': '002475',
            '歌尔股份': '002241', '国盾量子': '688027', '科大国创': '300520',
            '亿航智能': '688306', '山河智能': '002097', '宗申动力': '001696',
        }
        return codes.get(name, '------')
    
    def generate_report(self, theme_name: str, leaders: List[Stock], following: List[Stock] = None) -> str:
        """生成标的报告"""
        parts = [f"📌 【{theme_name}】标的清单", "=" * 40]
        
        if leaders:
            parts.append("\n🐉 龙头标的:")
            for s in leaders:
                parts.append(f"├ {s.name}({s.code})")
                parts.append(f"│  └ {s.reason}")
        
        if following:
            parts.append("\n📈 跟风标的:")
            for s in following:
                parts.append(f"├ {s.name}({s.code})")
                parts.append(f"│  └ {s.reason}")
        
        return "\n".join(parts)
