"""
主要工作流程 - 模型关键词提取系统
"""
import os
import argparse
import json
from datetime import datetime
from typing import List, Optional
import traceback

from models import ModelInfo, KeywordResult, save_to_json, load_from_json
from csv_reader import CSVModelReader
from ai_extractor import KeywordExtractor
from multi_platform_extractor import MultiPlatformExtractorSync


def detect_available_platforms() -> int:
    """检测可用的API平台数量"""
    platforms = {
        "SILICONFLOW_API_KEY": "硅基流动",
        "MOONSHOT_API_KEY": "月之暗面",
        "DASHSCOPE_API_KEY": "阿里百炼", 
        "QINIU_API_KEY": "七牛云",
        "HUNYUAN_API_KEY": "腾讯混元",
        "ZHIPU_API_KEY": "智谱AI",
        "VOLCENGINE_API_KEY": "火山引擎",
        "QIANFAN_API_KEY": "百度千帆",
        "SPARK_API_KEY": "讯飞星火",
        "OPENAI_API_KEY": "OpenAI"
    }
    
    available_count = 0
    for key, name in platforms.items():
        if os.getenv(key):
            available_count += 1
    
    return available_count


class ModelKeywordExtractor:
    """模型关键词提取主程序"""
    
    def __init__(self, output_dir: str = "output", token: Optional[str] = None, use_multi_platform: bool = False):
        """
        初始化提取器
        
        Args:
            output_dir: 输出目录
            token: 可选的认证token
            use_multi_platform: 是否使用多平台并发提取
        """
        self.output_dir = output_dir
        self.token = token
        self.use_multi_platform = use_multi_platform
        self.ensure_output_dir()
        
        # 初始化组件
        self.csv_reader = CSVModelReader(delay=0.1, token=token)  # CSV读取器，集成爬虫功能
        
        # 选择提取器
        if use_multi_platform:
            print("🚀 使用多平台并发提取器")
            self.extractor = MultiPlatformExtractorSync()
        else:
            print("📡 使用单平台提取器")
            self.extractor = KeywordExtractor()
    
    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def run_full_pipeline(self, max_models: int = 100, force_crawl: bool = False, use_csv: bool = True):
        """
        运行完整的提取流程
        
        Args:
            max_models: 最大模型数量
            force_crawl: 是否强制重新爬取
            use_csv: 是否优先使用CSV文件
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 为本次运行创建专属文件夹
        run_output_dir = os.path.join(self.output_dir, f"run_{timestamp}")
        os.makedirs(run_output_dir, exist_ok=True)
        print(f"📁 本次输出目录: {run_output_dir}")
        
        print("=" * 60)
        print("模型关键词提取系统")
        print("=" * 60)
        
        try:
            # 步骤1: 获取模型信息
            models_file = os.path.join(run_output_dir, f"models_{timestamp}.json")
            models = self.crawl_or_load_models(max_models, force_crawl, models_file, use_csv)
            
            if not models:
                print("错误：未能获取任何模型信息")
                return
            
            # 步骤2: 提取关键词
            keywords_file = os.path.join(run_output_dir, f"keywords_{timestamp}.json")
            keyword_results = self.extract_keywords(models, keywords_file)
            
            if not keyword_results:
                print("错误：未能提取任何关键词")
                return
            
            # 步骤3: 去重处理
            dedup_file = os.path.join(run_output_dir, f"keywords_dedup_{timestamp}.json")
            final_results = self.deduplicate_keywords(keyword_results, dedup_file)
            
            # 步骤4: 生成报告
            report_file = os.path.join(run_output_dir, f"report_{timestamp}.md")
            self.generate_report(keyword_results, final_results, report_file, total_attempted=len(models))
            
            print(f"\n✅ 提取完成！")
            print(f"📊 统计信息:")
            print(f"   📝 CSV读取模型数: {len(models)}")
            print(f"   ✅ 成功提取模型数: {len(final_results)}")
            print(f"   ❌ 失败模型数: {len(models) - len(final_results)}")
            print(f"   🔍 关键词总数: {sum(len(r.keywords) for r in final_results)}")
            print(f"   📈 成功率: {len(final_results)/len(models)*100:.1f}%")
            print(f"📁 输出文件:")
            print(f"   - 模型信息: {models_file}")
            print(f"   - 原始关键词: {keywords_file}")
            print(f"   - 去重关键词: {dedup_file}")
            print(f"   - 分析报告: {report_file}")
            print(f"   - CSV导出: {report_file.replace('.md', '.csv')}")
            print(f"   - 关键词列表: {report_file.replace('.md', '_keywords.txt')}")
            
        except Exception as e:
            print(f"❌ 运行过程中出现错误: {e}")
            traceback.print_exc()
    
    def crawl_or_load_models(self, max_models: int, force_crawl: bool, output_file: str, use_csv: bool = True) -> List[ModelInfo]:
        """
        获取或加载模型信息
        
        Args:
            max_models: 最大模型数量
            force_crawl: 是否强制重新获取
            output_file: 输出文件路径
            use_csv: 是否使用CSV文件（保留参数兼容性，但只支持CSV）
            
        Returns:
            模型信息列表
        """
        print(f"\n📖 步骤1: 从CSV文件获取模型信息 (目标数量: {max_models})")
        
        # 检查是否存在缓存文件
        cache_file = os.path.join(self.output_dir, "models_cache.json")
        
        if not force_crawl and os.path.exists(cache_file):
            print("发现缓存文件，正在加载...")
            try:
                cached_data = load_from_json(cache_file)
                if cached_data:
                    cached_count = len(cached_data)
                    print(f"📁 缓存文件中有 {cached_count} 个模型")
                    
                    # 如果缓存数量足够，直接使用缓存
                    if cached_count >= max_models:
                        models = [ModelInfo.from_dict(data) for data in cached_data[:max_models]]
                        print(f"✅ 从缓存加载了 {len(models)} 个模型信息（完全使用缓存）")
                        
                        # 保存到输出文件
                        model_dicts = [model.to_dict() for model in models]
                        save_to_json(model_dicts, output_file)
                        
                        return models
                    else:
                        print(f"⚠️  缓存中只有 {cached_count} 个模型，需要 {max_models} 个，将使用缓存并补充爬取")
                        # 继续执行，让 crawl_models 使用缓存
            except Exception as e:
                print(f"⚠️  加载缓存失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 从CSV文件获取模型信息（传递缓存文件路径，优先使用缓存）
        print("开始从CSV文件读取模型信息...")
        try:
            models = self.csv_reader.crawl_models(max_models, fetch_details=True, cache_file=cache_file)
        except Exception as e:
            print(f"❌ CSV读取失败: {e}")
            return []
        
        if models:
            # 保存到缓存和输出文件
            model_dicts = [model.to_dict() for model in models]
            save_to_json(model_dicts, cache_file)
            save_to_json(model_dicts, output_file)
            print(f"✅ 成功读取 {len(models)} 个模型信息")
        else:
            print("❌ 未能读取到任何模型信息")
        
        return models
    
    def extract_keywords(self, models: List[ModelInfo], output_file: str) -> List[KeywordResult]:
        """
        提取关键词
        
        Args:
            models: 模型信息列表
            output_file: 输出文件路径
            
        Returns:
            关键词提取结果列表
        """
        print(f"\n🤖 步骤2: 提取关键词 (模型数量: {len(models)})")
        
        # 检查模型有效性（项目名称不为空即可）
        valid_models = [m for m in models if m.project_name.strip()]
        print(f"有效模型数量: {len(valid_models)}")
        
        # 失败原因统计
        failure_stats = {
            'json_parse_error': 0,
            'insufficient_keywords': 0,
            'validation_error': 0,
            'api_error': 0,
            'other_error': 0
        }
        
        # 说明README获取方式
        print(f"说明: README内容已通过爬虫获取，AI将基于爬取的数据进行分析")
        
        if not valid_models:
            print("❌ 没有有效的模型用于关键词提取")
            return []
        
        # 批量提取关键词
        keyword_results = self.extractor.extract_batch_keywords(valid_models)
        
        if keyword_results:
            # 保存结果
            results_data = [result.to_dict() for result in keyword_results]
            save_to_json(results_data, output_file)
            print(f"✅ 成功提取 {len(keyword_results)} 个模型的关键词")
            
            # 显示失败统计（如果有失败的话）
            failed_count = len(valid_models) - len(keyword_results)
            if failed_count > 0:
                print(f"\n📊 失败分析:")
                print(f"   💔 失败模型数: {failed_count}")
                print(f"   📋 建议检查上述错误信息了解具体失败原因")
        else:
            print("❌ 关键词提取失败")
        
        return keyword_results
    
    def deduplicate_keywords(self, keyword_results: List[KeywordResult], output_file: str) -> List[KeywordResult]:
        """
        关键词去重
        
        Args:
            keyword_results: 原始关键词结果
            output_file: 输出文件路径
            
        Returns:
            去重后的结果
        """
        print(f"\n🔄 步骤3: 保存关键词（去重将在报告生成时进行）")
        
        # 执行去重
        dedup_results = self.extractor.deduplicate_keywords(keyword_results)
        
        if dedup_results:
            # 保存去重结果
            results_data = [result.to_dict() for result in dedup_results]
            save_to_json(results_data, output_file)
            
            # 统计信息
            original_count = sum(len(r.keywords) for r in keyword_results)
            final_count = sum(len(r.keywords) for r in dedup_results)
            print(f"✅ 去重完成: {original_count} → {final_count} 个关键词")
        else:
            print("❌ 去重失败")
        
        return dedup_results
    
    def _csv_deduplicate_keywords(self, keyword_results: List[KeywordResult]) -> List[KeywordResult]:
        """
        执行CSV级别的去重，与generate_csv_output中的逻辑一致
        
        Args:
            keyword_results: 关键词结果列表
            
        Returns:
            去重后的结果列表
        """
        # 用于去重的已使用关键词集合（保留先生成的）
        used_keywords = set()
        dedup_results = []
        
        for result in keyword_results:
            filtered_keywords = []
            
            for kw in result.keywords:
                keyword = kw['keyword']
                
                # 去重：保留先生成的关键词
                if keyword not in used_keywords:
                    used_keywords.add(keyword)
                    filtered_keywords.append(kw)
            
            if filtered_keywords:
                # 创建新的结果对象，包含去重后的关键词
                dedup_result = KeywordResult(
                    model_url=result.model_url,
                    keywords=filtered_keywords
                )
                dedup_results.append(dedup_result)
        
        return dedup_results
    
    def generate_report(self, original_results: List[KeywordResult], final_results: List[KeywordResult], output_file: str, total_attempted: int = None):
        """
        生成分析报告
        
        Args:
            original_results: 原始关键词结果（未去重）
            final_results: 最终关键词结果（与original_results相同，因为去重在CSV阶段进行）
            output_file: 报告文件路径
        """
        print(f"\n📋 步骤4: 生成分析报告")
        
        # 先进行CSV去重，获取真实的去重后数据
        csv_dedup_results = self._csv_deduplicate_keywords(final_results)
        
        # 统计分析
        total_models = len(final_results)
        total_keywords = sum(len(r.keywords) for r in csv_dedup_results)  # 使用CSV去重后的数据
        original_keywords = sum(len(r.keywords) for r in original_results)
        
        # 按维度统计（使用CSV去重后的结果）
        dimension_stats = {}
        final_keywords = []
        
        for result in csv_dedup_results:
            for kw in result.keywords:
                dimension = kw['dimension']
                dimension_stats[dimension] = dimension_stats.get(dimension, 0) + 1
                final_keywords.append(kw['keyword'])
        
        # 原始数据统计（用于高频关键词分析）
        original_keyword_freq = {}
        for result in original_results:
            for kw in result.keywords:
                keyword = kw['keyword']
                original_keyword_freq[keyword] = original_keyword_freq.get(keyword, 0) + 1
        
        # 使用传入的尝试总数，如果没有则使用成功数量
        attempted_models = total_attempted if total_attempted else total_models
        
        # 生成Markdown报告
        report_content = f"""# 模型关键词提取分析报告

