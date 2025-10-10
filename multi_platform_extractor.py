"""
多平台AI关键词提取模块 - 支持并发调用多个大模型平台
"""
import os
import re
import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv

from models import ModelInfo, KeywordResult
from base_extractor import BaseKeywordExtractor

# 加载环境变量
load_dotenv()


class MultiPlatformExtractor(BaseKeywordExtractor):
    """多平台关键词提取器"""
    
    def __init__(self):
        """初始化多个AI客户端"""
        self.platforms = self._init_platforms()
        
    def _init_platforms(self) -> Dict[str, Dict]:
        """初始化支持的平台配置"""
        platforms = {}
        
        # 月之暗面 (Moonshot)
        if os.getenv("MOONSHOT_API_KEY"):
            platforms["moonshot"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("MOONSHOT_API_KEY"),
                    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
                ),
                "model": "kimi-k2-0905-preview",
                "name": "月之暗面",
                "enabled": True
            }
        
        # 阿里百炼 (DashScope)
        if os.getenv("DASHSCOPE_API_KEY"):
            platforms["dashscope"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("DASHSCOPE_API_KEY"),
                    base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                ),
                "model": os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
                "name": "阿里百炼",
                "enabled": True
            }
        
        # OpenAI (如果配置了)
        if os.getenv("OPENAI_API_KEY"):
            platforms["openai"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                ),
                "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                "name": "OpenAI",
                "enabled": True
            }
        
        # 智谱AI (如果配置了)
        if os.getenv("ZHIPU_API_KEY"):
            platforms["zhipu"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("ZHIPU_API_KEY"),
                    base_url=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
                ),
                "model": os.getenv("ZHIPU_MODEL", "glm-4"),
                "name": "智谱AI",
                "enabled": True
            }
        
        # 七牛云 (如果配置了)
        if os.getenv("QINIU_API_KEY"):
            platforms["qiniu"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("QINIU_API_KEY"),
                    base_url=os.getenv("QINIU_BASE_URL", "https://openai.qiniu.com/v1"),
                ),
                "model": os.getenv("QINIU_MODEL", "gpt-oss-120b"),
                "name": "七牛云",
                "enabled": True
            }
        
        # 腾讯混元 (如果配置了)
        if os.getenv("HUNYUAN_API_KEY"):
            platforms["hunyuan"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("HUNYUAN_API_KEY"),
                    base_url=os.getenv("HUNYUAN_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1"),
                ),
                "model": os.getenv("HUNYUAN_MODEL", "hunyuan-turbos-latest"),
                "name": "腾讯混元",
                "enabled": True
            }
        
        print(f"🚀 初始化完成，支持 {len(platforms)} 个平台:")
        for platform_id, config in platforms.items():
            print(f"   - {config['name']} ({platform_id}): {config['model']}")
        
        return platforms
    
    # build_prompt 方法已移至 BaseKeywordExtractor
    
    async def extract_keywords_single_platform(self, model_info: ModelInfo, platform_id: str) -> Optional[Tuple[str, List[Dict[str, str]]]]:
        """使用单个平台提取关键词"""
        if platform_id not in self.platforms or not self.platforms[platform_id]["enabled"]:
            return None
        
        platform = self.platforms[platform_id]
        client = platform["client"]
        model = platform["model"]
        platform_name = platform["name"]
        
        try:
            print(f"🔄 使用 {platform_name} 提取关键词...")
            
            prompt = self.build_prompt(model_info)
            
            # 为腾讯混元添加特殊参数
            extra_params = {}
            if platform_id == "hunyuan":
                extra_params["extra_body"] = {"enable_enhancement": True}
            
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位专业的AI项目运营专家和SEO大师，专门负责从AI模型项目中提取高价值的关键词。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1200,  # 进一步增加token数量，避免响应被截断
                **extra_params
            )
            
            response_content = completion.choices[0].message.content
            
            # 为智谱AI添加详细调试信息
            if platform_id == "zhipu":
                print(f"🔍 智谱AI调试信息:")
                print(f"   响应长度: {len(response_content)} 字符")
                print(f"   响应内容前500字符:")
                print(f"   {response_content[:500]}")
                print(f"   响应内容后500字符:")
                print(f"   {response_content[-500:]}")
                print(f"   完整响应内容:")
                print(f"   {response_content}")
                print(f"   响应内容类型: {type(response_content)}")
            
            keywords = self._parse_keywords_response(response_content)
            
            if keywords:
                print(f"✅ {platform_name} 成功提取 {len(keywords)} 个关键词")
                return platform_id, keywords
            else:
                print(f"❌ {platform_name} 未能提取到有效关键词")
                return None
                
        except Exception as e:
            print(f"❌ {platform_name} 提取失败: {e}")
            return None
    
    async def extract_keywords_concurrent(self, model_info: ModelInfo) -> Optional[KeywordResult]:
        """并发调用多个平台提取关键词"""
        import time
        start_time = time.time()
        
        print(f"🚀 并发调用 {len(self.platforms)} 个平台提取关键词...")
        
        # 创建并发任务
        tasks = []
        for platform_id in self.platforms.keys():
            if self.platforms[platform_id]["enabled"]:
                task = self.extract_keywords_single_platform(model_info, platform_id)
                tasks.append(task)
        
        if not tasks:
            print("❌ 没有可用的平台")
            return None
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ 平台调用异常: {result}")
            elif result is not None:
                platform_id, keywords = result
                successful_results.append((platform_id, keywords))
        
        if not successful_results:
            print("❌ 所有平台都提取失败")
            return None
        
        # 选择最佳结果（优先选择关键词数量最多的）
        best_platform_id, best_keywords = max(successful_results, key=lambda x: len(x[1]))
        best_platform_name = self.platforms[best_platform_id]["name"]
        
        elapsed_time = time.time() - start_time
        print(f"✅ 最佳结果来自 {best_platform_name}: {len(best_keywords)} 个关键词 (总耗时: {elapsed_time:.1f}秒)")
        
        return KeywordResult(
            model_url=model_info.url,
            keywords=best_keywords
        )
    
    # _parse_keywords_response 方法已移至 BaseKeywordExtractor
    
    # _validate_keyword, _clean_keyword, _fix_common_json_errors, _fix_truncated_json 方法已移至 BaseKeywordExtractor
    
    def extract_keywords(self, model_info: ModelInfo) -> Optional[KeywordResult]:
        """实现抽象方法 - 同步版本的关键词提取"""
        return asyncio.run(self.extract_keywords_concurrent(model_info))
    
    async def extract_batch_keywords(self, model_infos: List[ModelInfo]) -> List[KeywordResult]:
        """批量提取关键词（work-stealing版本）"""
        return await self._work_stealing_main(model_infos)
    
    async def _work_stealing_main(self, model_infos: List[ModelInfo]) -> List[KeywordResult]:
        """任务池 + work-stealing 主逻辑"""
        import time
        start_time = time.time()
        
        total = len(model_infos)
        
        # 获取可用的平台
        available_platforms = [pid for pid, config in self.platforms.items() if config["enabled"]]
        platform_count = len(available_platforms)
        
        if platform_count == 0:
            print("❌ 没有可用的平台")
            return []
        
        print(f"🚀 任务池启动，模型 {total} 个，平台 {platform_count} 个")
        
        # 创建任务队列 (ModelInfo, retry_count)
        queue = asyncio.Queue()
        for model_info in model_infos:
            await queue.put((model_info, 0))
        
        # 共享结果列表和锁
        results = []
        lock = asyncio.Lock()
        
        # 创建worker任务
        workers = []
        for platform_id in available_platforms:
            worker = asyncio.create_task(
                self._worker(platform_id, queue, results, lock, platform_count)
            )
            workers.append(worker)
        
        # 等待所有任务完成
        await queue.join()
        
        # 取消所有worker
        for worker in workers:
            worker.cancel()
        
        # 等待worker清理完成
        await asyncio.gather(*workers, return_exceptions=True)
        
        # 计算耗时
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(results) if results else 0
        
        print(f"🚀 任务池处理完成，成功处理 {len(results)} 个模型")
        print(f"⏱️  总耗时: {total_time:.2f}秒，平均耗时: {avg_time:.2f}秒/模型")
        return results
    
    async def _worker(self, platform_id: str, queue: asyncio.Queue, results: List[KeywordResult], 
                     lock: asyncio.Lock, max_retries: int):
        """单个平台的worker协程"""
        platform_name = self.platforms[platform_id]["name"]
        success_count = 0
        
        while True:
            try:
                # 从队列获取任务
                model_info, retry_count = queue.get_nowait()
                
                # 尝试处理模型
                result = await self.extract_keywords_single_platform(model_info, platform_id)
                
                if result:
                    # 成功处理
                    platform_id_result, keywords = result
                    keyword_result = KeywordResult(
                        model_url=model_info.url,
                        keywords=keywords
                    )
                    
                    # 线程安全地添加结果
                    async with lock:
                        results.append(keyword_result)
                    
                    success_count += 1
                    queue.task_done()
                else:
                    # 处理失败，检查是否需要重试
                    if retry_count < max_retries - 1:
                        # 重新放回队列，增加重试次数
                        await queue.put((model_info, retry_count + 1))
                        queue.task_done()
                    else:
                        # 所有平台都试过了，丢弃
                        print(f"⚠️  {model_info.project_name} 所有平台均失败，已丢弃")
                        queue.task_done()
                        
            except asyncio.QueueEmpty:
                # 队列为空，worker退出
                break
            except Exception as e:
                # 单个任务异常，不影响其他任务
                print(f"❌ {platform_name} 处理异常: {e}")
                try:
                    queue.task_done()
                except ValueError:
                    pass  # 如果task_done()被调用多次，忽略错误
        
        print(f"✅ {platform_name} 成功处理 {success_count} 个")
    
    async def extract_keywords_shard(self, platform_id: str, model_infos: List[ModelInfo], start_index: int) -> List[KeywordResult]:
        """单个平台处理分片"""
        platform_name = self.platforms[platform_id]["name"]
        shard_size = len(model_infos)
        
        print(f"🔄 {platform_name} 开始处理分片 (模型 {start_index+1}-{start_index+shard_size})")
        
        results = []
        for i, model_info in enumerate(model_infos):
            model_index = start_index + i + 1
            print(f"   进度: {model_index}/{start_index+shard_size} - {model_info.project_name}")
            
            # 使用单个平台提取关键词
            result = await self.extract_keywords_single_platform(model_info, platform_id)
            
            if result:
                platform_id_result, keywords = result
                keyword_result = KeywordResult(
                    model_url=model_info.url,
                    keywords=keywords
                )
                results.append(keyword_result)
                print(f"   ✅ 成功提取 {len(keywords)} 个关键词")
            else:
                print(f"   ❌ 提取失败")
        
        print(f"✅ {platform_name} 分片处理完成，成功 {len(results)}/{shard_size} 个模型")
        return results


