#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预爬取脚本 - 批量爬取模型网页数据并保存到缓存

功能：
- 从模型提示词.csv读取所有符合条件的模型
- 使用爬虫获取README和标签信息
- 支持断点续传和分批处理
- 实时保存到缓存文件
"""

import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Set
from tqdm import tqdm

from models import ModelInfo
from csv_reader import CSVModelReader, DEFAULT_CSV_FILE
from hf_scraper import scrape_hf_model_sync


class PreCrawler:
    """预爬取器"""
    
    def __init__(self, csv_file: str = None, cache_file: str = "output/models_cache.json", 
                 delay: float = 0.5, token: str = None):
        """
        初始化预爬取器
        
        Args:
            csv_file: CSV文件路径（None时使用全局配置）
            cache_file: 缓存文件路径
            delay: 爬取延迟时间（秒）
            token: 可选的认证token
        """
        self.csv_file = csv_file or DEFAULT_CSV_FILE
        self.cache_file = cache_file
        self.delay = delay
        self.token = token
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        # 初始化CSV读取器
        self.csv_reader = CSVModelReader(csv_file=csv_file, delay=delay, token=token)
    
    def load_existing_cache(self) -> Dict[str, ModelInfo]:
        """
        加载现有缓存
        
        Returns:
            已缓存的模型字典 {url: ModelInfo}
        """
        if not os.path.exists(self.cache_file):
            print("📁 缓存文件不存在，将创建新缓存")
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            cached_models = {}
            for data in cached_data:
                model_info = ModelInfo.from_dict(data)
                cached_models[model_info.url] = model_info
            
            print(f"📁 加载现有缓存: {len(cached_models)} 个模型")
            return cached_models
            
        except Exception as e:
            print(f"⚠️ 加载缓存失败: {e}")
            return {}
    
    def get_all_models_from_csv(self) -> List[ModelInfo]:
        """
        从CSV文件获取所有符合条件的模型
        
        Returns:
            模型信息列表
        """
        print(f"📖 从CSV文件读取模型: {self.csv_file}")
        
        # 读取CSV数据
        csv_models = self.csv_reader.read_csv_data(max_models=10000)  # 设置一个很大的数字
        
        if not csv_models:
            print("❌ 无法从CSV获取模型数据")
            return []
        
        # 转换为ModelInfo对象（只转换基本信息，不爬取详情）
        model_infos = []
        for csv_model in csv_models:
            try:
                model_info = self.csv_reader.convert_csv_to_model_info(csv_model)
                model_infos.append(model_info)
            except Exception as e:
                print(f"⚠️ 转换模型信息失败: {e}")
                continue
        
        print(f"📊 CSV中符合条件的模型: {len(model_infos)} 个")
        return model_infos
    
    def filter_uncached_models(self, all_models: List[ModelInfo], 
                              cached_models: Dict[str, ModelInfo]) -> List[ModelInfo]:
        """
        过滤出未缓存的模型
        
        Args:
            all_models: 所有模型列表
            cached_models: 已缓存的模型字典
            
        Returns:
            未缓存的模型列表
        """
        uncached_models = []
        cached_urls = set(cached_models.keys())
        
        for model in all_models:
            if model.url not in cached_urls:
                uncached_models.append(model)
        
        print(f"📋 需要爬取的模型: {len(uncached_models)} 个")
        print(f"📁 已缓存的模型: {len(cached_models)} 个")
        
        return uncached_models
    
    def crawl_models_batch(self, models: List[ModelInfo], batch_size: int = 50, 
                          cached_models: Dict[str, ModelInfo] = None) -> List[ModelInfo]:
        """
        分批爬取模型数据，每爬取一个立即保存到缓存
        
        Args:
            models: 要爬取的模型列表
            batch_size: 批次大小
            cached_models: 已缓存的模型字典，用于实时更新
            
        Returns:
            成功爬取的模型列表
        """
        if not models:
            print("✅ 没有需要爬取的模型")
            return []
        
        print(f"🚀 开始分批爬取 {len(models)} 个模型 (批次大小: {batch_size})")
        print("💾 实时保存模式：每爬取一个模型立即保存到缓存")
        
        successful_models = []
        total_batches = (len(models) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(models))
            batch_models = models[start_idx:end_idx]
            
            print(f"\n📦 处理批次 {batch_idx + 1}/{total_batches} ({len(batch_models)} 个模型)")
            
            batch_successful = []
            for i, model in enumerate(tqdm(batch_models, desc=f"批次 {batch_idx + 1}")):
                try:
                    # 使用爬虫获取详细信息
                    detailed_model = self.csv_reader.get_model_detail_from_scraper(model)
                    
                    if detailed_model.readme or detailed_model.tags:
                        batch_successful.append(detailed_model)
                        
                        # 立即保存到缓存
                        if cached_models is not None:
                            cached_models[detailed_model.url] = detailed_model
                            self.save_cache_immediate(cached_models)
                        
                        print(f"✅ {model.project_name}: README={len(detailed_model.readme)}, 标签={len(detailed_model.tags)} [已保存]")
                    else:
                        print(f"⚠️ {model.project_name}: 爬取失败，跳过")
                    
                    # 添加延迟
                    if i < len(batch_models) - 1:
                        time.sleep(self.delay)
                        
                except Exception as e:
                    print(f"❌ {model.project_name}: 爬取异常 - {e}")
                    continue
            
            successful_models.extend(batch_successful)
            print(f"📊 批次 {batch_idx + 1} 完成: {len(batch_successful)}/{len(batch_models)} 成功")
            
            # 批次间稍长延迟
            if batch_idx < total_batches - 1:
                print("⏸️ 批次间休息 2 秒...")
                time.sleep(2)
        
        print(f"\n🎉 爬取完成: {len(successful_models)}/{len(models)} 个模型成功")
        return successful_models
    
    def save_cache_immediate(self, cached_models: Dict[str, ModelInfo]):
        """
        立即保存缓存到文件（实时保存）
        
        Args:
            cached_models: 已缓存的模型字典
        """
        # 转换为字典列表
        model_dicts = [model.to_dict() for model in cached_models.values()]
        
        # 保存到文件
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(model_dicts, f, ensure_ascii=False, indent=2)
            
            # 不打印太多信息，避免刷屏
            # print(f"💾 实时保存: {len(model_dicts)} 个模型")
            
        except Exception as e:
            print(f"❌ 实时保存缓存失败: {e}")
    
    def save_cache(self, cached_models: Dict[str, ModelInfo], new_models: List[ModelInfo]):
        """
        保存缓存到文件（批量保存，兼容旧接口）
        
        Args:
            cached_models: 已缓存的模型字典
            new_models: 新爬取的模型列表
        """
        # 合并新旧模型
        for model in new_models:
            cached_models[model.url] = model
        
        # 转换为字典列表
        model_dicts = [model.to_dict() for model in cached_models.values()]
        
        # 保存到文件
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(model_dicts, f, ensure_ascii=False, indent=2)
            
            print(f"💾 缓存已保存: {len(model_dicts)} 个模型 -> {self.cache_file}")
            
        except Exception as e:
            print(f"❌ 保存缓存失败: {e}")
    
    def run(self, max_models: int = None, batch_size: int = 50, force_crawl: bool = False):
        """
        运行预爬取流程
        
        Args:
            max_models: 最大模型数量（None表示全部）
            batch_size: 批次大小
            force_crawl: 是否强制重新爬取
        """
        start_time = time.time()
        
        print("=" * 60)
        print("🚀 模型数据预爬取系统")
        print("=" * 60)
        print(f"📁 CSV文件: {self.csv_file}")
        print(f"💾 缓存文件: {self.cache_file}")
        print(f"⏱️ 爬取延迟: {self.delay}秒")
        print(f"📦 批次大小: {batch_size}")
        print("=" * 60)
        
        try:
            # 1. 加载现有缓存
            cached_models = {} if force_crawl else self.load_existing_cache()
            
            # 2. 获取所有模型
            all_models = self.get_all_models_from_csv()
            if not all_models:
                print("❌ 无法获取模型数据")
                return
            
            # 3. 限制模型数量
            if max_models and max_models < len(all_models):
                all_models = all_models[:max_models]
                print(f"📊 限制处理数量: {len(all_models)} 个模型")
            
            # 4. 过滤未缓存的模型
            uncached_models = self.filter_uncached_models(all_models, cached_models)
            
            if not uncached_models:
                print("✅ 所有模型都已缓存，无需爬取")
                return
            
            # 5. 分批爬取（实时保存模式）
            new_models = self.crawl_models_batch(uncached_models, batch_size, cached_models)
            
            # 6. 最终保存缓存（确保数据完整性）
            if new_models:
                self.save_cache(cached_models, [])  # 传入空列表，因为已经实时保存了
            
            # 7. 统计信息
            end_time = time.time()
            total_time = end_time - start_time
            
            print("\n" + "=" * 60)
            print("📊 爬取统计")
            print("=" * 60)
            print(f"⏱️ 总耗时: {total_time:.2f}秒")
            print(f"📊 处理模型: {len(all_models)} 个")
            print(f"🆕 新爬取: {len(new_models)} 个")
            print(f"📁 缓存总数: {len(cached_models) + len(new_models)} 个")
            print(f"⚡ 平均速度: {len(new_models)/total_time:.2f} 个/秒")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 预爬取过程中出现错误: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="预爬取模型网页数据")
    parser.add_argument("--csv-file", default=DEFAULT_CSV_FILE, help="CSV文件路径")
    parser.add_argument("--cache-file", default="output/models_cache.json", help="缓存文件路径")
    parser.add_argument("--max-models", type=int, help="最大模型数量")
    parser.add_argument("--batch-size", type=int, default=50, help="批次大小")
    parser.add_argument("--delay", type=float, default=0.5, help="爬取延迟时间（秒）")
    parser.add_argument("--force-crawl", action="store_true", help="强制重新爬取所有模型")
    parser.add_argument("--token", help="可选的认证token")
    
    args = parser.parse_args()
    
    # 创建预爬取器
    crawler = PreCrawler(
        csv_file=args.csv_file,
        cache_file=args.cache_file,
        delay=args.delay,
        token=args.token
    )
    
    # 运行预爬取
    crawler.run(
        max_models=args.max_models,
        batch_size=args.batch_size,
        force_crawl=args.force_crawl
    )


if __name__ == "__main__":
    main()
