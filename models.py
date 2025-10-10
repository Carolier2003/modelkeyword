"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import List, Optional
import json


@dataclass
class ModelInfo:
    """AI模型信息数据类"""
    url: str = ""
    project_name: str = ""
    readme: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "url": self.url,
            "project_name": self.project_name,
            "readme": self.readme,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建实例"""
        return cls(
            url=data.get("url", ""),
            project_name=data.get("project_name", ""),
            readme=data.get("readme", ""),
            tags=data.get("tags", [])
        )


@dataclass
class KeywordResult:
    """关键词提取结果数据类"""
    model_url: str
    keywords: List[dict] = field(default_factory=list)  # [{"keyword": "", "dimension": "", "reason": ""}]
    
    def to_dict(self):
        """转换为字典"""
        return {
            "model_url": self.model_url,
            "keywords": self.keywords
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建实例"""
        return cls(
            model_url=data.get("model_url", ""),
            keywords=data.get("keywords", [])
        )


def save_to_json(data, filename: str):
    """保存数据到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_from_json(filename: str):
    """从JSON文件加载数据"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