## 概览统计

- 📊 **CSV读取模型数**: {attempted_models}
- ✅ **成功提取模型数**: {total_models}
- ❌ **失败模型数**: {attempted_models - total_models}
- 📈 **成功率**: {total_models/attempted_models*100:.1f}%
- 🔍 **原始关键词总数**: {original_keywords}
- ✂️ **去重后关键词总数**: {total_keywords}
- 📉 **去重率**: {(1-total_keywords/original_keywords)*100:.1f}%
- 📊 **平均每模型关键词数**: {total_keywords/total_models:.1f}
- 🕐 **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 维度分布

| 维度 | 关键词数量 | 占比 |
|------|------------|------|
"""
        
        for dimension, count in sorted(dimension_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_keywords * 100
            report_content += f"| {dimension} | {count} | {percentage:.1f}% |\n"
        
        report_content += f"""
## 原始数据高频关键词分析

> 基于去重前的原始提取数据，展示整个数据集中最常见的关键词

| 排名 | 关键词 | 原始出现次数 | 最终保留次数 |
|------|--------|-------------|-------------|
"""
        
        # 统计最终结果中的关键词频率
        final_keyword_freq = {}
        for kw in final_keywords:
            final_keyword_freq[kw] = final_keyword_freq.get(kw, 0) + 1
        
        top_original_keywords = sorted(original_keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        for i, (keyword, original_freq) in enumerate(top_original_keywords, 1):
            final_freq = final_keyword_freq.get(keyword, 0)
            report_content += f"| {i} | {keyword} | {original_freq} | {final_freq} |\n"
        
        # 添加所有关键词列表部分
        report_content += """
