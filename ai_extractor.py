"""
AI关键词提取模块 - 使用Moonshot AI进行关键词提取
"""
import os
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

from models import ModelInfo, KeywordResult
from base_extractor import BaseKeywordExtractor

# 加载环境变量
load_dotenv()


class KeywordExtractor(BaseKeywordExtractor):
    """关键词提取器"""
    
    def __init__(self):
        """初始化AI客户端"""
        super().__init__()  # 调用基类初始化
        self.client = OpenAI(
            api_key=os.getenv("MOONSHOT_API_KEY"), 
            base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
        )
        self.model = "kimi-k2-0905-preview"
        
        # 移除全局关键词去重，改为在报告生成时去重
    
    # build_prompt 方法已移至 BaseKeywordExtractor
    
    def extract_keywords(self, model_info: ModelInfo) -> Optional[KeywordResult]:
        """
        提取单个模型的关键词（带重试机制和性能监控）
        
        Args:
            model_info: 模型信息
            
        Returns:
            关键词提取结果
        """
        import time
        start_time = time.time()
        
        max_retries = 3
        base_delay = 3  # 减少基础延迟
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # 重试时的延迟（指数退避）
                    retry_delay = base_delay * (2 ** (attempt - 1))
                    print(f"🔄 第{attempt}次重试，等待 {retry_delay} 秒...")
                    import time
                    time.sleep(retry_delay)
                
                prompt = self.build_prompt(model_info)
                
                if attempt == 0:
                    print(f"正在为模型 {model_info.project_name} 提取关键词...")
                else:
                    print(f"重试中：正在为模型 {model_info.project_name} 提取关键词...")
                
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一位专业的AI项目运营专家和SEO大师，专门负责从AI模型项目中提取高价值的关键词。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # 降低温度保持一致性
                    max_tokens=500  # 进一步减少token数量，提高响应速度
                )
                
                response_content = completion.choices[0].message.content
                
                # 解析JSON响应
                keywords = self._parse_keywords_response(response_content)
                
                if keywords:
                    elapsed_time = time.time() - start_time
                    if attempt > 0:
                        print(f"✅ 重试成功！提取 {len(keywords)} 个关键词 (耗时: {elapsed_time:.1f}秒)")
                    else:
                        print(f"✅ 成功提取 {len(keywords)} 个关键词 (耗时: {elapsed_time:.1f}秒)")
                    return KeywordResult(
                        model_url=model_info.url,
                        keywords=keywords
                    )
                else:
                    print(f"❌ 未能提取到有效关键词 - 模型: {model_info.project_name}")
                    print(f"🔍 可能原因: JSON解析失败、关键词数量不足或格式验证失败")
                    if attempt == max_retries:  # 最后一次尝试才显示详细信息
                        print(f"📝 AI原始返回内容:")
                        print("=" * 80)
                        print(response_content[:1000] + ("..." if len(response_content) > 1000 else ""))
                        print("=" * 80)
                    return None
                    
            except Exception as e:
                error_message = str(e)
                
                # 检查是否是API限流错误
                if "429" in error_message or "rate_limit" in error_message.lower():
                    if attempt < max_retries:
                        retry_delay = 30 + (attempt * 10)  # 限流时等待更长时间
                        print(f"⚠️ API限流错误 - 模型: {model_info.project_name}")
                        print(f"🕐 等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"❌ API限流错误，重试次数已用完 - 模型: {model_info.project_name}")
                        print(f"🔍 错误详情: {e}")
                        return None
                
                # 检查是否是网络错误
                elif "timeout" in error_message.lower() or "connection" in error_message.lower():
                    if attempt < max_retries:
                        retry_delay = base_delay * 2  # 网络错误时等待较短时间
                        print(f"⚠️ 网络错误 - 模型: {model_info.project_name}")
                        print(f"🕐 等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"❌ 网络错误，重试次数已用完 - 模型: {model_info.project_name}")
                        print(f"🔍 错误详情: {e}")
                        return None
                
                # 其他错误直接失败
                else:
                    print(f"❌ 提取关键词时出错 - 模型: {model_info.project_name}")
                    print(f"🔍 错误详情: {e}")
                    print(f"🌐 模型URL: {model_info.url}")
                    return None
        
        # 如果所有重试都失败了
        print(f"❌ 所有重试尝试均失败 - 模型: {model_info.project_name}")
        return None
    
    # _parse_keywords_response 方法已移至 BaseKeywordExtractor
    
    # _validate_keyword 和 _clean_keyword 方法已移至 BaseKeywordExtractor
    
    def extract_batch_keywords(self, model_infos: List[ModelInfo]) -> List[KeywordResult]:
        """
        批量提取关键词（性能优化版）
        
        Args:
            model_infos: 模型信息列表
            
        Returns:
            关键词提取结果列表
        """
        results = []
        total = len(model_infos)
        
        print(f"开始批量提取 {total} 个模型的关键词...")
        print(f"⚡ 性能优化：减少延迟，提高处理速度")
        
        for i, model_info in enumerate(model_infos, 1):
            print(f"\n进度: {i}/{total}")
            
            # 跳过无效的模型信息
            # 说明AI将基于爬取的数据进行分析
            print(f"📡 模型 {model_info.project_name} - AI将基于爬取的README和标签信息进行分析")
            
            result = self.extract_keywords(model_info)
            if result:
                results.append(result)
                # ✨ 实时更新排除队列
                self.update_exclusion_queue(result.keywords)
            
            # 智能延迟：根据处理速度动态调整
            import time
            if i < total:  # 最后一个不需要延迟
                # 如果处理速度快，减少延迟；如果慢，保持适当延迟
                delay = 1 if i % 5 == 0 else 0.5  # 每5个模型稍微长一点延迟
                time.sleep(delay)
        
        print(f"\n批量提取完成，成功处理 {len(results)} 个模型")
        return results
    
    # deduplicate_keywords, _is_similar_keyword_exists, _fix_common_json_errors, _enhance_brand_keywords 方法已移至 BaseKeywordExtractor


def test_extractor():
    """测试关键词提取功能"""
    extractor = KeywordExtractor()
    
    # 创建测试模型信息
    test_model = ModelInfo(
        url="https://ai.gitcode.com/ifly_opensource/Spark-Chemistry-X1-13B",
        project_name="ifly_opensource/Spark-Chemistry-X1-13B",
        readme="Spark Chemistry X1 13B 是一个专门用于化学推理的大语言模型。该模型基于先进的Transformer架构，经过化学相关数据的深度训练，能够进行复杂的化学分析、反应预测和分子设计。模型支持多种化学任务，包括化学反应预测、分子性质分析、化学方程式平衡等。",
        tags=["文本生成", "Transformers", "Safetensors", "英文", "汉语", "Apache License 2.0", "chemistry", "scientific llm", "CoT", "reasoning"]
    )
    
    # 测试关键词提取
    result = extractor.extract_keywords(test_model)
    
    if result:
        print(f"\n模型: {result.model_url}")
        print("提取的关键词:")
        for kw in result.keywords:
            print(f"- {kw['keyword']} ({kw['dimension']}): {kw['reason']}")
    else:
        print("关键词提取失败")


if __name__ == "__main__":
    test_extractor()
