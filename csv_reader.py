#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV模型读取器
用于从CSV文件读取模型信息并转换为ModelInfo对象
"""

import csv
import time
from typing import List, Dict, Optional
from models import ModelInfo
from hf_scraper import scrape_hf_model_sync

# ===== 全局配置 =====
# 只需要在这里修改CSV文件路径，其他地方会自动使用
DEFAULT_CSV_FILE = "UGR模型.csv"
# ===================


class CSVModelReader:
    """CSV模型读取器"""
    
    def __init__(self, csv_file: str = None, delay: float = 0.5, token: str = None):
        """
        初始化CSV读取器
        
        Args:
            csv_file: CSV文件路径（None时使用全局配置）
            delay: 爬取延迟时间（秒）
            token: 可选的认证token
        """
        self.csv_file = csv_file or DEFAULT_CSV_FILE
        self.delay = delay
        self.token = token
    
    def read_csv_data(self, max_models: int = None) -> List[Dict]:
        """
        从CSV文件读取模型数据
        
        Args:
            max_models: 最大模型数量（None表示全部）
            
        Returns:
            模型数据列表
        """
        print(f"📖 开始读取CSV文件: {self.csv_file}")
        
        models = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # 检查审核状态和是否公开
                    audit_status = row.get('审核状态', '')
                    is_public = row.get('是否公开', '')
                    
                    # 只处理审核通过且公开的模型
                    if audit_status == '2' and is_public == '1':
                        models.append(row)
                        
                        # 限制数量
                        if max_models and len(models) >= max_models:
                            break
            
            print(f"✅ 从CSV读取到 {len(models)} 个符合条件的模型")
            return models
            
        except Exception as e:
            print(f"❌ 读取CSV文件失败: {e}")
            return []
    
    def convert_csv_to_model_info(self, csv_model: Dict) -> ModelInfo:
        """
        将CSV数据转换为ModelInfo对象
        
        Args:
            csv_model: CSV行数据
            
        Returns:
            ModelInfo对象
        """
        # 提取基本信息
        project_id = csv_model.get('项目ID', '')
        project_name = csv_model.get('项目名称', '')
        project_url = csv_model.get('项目网址', '')
        
        # 创建ModelInfo对象（不包含README和标签，这些需要爬取）
        model_info = ModelInfo(
            url=project_url,
            project_name=project_name,
            readme="",  # 空字符串，需要爬取
            tags=[]     # 空列表，需要爬取
        )
        
        return model_info
    
    def get_model_detail_from_scraper(self, model_info: ModelInfo) -> ModelInfo:
        """
        使用爬虫获取模型的详细信息
        
        Args:
            model_info: 基础模型信息
            
        Returns:
            包含详细信息的ModelInfo对象
        """
        print(f"正在使用爬虫获取模型详细信息: {model_info.project_name}")
        
        try:
            # 使用爬虫获取详细信息
            scraped_data = scrape_hf_model_sync(model_info.url, self.token)
            
            # 更新模型信息
            model_info.readme = scraped_data.get('readme', '')
            model_info.tags = scraped_data.get('tags', [])
            
            print(f"✅ 成功获取模型信息: README长度={len(model_info.readme)}, 标签数={len(model_info.tags)}")
            return model_info
            
        except Exception as e:
            print(f"❌ 爬取模型信息失败: {e}")
            # 返回原始模型信息
            return model_info
