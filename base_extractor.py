"""
基础关键词提取器 - 提取公共代码
"""
import os
import re
import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from models import ModelInfo, KeywordResult


class BaseKeywordExtractor(ABC):
    """基础关键词提取器抽象类"""
    
    def __init__(self):
        """初始化排除队列相关属性"""
        self.keyword_frequency = {}  # 关键词频率统计
        self.excluded_keywords = []  # 排除队列
    
    def update_exclusion_queue(self, keywords: List[Dict[str, str]]):
        """更新排除队列 - 每处理一个模型后调用"""
        # 统计频率
        for kw_dict in keywords:
            keyword = kw_dict.get('keyword', '')
            self.keyword_frequency[keyword] = self.keyword_frequency.get(keyword, 0) + 1
        
        # 筛选高频词（出现≥10次）
        high_freq_keywords = [
            kw for kw, count in self.keyword_frequency.items() 
            if count >= 10
        ]
        
        # 按频率排序，取Top 50
        high_freq_keywords.sort(
            key=lambda k: self.keyword_frequency[k], 
            reverse=True
        )
        self.excluded_keywords = high_freq_keywords[:50]
    
    def build_prompt(self, model_info: ModelInfo) -> str:
        """
        根据需求文档构建Prompt
        
        Args:
            model_info: 模型信息
            
        Returns:
            构建好的prompt
        """
        prompt = f"""你是AI项目运营专家，你需要在模型页面中提取引流关键词以便投放到博客网站当中。

项目: {model_info.project_name}
URL: {model_info.url}

README内容（前800字符）：
{(model_info.readme[:800] + "...") if model_info.readme and len(model_info.readme) > 800 else (model_info.readme if model_info.readme else "暂无README内容")}

标签: {', '.join(model_info.tags) if model_info.tags else "暂无标签"}

## 核心原则：高亮词是"用户搜索AI模型时会用的词"

**引流逻辑**：
用户在CSDN搜索"SD-XL" → 看到博客 → 点击博客中的"SD-XL"高亮词 → 跳转到GitCode查看SD-XL模型

**⚠️ 最重要规则：只提取当前模型自身的关键词，严禁提取其他模型的名称**

**正确示例**：
- ✅ 当前模型：DeepSeek-R1-Distill-Qwen → 提取：DeepSeek-R1、链式思维、自我验证
- ❌ README提到"超越OpenAI-o1" → 不要提取"OpenAI-o1"（这是其他模型）
- ❌ README提到"基于Qwen2.5" → 不要提取"Qwen2.5"（这是基础模型，不是当前模型）
- ❌ README提到"对标GPT-4" → 不要提取"GPT-4"（这是对比对象，不是当前模型）

**因此高亮词必须是当前模型自身的**：
- ✅ 当前模型的名称（从项目名称提取，如DeepSeek-R1、JanusFlow、GLM-4）
- ✅ 当前模型的功能/用途（文生图、编程助手、AI写作）
- ✅ 当前模型的部署方式（Ollama部署、本地部署、ComfyUI）
- ✅ 当前模型的技术特性（多模态、量化模型、MoE架构、链式思维）

**严禁提取**：
- ❌ **其他模型名称**（OpenAI-o1、GPT-4、Claude、Qwen2.5、Llama等）→ README中作为对比/基础的模型
- ❌ 硬件相关（消费级显卡、A100、GPU）→ 用户搜这个是买显卡，不是找模型
- ❌ 通用形容词（高效、高清、强大、优秀）→ 太泛泛，没有指向性
- ❌ 技术细节（128K词表、8192上下文长度）→ 太专业，普通用户不搜

## 提取规则（严格遵守）
1. 基于原文内容，提取5-8个**用户会搜索的AI模型相关词**
2. **模型名称简化**：
   - ✅ JanusFlow、GLM-4、DeepSeek-V2、SD-XL（简洁品牌名）
   - ❌ JanusFlow-1.3B、GLM-4-32B-0414（带版本号太长）
3. **功能场景词**：
   - ✅ 文生图、AI写作、编程助手、智能对话（用户搜索意图明确）
   - ❌ 高效处理、高清生成（太泛泛）
4. **连接符使用规范**：
   - ✅ SD-XL、BERT-base、DeepSeek-V2（英文-英文可以用连字符）
   - ✅ 文生图、编程助手、AI写作（纯中文，不需要连字符）
   - ✅ PyTorch、Transformer、HuggingFace（纯英文，不需要连字符）
   - ❌ 文生图-TextToImage、编程助手-CodeAssistant（中文-英文禁止用连字符）
5. **参数规格**：
   - ✅ 7B参数、32B参数（主流规格，用户会搜）
   - ❌ 304M参数、1.68倍加速（太细节或性能指标）
6. **严禁提取（特别重要）**：
   - ❌ **其他模型名称**（OpenAI-o1、GPT-4、Claude、Gemini、Qwen2.5、Llama3、Mistral等）
     → README中作为对比、基础、参考的其他模型，绝对不能提取
   - ❌ 硬件词汇（消费级显卡、A100、GPU、显存）
   - ❌ 通用形容词（高效、高清、强大、优秀、先进）
   - ❌ 纯数字（50.0、1860863627）
   - ❌ 性能指标（1.68倍加速、250倍加速）
   - ❌ 过长描述（Colab免费GPU支持、A100H100推理）
   - ❌ 技术细节（128K词表、8192输入长度）
   - ❌ 抽象概念（定理证明、零样本预测）
   - ❌ 语言类型（英文摘要、中文、多语言）
   - ❌ **中文-英文格式**（文生图-TextToImage、编程助手-CodeAssistant）

## 5个维度（用户搜索AI模型时会用的词）
1. **当前模型品牌名**: 只提取当前模型的名称（从项目名称提取）
   - ✅ 示例：JanusFlow、GLM-4、DeepSeek-R1、SD-XL、MiniCPM
   - ❌ 禁止：OpenAI-o1、GPT-4、Claude（README中提到的其他模型）
   
   **⚠️ 国产大模型品牌名映射规则（必须遵守）**：
   - ERNIE → 提取"文心一言"或"百度大模型"
   - Qwen → 提取"通义千问"或"阿里大模型"
   - Hunyuan → 提取"混元"或"腾讯大模型"
   - GLM-4 → 提取"智谱AI"
   - ByteDance-Seed → 提取"豆包"或"字节大模型"
   - MoonshotAI → 提取"Kimi"或"月之暗面"

2. **功能场景**: 文生图、文生视频、AI写作、编程助手、智能对话、图像修复
3. **部署工具**: Ollama部署、本地部署、ComfyUI、量化模型、API调用
4. **技术特性**: 多模态、MoE架构、Transformer、自回归模型、链式思维
5. **参数规格**: 7B参数、32B参数、671B参数（仅主流规格）

## 格式规范（真实写作习惯）
- ✅ **英文-英文**：SD-XL、BERT-base、DeepSeek-V2（可以用连字符）
- ✅ **纯中文**：编程助手、AI写作、文生图
- ✅ **纯英文**：Transformer、PyTorch、HuggingFace
- ❌ **中文-英文**：文生图-TextToImage、编程助手-CodeAssistant（禁止用连字符连接中英文）

## 输出示例（用户在CSDN搜索时会用的词）

**示例1 - 普通模型**：
{{
  "keywords": [
    {{
      "keyword": "DeepSeek-R1",
      "dimension": "当前模型品牌名", 
      "reason": "从项目名称提取的当前模型名称"
    }},
    {{
      "keyword": "链式思维",
      "dimension": "技术特性",
      "reason": "当前模型的核心技术特性"
    }},
    {{
      "keyword": "编程助手",
      "dimension": "功能场景",
      "reason": "当前模型的应用场景"
    }}
  ]
}}

**示例2 - 国产大模型（遵循映射规则）**：
{{
  "keywords": [
    {{
      "keyword": "通义千问",
      "dimension": "当前模型品牌名", 
      "reason": "项目名称中有Qwen，映射为通义千问"
    }},
    {{
      "keyword": "阿里大模型",
      "dimension": "当前模型品牌名", 
      "reason": "Qwen属于阿里大模型系列"
    }},
    {{
      "keyword": "7B参数",
      "dimension": "参数规格",
      "reason": "当前模型的参数规格"
    }}
  ]
}}

⚠️ **错误示例（绝对禁止）**：
- ❌ 提取"OpenAI-o1"（这是README中作为对比的其他模型）
- ❌ 提取"Qwen2.5"（如果当前模型不是Qwen2.5，不要提取）
- ❌ 提取"GPT-4"（这是README中作为参考的其他模型）
- ❌ 提取"Qwen"（应该映射为"通义千问"或"阿里大模型"）

要求：5-8个关键词，每个包含keyword、dimension、reason字段。"""

        # 添加排除队列（如果有的话）
        exclusion_text = ""
        if self.excluded_keywords:
            exclusion_text = f"""

## 🚫 强制排除关键词（高频词）
以下关键词已被大量使用，**严禁再次提取**：
{', '.join(self.excluded_keywords[:50])}

你必须提取该模型**独特的、有区分度的**关键词，避开上述所有高频词。
"""
            prompt += exclusion_text

        return prompt
    
    def _parse_keywords_response(self, response: str) -> List[Dict[str, str]]:
        """
        解析AI响应中的关键词JSON
        
        Args:
            response: AI响应内容
            
        Returns:
            关键词列表
        """
        try:
            # 第一步：尝试直接解析（AI应该返回标准JSON）
            cleaned_response = response.strip()
            
            # 清理可能的中文引号问题
            json_str = cleaned_response.replace('"', '"').replace('"', '"')
            json_str = json_str.replace(''', "'").replace(''', "'")
            
            # 直接尝试解析
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON部分
                if '```json' in json_str:
                    start = json_str.find('```json') + 7
                    end = json_str.find('```', start)
                    if end != -1:
                        json_str = json_str[start:end].strip()
                    else:
                        json_str = json_str[start:].strip()
                else:
                    # 查找JSON对象边界
                    start_pos = json_str.find('{')
                    if start_pos != -1:
                        end_pos = json_str.rfind('}')
                        if end_pos != -1 and end_pos > start_pos:
                            json_str = json_str[start_pos:end_pos+1]
                
                # 再次清理和解析
                json_str = json_str.replace('"', '"').replace('"', '"')
                json_str = json_str.replace(''', "'").replace(''', "'")
                
                # 尝试修复常见的JSON格式错误
                json_str = self._fix_common_json_errors(json_str)
                
                # 尝试修复截断的JSON
                json_str = self._fix_truncated_json(json_str)
                
                data = json.loads(json_str)
            
            keywords = data.get('keywords', [])
            
            # 验证关键词数量（适度放宽至3-8个以减少失败率）
            if len(keywords) < 3:
                print(f"⚠️ 关键词数量不足：只有{len(keywords)}个，要求至少3个")
                return []
            elif len(keywords) > 8:
                print(f"⚠️ 关键词数量过多：有{len(keywords)}个，要求3-8个，取前8个")
                keywords = keywords[:8]
            else:
                print(f"✅ 关键词数量符合要求：{len(keywords)}个")
            
            # 验证和清理关键词
            cleaned_keywords = []
            for kw in keywords:
                if self._validate_keyword(kw):
                    cleaned_kw = self._clean_keyword(kw)
                    # 只检查当前模型内的重复，不跨模型去重
                    current_keywords = [k['keyword'] for k in cleaned_keywords]
                    if cleaned_kw['keyword'] not in current_keywords:
                        cleaned_keywords.append(cleaned_kw)
            
            return cleaned_keywords
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"📝 AI完整返回内容:")
            print("=" * 80)
            print(response[:1500] + ("..." if len(response) > 1500 else ""))
            print("=" * 80)
            print("💡 提示：AI可能没有按照要求的JSON格式返回")
            return []
        except Exception as e:
            print(f"❌ 解析响应时出错: {e}")
            print(f"📝 AI完整返回内容:")
            print("=" * 80)
            print(response[:1500] + ("..." if len(response) > 1500 else ""))
            print("=" * 80)
            return []
    
    def _validate_keyword(self, keyword_obj: Dict[str, str]) -> bool:
        """
        验证关键词对象是否有效
        
        Args:
            keyword_obj: 关键词对象
            
        Returns:
            是否有效
        """
        required_fields = ['keyword', 'dimension', 'reason']
        return all(field in keyword_obj and keyword_obj[field].strip() for field in required_fields)
    
    def _clean_keyword(self, keyword_obj: Dict[str, str]) -> Dict[str, str]:
        """
        清理关键词，确保符合格式要求
        
        Args:
            keyword_obj: 原始关键词对象
            
        Returns:
            清理后的关键词对象
        """
        keyword = keyword_obj['keyword'].strip()
        
        # 移除括号
        keyword = re.sub(r'[()（）]', '', keyword)
        
        # 替换空格为连字符
        keyword = re.sub(r'\s+', '-', keyword)
        
        # 只保留中英文、数字、连字符、点号
        keyword = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\.-]', '', keyword)
        
        # 移除连续的连字符和点号
        keyword = re.sub(r'-+', '-', keyword)
        keyword = re.sub(r'\.+', '.', keyword)
        
        # 移除首尾连字符和点号
        keyword = keyword.strip('-.')
        
        # 但保留版本号格式（如v2.0, FLUX.1等）
        # 如果关键词以v开头且包含点号，保留它
        if keyword.lower().startswith('v') and '.' in keyword:
            pass  # 保持原样，不再处理
        # 如果是常见的版本号格式，也保留
        elif re.match(r'^[A-Za-z0-9]+\.[0-9]+$', keyword):
            pass  # 保持原样，如FLUX.1, GPT.4等
        
        # 品牌名称智能扩展策略
        keyword = self._enhance_brand_keywords(keyword, keyword_obj['dimension'])
        
        return {
            'keyword': keyword,
            'dimension': keyword_obj['dimension'].strip(),
            'reason': keyword_obj['reason'].strip()
        }
    
    def _fix_common_json_errors(self, json_str: str) -> str:
        """
        修复AI生成JSON中的常见错误
        
        Args:
            json_str: 待修复的JSON字符串
            
        Returns:
            修复后的JSON字符串
        """
        import re
        
        # 修复缺失开括号的情况：},\n  "keyword" → },\n  {"keyword"
        # 匹配：},后面跟着换行和空格，然后直接是"keyword"（而不是{）
        pattern = r'(\},\s*\n\s*)("keyword":)'
        json_str = re.sub(pattern, r'\1{\2', json_str)
        
        # 修复多余逗号的情况：},\n  }\n] → }\n  }\n]
        json_str = re.sub(r',(\s*\}\s*\])', r'\1', json_str)
        
        # 修复缺失逗号的情况：}\n  { → },\n  {
        json_str = re.sub(r'(\})\s*\n\s*(\{)', r'\1,\n  \2', json_str)
        
        return json_str
    
    def _fix_truncated_json(self, json_str: str) -> str:
        """修复截断的JSON"""
        import re
        
        # 如果JSON被截断，尝试修复
        if not json_str.endswith('}'):
            # 查找最后一个完整的对象
            last_complete_obj = json_str.rfind('}')
            if last_complete_obj != -1:
                # 检查是否在keywords数组中
                before_last = json_str[:last_complete_obj]
                if '"keywords"' in before_last:
                    # 尝试找到最后一个完整的keyword对象
                    keyword_objects = re.findall(r'\{[^}]*"keyword"[^}]*\}', before_last)
                    if keyword_objects:
                        # 使用最后一个完整的keyword对象
                        last_keyword = keyword_objects[-1]
                        # 重新构建JSON
                        json_str = before_last[:before_last.rfind(last_keyword)] + last_keyword + '}]}'
                    else:
                        # 如果没有完整的keyword对象，尝试添加缺失的结束符
                        json_str = before_last + '}]}'
        
        return json_str
    
    def _enhance_brand_keywords(self, keyword: str, dimension: str) -> str:
        """
        品牌关键词智能扩展策略
        
        Args:
            keyword: 原始关键词
            dimension: 关键词维度
            
        Returns:
            扩展后的关键词
        """
        # 只对"品牌与身份"维度的关键词进行扩展
        if dimension != "品牌与身份":
            return keyword
        
        # 定义需要扩展的品牌名称列表
        brand_names = {
            # 中国大厂
            "百度": "百度大模型",
            "腾讯": "腾讯大模型", 
            "阿里": "阿里大模型",
            "阿里巴巴": "阿里巴巴大模型",
            "字节": "字节大模型",
            "字节跳动": "字节跳动大模型",
            "华为": "华为大模型",
            "小米": "小米大模型",
            "快手": "快手大模型",
            "网易": "网易大模型",
            "京东": "京东大模型",
            "美团": "美团大模型",
            "滴滴": "滴滴大模型",
            
            # 国际大厂
            "OpenAI": "OpenAI大模型",
            "Google": "Google大模型", 
            "谷歌": "谷歌大模型",
            "Microsoft": "Microsoft大模型",
            "微软": "微软大模型",
            "Meta": "Meta大模型",
            "Facebook": "Facebook大模型",
            "Amazon": "Amazon大模型",
            "亚马逊": "亚马逊大模型",
            "Apple": "Apple大模型",
            "苹果": "苹果大模型",
            "NVIDIA": "NVIDIA大模型",
            "英伟达": "英伟达大模型",
            
            # AI创业公司
            "智谱": "智谱大模型",
            "月之暗面": "月之暗面大模型",
            "零一万物": "零一万物大模型",
            "深度求索": "深度求索大模型",
            "商汤": "商汤大模型",
            "旷视": "旷视大模型",
            "科大讯飞": "科大讯飞大模型",
            "云知声": "云知声大模型",
            "出门问问": "出门问问大模型",
            "小冰": "小冰大模型"
        }
        
        # 检查是否为需要扩展的品牌名称
        for brand, enhanced in brand_names.items():
            if keyword == brand:
                print(f"🔄 品牌扩展: {brand} → {enhanced}")
                return enhanced
        
        return keyword
    
    def deduplicate_keywords(self, keyword_results: List[KeywordResult]) -> List[KeywordResult]:
        """
        不进行去重，直接返回原始结果
        去重将在CSV生成阶段统一处理
        
        Args:
            keyword_results: 关键词提取结果列表
            
        Returns:
            原始结果列表（无去重）
        """
        print("跳过关键词去重，将在CSV生成时统一去重")
        return keyword_results
    
    def _is_similar_keyword_exists(self, keyword: str, existing_keywords: set) -> bool:
        """
        检查是否存在相似的关键词（宽松版：只检查完全重复）
        
        Args:
            keyword: 待检查的关键词
            existing_keywords: 已存在的关键词集合
            
        Returns:
            是否存在相似关键词
        """
        keyword_lower = keyword.lower()
        
        for existing in existing_keywords:
            existing_lower = existing.lower()
            
            # 只检查完全相同的情况，不再检查包含关系
            # 这样可以保留更多有意义的关键词变体
            if keyword_lower == existing_lower:
                return True
        
        return False
    
    @abstractmethod
    def extract_keywords(self, model_info: ModelInfo) -> Optional[KeywordResult]:
        """提取关键词的抽象方法"""
        pass
    
    @abstractmethod
    def extract_batch_keywords(self, model_infos: List[ModelInfo]) -> List[KeywordResult]:
        """批量提取关键词的抽象方法"""
        pass