## 所有关键词列表

"""
        
        # 按维度分组显示所有关键词（最终结果）
        keywords_by_dimension = {}
        for result in final_results:
            for kw in result.keywords:
                dimension = kw['dimension']
                if dimension not in keywords_by_dimension:
                    keywords_by_dimension[dimension] = []
                keywords_by_dimension[dimension].append(kw['keyword'])
        
        # 为每个维度添加关键词列表
        for dimension in sorted(keywords_by_dimension.keys()):
            keywords = sorted(set(keywords_by_dimension[dimension]))  # 去重并排序
            report_content += f"\n### {dimension} ({len(keywords)}个)\n\n"
            
            # 将关键词分成多行显示，每行最多5个
            for i in range(0, len(keywords), 5):
                line_keywords = keywords[i:i+5]
                report_content += "- " + " • ".join(f"**{kw}**" for kw in line_keywords) + "\n"
        
        report_content += """
## 详细结果

"""
        
        # 添加每个模型的详细结果（使用CSV去重后的结果）
        for result in csv_dedup_results:
            model_name = result.model_url.split('/')[-2:] if '/' in result.model_url else [result.model_url]
            model_name = '/'.join(model_name)
            
            # 将URL中的gitcode.com替换为ai.gitcode.com
            ai_url = result.model_url.replace('gitcode.com', 'ai.gitcode.com')
            
            report_content += f"\n### {model_name}\n\n"
            report_content += f"**URL**: {ai_url}\n\n"
            report_content += "**关键词列表**:\n\n"
            
            for kw in result.keywords:
                report_content += f"- **{kw['keyword']}** ({kw['dimension']}): {kw['reason']}\n"
        
        # 保存报告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ 报告生成完成: {output_file}")
        
        # 生成CSV文件
        csv_file = output_file.replace('.md', '.csv')
        self.generate_csv_output(final_results, csv_file)
        print(f"✅ CSV文件生成完成: {csv_file}")
        
        # 生成纯文本关键词列表
        txt_file = output_file.replace('.md', '_keywords.txt')
        self.generate_keywords_txt(final_results, txt_file)
        print(f"✅ 关键词列表文件生成完成: {txt_file}")
    
    def generate_csv_output(self, keyword_results: List[KeywordResult], csv_file: str):
        """
        生成CSV格式的关键词输出文件
        
        Args:
            keyword_results: 关键词结果列表
            csv_file: CSV文件路径
        """
        import csv
        
        print(f"\n📊 生成CSV输出文件...")
        
        # 用于去重的已使用关键词集合（保留先生成的，不区分大小写）
        used_keywords_lower = set()  # 存储小写版本用于比较
        csv_data = []
        
        for result in keyword_results:
            # 提取项目名称（从URL中获取）
            project_name = result.model_url.split('/')[-1] if '/' in result.model_url else result.model_url
            if result.model_url.count('/') >= 2:
                # 如果URL包含用户名/项目名格式，提取最后两部分
                parts = result.model_url.rstrip('/').split('/')
                if len(parts) >= 2:
                    project_name = '/'.join(parts[-2:])
            
            # 处理每个关键词（按生成顺序，去重保留先生成的）
            for kw in result.keywords:
                keyword = kw['keyword']
                keyword_lower = keyword.lower()  # 转换为小写用于比较
                
                # 去重：不区分大小写，保留先生成的关键词
                if keyword_lower not in used_keywords_lower:
                    used_keywords_lower.add(keyword_lower)
                    # 将URL中的gitcode.com替换为ai.gitcode.com
                    ai_url = result.model_url.replace('gitcode.com', 'ai.gitcode.com')
                    csv_data.append({
                        '项目链接': ai_url,
                        '项目名称': project_name,
                        '高亮词': keyword
                    })
        
        # 写入CSV文件
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if csv_data:
                fieldnames = ['项目链接', '项目名称', '高亮词']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 写入表头
                writer.writeheader()
                
                # 写入数据
                for row in csv_data:
                    writer.writerow(row)
        
        print(f"📊 CSV统计:")
        print(f"   📝 总项目数: {len(keyword_results)}")
        print(f"   🔍 去重前关键词数: {sum(len(r.keywords) for r in keyword_results)}")
        print(f"   ✂️ 去重后关键词数: {len(csv_data)}")
        print(f"   📉 去重率: {(1 - len(csv_data) / sum(len(r.keywords) for r in keyword_results)) * 100:.1f}%")
    
    def generate_keywords_txt(self, keyword_results: List[KeywordResult], txt_file: str):
        """
        生成纯文本格式的关键词列表文件（无markdown格式）
        
        Args:
            keyword_results: 关键词结果列表
            txt_file: 文本文件路径
        """
        print(f"\n📄 生成纯文本关键词列表...")
        
        # 按维度分组显示所有关键词
        keywords_by_dimension = {}
        for result in keyword_results:
            for kw in result.keywords:
                dimension = kw['dimension']
                if dimension not in keywords_by_dimension:
                    keywords_by_dimension[dimension] = []
                keywords_by_dimension[dimension].append(kw['keyword'])
        
        # 生成纯文本内容
        txt_content = "所有关键词列表\n"
        txt_content += "=" * 50 + "\n\n"
        
        # 为每个维度添加关键词列表
        for dimension in sorted(keywords_by_dimension.keys()):
            keywords = sorted(set(keywords_by_dimension[dimension]))  # 去重并排序
            txt_content += f"{dimension} ({len(keywords)}个)\n"
            txt_content += "-" * 30 + "\n"
            
            # 将关键词分成多行显示，每行最多8个
            for i in range(0, len(keywords), 8):
                line_keywords = keywords[i:i+8]
                txt_content += " • ".join(line_keywords) + "\n"
            
            txt_content += "\n"
        
        # 添加统计信息
        total_unique_keywords = len(set(kw for keywords in keywords_by_dimension.values() for kw in keywords))
        total_keywords = sum(len(r.keywords) for r in keyword_results)
        
        txt_content += "统计信息\n"
        txt_content += "=" * 50 + "\n"
        txt_content += f"总模型数: {len(keyword_results)}\n"
        txt_content += f"关键词总数: {total_keywords}\n"
        txt_content += f"去重后关键词数: {total_unique_keywords}\n"
        txt_content += f"平均每模型关键词数: {total_keywords/len(keyword_results):.1f}\n"
        
        # 保存文件
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        
        print(f"📄 纯文本统计:")
        print(f"   📝 维度数: {len(keywords_by_dimension)}")
        print(f"   🔤 去重后关键词数: {total_unique_keywords}")
        print(f"   📊 总关键词数: {total_keywords}")
    
    def test_single_model(self, model_url: str):
        """
        测试单个模型的关键词提取（已弃用）
        
        Args:
            model_url: 模型URL
        """
        print(f"🧪 测试单个模型: {model_url}")
        print("❌ 单个模型测试功能已移除")
        print("💡 请使用CSV文件批量处理: python keyword_extractor.py --max-models 10")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI模型关键词提取系统")
    parser.add_argument("--max-models", type=int, default=10, help="最大模型数量 (默认: 10)")
    parser.add_argument("--force-crawl", action="store_true", help="强制重新获取模型信息")
    parser.add_argument("--test-url", type=str, help="测试单个模型URL")
    parser.add_argument("--output-dir", type=str, default="output", help="输出目录 (默认: output)")
    parser.add_argument("--token", type=str, help="可选的认证token")
    
    args = parser.parse_args()
    
    # 自动检测可用的API平台数量
    available_platforms = detect_available_platforms()
    # 只要有可用平台就使用多平台提取器（支持单个平台的多并发）
    use_multi_platform = available_platforms > 0
    
    print(f"🔍 检测到 {available_platforms} 个可用的API平台")
    if use_multi_platform:
        if available_platforms == 1:
            print("🚀 使用单平台多并发模式（每个平台 5 个并发 worker）")
        else:
            print("🚀 自动启用多平台并发模式")
    else:
        print("❌ 未检测到可用的API平台，请配置至少一个API Key")
    
    # 创建提取器
    extractor = ModelKeywordExtractor(
        output_dir=args.output_dir, 
        token=args.token,
        use_multi_platform=use_multi_platform
    )
    
    if args.test_url:
        # 测试单个模型
        extractor.test_single_model(args.test_url)
    else:
        # 运行完整流程
        extractor.run_full_pipeline(
            max_models=args.max_models,
            force_crawl=args.force_crawl,
            use_csv=True  # 始终使用CSV文件
        )


if __name__ == "__main__":
    main()