# 同步包装器，保持与原版兼容
class MultiPlatformExtractorSync:
    """多平台关键词提取器（同步版本）"""
    
    def __init__(self):
        self.async_extractor = MultiPlatformExtractor()
    
    def extract_keywords(self, model_info: ModelInfo) -> Optional[KeywordResult]:
        """同步版本的关键词提取"""
        return asyncio.run(self.async_extractor.extract_keywords_concurrent(model_info))
    
    def extract_batch_keywords(self, model_infos: List[ModelInfo]) -> List[KeywordResult]:
        """同步版本的批量提取"""
        return asyncio.run(self.async_extractor.extract_batch_keywords(model_infos))
    
    def deduplicate_keywords(self, keyword_results: List[KeywordResult]) -> List[KeywordResult]:
        """同步版本的关键词去重"""
        return self.async_extractor.deduplicate_keywords(keyword_results)


def test_multi_platform():
    """测试多平台提取功能"""
    import asyncio
    from models import ModelInfo
    
    async def test_async():
        extractor = MultiPlatformExtractor()
        
        # 创建测试模型信息
        test_model = ModelInfo(
            url="https://gitcode.com/hf_mirrors/internlm/Intern-S1-FP8",
            project_name="internlm/Intern-S1-FP8",
            readme="Intern-S1 是一个多模态推理模型，支持文本、图像和视频输入。",
            tags=["多模态", "推理", "Transformers"]
        )
        
        # 测试并发提取
        result = await extractor.extract_keywords_concurrent(test_model)
        
        if result:
            print(f"\n模型: {result.model_url}")
            print("提取的关键词:")
            for kw in result.keywords:
                print(f"- {kw['keyword']} ({kw['dimension']}): {kw['reason']}")
        else:
            print("关键词提取失败")
    
    asyncio.run(test_async())


if __name__ == "__main__":
    test_multi_platform()
