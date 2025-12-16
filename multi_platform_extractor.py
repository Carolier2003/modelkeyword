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
    
    def __init__(self, workers_per_platform: int = None):
        """
        初始化多个AI客户端
        
        Args:
            workers_per_platform: 每个平台的并发 worker 数量（None 时从环境变量读取或自动计算）
        """
        super().__init__()  # 调用基类初始化
        self.platforms = self._init_platforms()
        
        # 如果未指定，尝试从环境变量读取，否则自动计算
        if workers_per_platform is None:
            env_workers = os.getenv("WORKERS_PER_PLATFORM")
            if env_workers:
                try:
                    self.workers_per_platform = int(env_workers)
                except ValueError:
                    print(f"⚠️ 环境变量 WORKERS_PER_PLATFORM={env_workers} 无效，使用默认值")
                    self.workers_per_platform = self._calculate_default_workers()
            else:
                self.workers_per_platform = self._calculate_default_workers()
        else:
            self.workers_per_platform = workers_per_platform
        
        print(f"📊 并发配置：每个平台 {self.workers_per_platform} 个 worker")
    
    def _calculate_default_workers(self) -> int:
        """根据平台数量自动计算默认 worker 数量"""
        platform_count = len([p for p in self.platforms.values() if p.get("enabled", True)])
        # 单个平台时默认 5 个 worker，多个平台时每个平台 1 个
        return 5 if platform_count == 1 else 1
        
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
        
        # 硅基流动 (如果配置了)
        if os.getenv("SILICONFLOW_API_KEY"):
            platforms["siliconflow"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("SILICONFLOW_API_KEY"),
                    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
                ),
                "model": os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen3-Next-80B-A3B-Instruct"),
                "name": "硅基流动",
                "enabled": True
            }
        
        # 火山引擎 (如果配置了)
        if os.getenv("VOLCENGINE_API_KEY"):
            platforms["volcengine"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("VOLCENGINE_API_KEY"),
                    base_url=os.getenv("VOLCENGINE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
                ),
                "model": os.getenv("VOLCENGINE_MODEL", "doubao-1-5-pro-32k-250115"),
                "name": "火山引擎",
                "enabled": True
            }
        
        # 百度千帆 (如果配置了)
        if os.getenv("QIANFAN_API_KEY"):
            platforms["qianfan"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("QIANFAN_API_KEY"),
                    base_url=os.getenv("QIANFAN_BASE_URL", "https://qianfan.baidubce.com"),
                ),
                "model": os.getenv("QIANFAN_MODEL", "ernie-4.5-turbo-128k"),
                "name": "百度千帆",
                "enabled": True
            }
        
        # 讯飞星火 (如果配置了)
        if os.getenv("SPARK_API_KEY"):
            platforms["spark"] = {
                "client": AsyncOpenAI(
                    api_key=os.getenv("SPARK_API_KEY"),
                    base_url=os.getenv("SPARK_BASE_URL", "https://spark-api-open.xf-yun.com/v2"),
                ),
                "model": os.getenv("SPARK_MODEL", "x1"),
                "name": "讯飞星火",
                "enabled": True
            }
        
        print(f"🚀 初始化完成，支持 {len(platforms)} 个平台:")
        for platform_id, config in platforms.items():
            print(f"   - {config['name']} ({platform_id}): {config['model']}")
        
        return platforms
    
    # build_prompt 方法已移至 BaseKeywordExtractor
    
    async def extract_keywords_single_platform(self, model_info: ModelInfo, platform_id: str) -> Optional[Tuple[str, List[Dict[str, str]]]]:
        """使用单个平台提取关键词"""
        import time
        start_time = time.time()
        
        if platform_id not in self.platforms or not self.platforms[platform_id]["enabled"]:
            return None
        
        platform = self.platforms[platform_id]
        client = platform["client"]
        model = platform["model"]
        platform_name = platform["name"]
        
        # 提取模型名称用于显示
        model_name = model_info.url.split('/')[-2:] if '/' in model_info.url else [model_info.url]
        model_name = '/'.join(model_name)
        
        try:
            print(f"🔄 使用 {platform_name} 处理 {model_name}...")
            
            prompt = self.build_prompt(model_info)
            
            # 为腾讯混元、百度千帆、火山引擎、阿里百炼添加特殊参数
            extra_params = {}
            if platform_id == "hunyuan":
                extra_params["extra_body"] = {"enable_enhancement": True}
            elif platform_id == "qianfan":
                extra_params["extra_body"] = {
                    "penalty_score": 1,
                    "stop": [],
                    "web_search": {
                        "enable": False,
                        "enable_trace": False
                    }
                }
            elif platform_id == "volcengine":
                extra_params["extra_body"] = {
                    "thinking": {
                        "type": "disabled"  # 禁用深度思考能力，加快响应速度
                    }
                }
            elif platform_id == "dashscope":
                extra_params["extra_body"] = {
                    "enable_thinking": False  # 关闭思考功能，加快响应速度
                }
            
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
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if keywords:
                print(f"✅ {platform_name} 成功处理 {model_name} ({processing_time:.2f}s) - 提取 {len(keywords)} 个关键词")
                return platform_id, keywords
            else:
                print(f"❌ {platform_name} 处理 {model_name} ({processing_time:.2f}s) - 未能提取到有效关键词")
                return None
                
        except Exception as e:
            end_time = time.time()
            processing_time = end_time - start_time
            error_msg = str(e)
            print(f"❌ {platform_name} 处理 {model_name} ({processing_time:.2f}s) - 提取失败: {e}")
            
            # 检查是否是API限制错误（429/503）
            if "429" in error_msg or "503" in error_msg or "rate_limit" in error_msg.lower() or "too busy" in error_msg.lower():
                # 计算延迟时间：基础延迟 + 随机延迟
                import random
                base_delay = 1  # 减少基础延迟到1秒
                random_delay = random.uniform(0.5, 1.5)  # 减少随机延迟
                total_delay = base_delay + random_delay
                
                print(f"⏳ {platform_name} 遇到API限制，等待 {total_delay:.1f} 秒后重试...")
                await asyncio.sleep(total_delay)
            
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
        
        # 计算总 worker 数量
        total_workers = platform_count * self.workers_per_platform
        
        print(f"🚀 任务池启动，模型 {total} 个，平台 {platform_count} 个")
        print(f"🔥 并发模式：每个平台 {self.workers_per_platform} 个 worker，共 {total_workers} 个并发 worker")
        
        # 创建任务队列 (ModelInfo, retry_count)
        queue = asyncio.Queue()
        for model_info in model_infos:
            await queue.put((model_info, 0))
        
        # 共享结果列表和锁
        results = []
        lock = asyncio.Lock()
        
        # 进度跟踪
        progress_lock = asyncio.Lock()
        completed_count = [0]  # 使用列表以便在不同协程间共享
        
        # 创建worker任务：为每个平台创建多个 worker
        workers = []
        for platform_id in available_platforms:
            for worker_idx in range(self.workers_per_platform):
                worker = asyncio.create_task(
                    self._worker(platform_id, queue, results, lock, platform_count, progress_lock, completed_count, total)
                )
                workers.append(worker)
        
        # 启动进度监控任务
        progress_task = asyncio.create_task(
            self._progress_monitor(progress_lock, completed_count, total, start_time)
        )
        
        # 等待所有任务完成
        await queue.join()
        
        # 取消所有worker和进度监控
        for worker in workers:
            worker.cancel()
        progress_task.cancel()
        
        # 等待worker清理完成
        await asyncio.gather(*workers, return_exceptions=True)
        
        # 计算耗时
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(results) if results else 0
        
        print(f"\n🚀 任务池处理完成，成功处理 {len(results)} 个模型")
        print(f"⏱️  总耗时: {total_time:.2f}秒，平均耗时: {avg_time:.2f}秒/模型")
        return results
    
    async def _progress_monitor(self, progress_lock: asyncio.Lock, completed_count: int, total: int, start_time: float):
        """进度监控任务"""
        import time
        
        while True:
            try:
                await asyncio.sleep(1)  # 每1秒更新一次进度
                
                async with progress_lock:
                    current_completed = completed_count[0]
                
                if current_completed >= total:
                    break
                
                # 计算进度
                progress_percent = (current_completed / total) * 100
                elapsed_time = time.time() - start_time
                
                # 计算预估剩余时间
                if current_completed > 0:
                    avg_time_per_model = elapsed_time / current_completed
                    remaining_models = total - current_completed
                    estimated_remaining = avg_time_per_model * remaining_models
                else:
                    estimated_remaining = 0
                
                # 创建进度条
                bar_length = 30
                filled_length = int(bar_length * current_completed // total)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                # 显示进度
                print(f"\r📊 进度: [{bar}] {current_completed}/{total} ({progress_percent:.1f}%) | 已用时: {elapsed_time:.1f}s | 预计剩余: {estimated_remaining:.1f}s", end='', flush=True)
                
            except asyncio.CancelledError:
                break
            except Exception:
                break
    
    async def _worker(self, platform_id: str, queue: asyncio.Queue, results: List[KeywordResult], 
                     lock: asyncio.Lock, max_retries: int, progress_lock: asyncio.Lock, completed_count: int, total: int):
        """单个平台的worker协程"""
        platform_name = self.platforms[platform_id]["name"]
        success_count = 0
        consecutive_failures = 0  # 连续失败计数
        
        while True:
            try:
                # 从队列获取任务
                model_info, retry_count = queue.get_nowait()
                
                # 如果连续失败次数过多，增加延迟
                if consecutive_failures > 2:
                    delay = min(consecutive_failures * 0.5, 3.0)  # 最多延迟3秒
                    print(f"⏳ {platform_name} 连续失败 {consecutive_failures} 次，延迟 {delay:.1f} 秒...")
                    await asyncio.sleep(delay)
                
                # 显示开始处理
                print(f"🔄 使用 {platform_name} 处理 {model_info.project_name}...")
                
                # 尝试处理模型
                result = await self.extract_keywords_single_platform(model_info, platform_id)
                
                if result:
                    # 成功处理，重置连续失败计数
                    consecutive_failures = 0
                    platform_id_result, keywords = result
                    keyword_result = KeywordResult(
                        model_url=model_info.url,
                        keywords=keywords
                    )
                    
                    # 线程安全地添加结果
                    async with lock:
                        results.append(keyword_result)
                        # ✨ 实时更新排除队列
                        self.update_exclusion_queue(keywords)
                    
                    # 更新进度计数
                    async with progress_lock:
                        completed_count[0] += 1
                    
                    success_count += 1
                    queue.task_done()
                else:
                    # 处理失败，增加连续失败计数
                    consecutive_failures += 1
                    
                    # 检查是否需要重试
                    if retry_count < max_retries - 1:
                        # 重新放回队列，增加重试次数
                        await queue.put((model_info, retry_count + 1))
                        queue.task_done()
                    else:
                        # 所有平台都试过了，丢弃
                        print(f"\n⚠️  {model_info.project_name} 所有平台均失败，已丢弃")
                        
                        # 更新进度计数（即使失败也算完成）
                        async with progress_lock:
                            completed_count[0] += 1
                        
                        queue.task_done()
                        
            except asyncio.QueueEmpty:
                # 队列为空，worker退出
                break
            except Exception as e:
                # 单个任务异常，增加连续失败计数
                consecutive_failures += 1
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
    
    def __init__(self, workers_per_platform: int = None):
        """
        初始化同步版本提取器
        
        Args:
            workers_per_platform: 每个平台的并发 worker 数量（None 时自动计算）
        """
        self.async_extractor = MultiPlatformExtractor(workers_per_platform=workers_per_platform)
    
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
