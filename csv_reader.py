"""
CSV数据读取器 - 从本地CSV文件读取HuggingFace模型数据，并使用爬虫获取详细信息
"""
import csv
import requests
import time
import json
from typing import List, Optional
from urllib.parse import urlparse
from tqdm import tqdm
from bs4 import BeautifulSoup

from models import ModelInfo
from hf_scraper import scrape_hf_model_sync


class CSVModelReader:
    """CSV模型数据读取器"""
    
    def __init__(self, csv_file: str = "huggingface模型数据_202509241526.csv", delay: float = 0.1, token: Optional[str] = None):
        """
        初始化CSV读取器
        
        Args:
            csv_file: CSV文件路径
            delay: 爬取详细信息时的延迟时间
            token: 可选的认证token
        """
        self.csv_file = csv_file
        self.delay = delay
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        })
    
    def read_csv_data(self, max_models: int = 100) -> List[dict]:
        """
        从CSV文件读取符合条件的模型数据
        
        Args:
            max_models: 最大模型数量
            
        Returns:
            符合条件的模型数据列表
        """
        models = []
        
        try:
            print(f"📖 开始读取CSV文件: {self.csv_file}")
            
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    # 检查是否符合筛选条件：审核状态为2，是否公开为1
                    if (row.get('审核状态') == '2' and 
                        row.get('是否公开') == '1' and 
                        row.get('项目名称') and 
                        row.get('项目网址')):
                        
                        models.append({
                            'id': row.get('项目ID', ''),
                            'name': row.get('项目名称', ''),
                            'url': row.get('项目网址', ''),
                            'audit_status': row.get('审核状态', ''),
                            'is_public': row.get('是否公开', '')
                        })
                        
                        if len(models) >= max_models:
                            break
            
            print(f"✅ 从CSV读取到 {len(models)} 个符合条件的模型")
            return models
            
        except FileNotFoundError:
            print(f"❌ 找不到CSV文件: {self.csv_file}")
            return []
        except Exception as e:
            print(f"❌ 读取CSV文件时出错: {e}")
            return []
    
    def convert_csv_to_model_info(self, csv_model: dict) -> ModelInfo:
        """
        将CSV数据转换为ModelInfo对象
        
        Args:
            csv_model: CSV中的模型数据
            
        Returns:
            ModelInfo对象
        """
        project_name = csv_model['name']
        model_url = csv_model['url']
        
        # 从URL中提取更规范的项目名称
        parsed_url = urlparse(model_url)
        if parsed_url.path:
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2:
                # 去掉可能的前缀如 hf_mirrors
                if path_parts[0] in ['hf_mirrors', 'mirrors']:
                    if len(path_parts) >= 3:
                        project_name = '/'.join(path_parts[1:])
                    else:
                        project_name = '/'.join(path_parts[1:]) if len(path_parts) > 1 else path_parts[-1]
                else:
                    project_name = '/'.join(path_parts[-2:]) if len(path_parts) >= 2 else path_parts[-1]
        
        return ModelInfo(
            url=model_url,
            project_name=project_name,
            readme="",  # 由AI访问URL获取
            tags=[]     # 由AI访问URL获取
        )
    
    def get_model_detail_from_scraper(self, model_info: ModelInfo) -> ModelInfo:
        """
        使用爬虫获取模型的详细信息
        
        Args:
            model_info: 基础模型信息
            
        Returns:
            包含详细信息的ModelInfo对象
        """
        try:
            print(f"正在使用爬虫获取模型详细信息: {model_info.project_name}")
            
            # 使用爬虫获取详细信息
            scraped_data = scrape_hf_model_sync(model_info.url, self.token)
            
            if scraped_data and scraped_data.get("name") != "Error":
                # 更新模型信息
                model_info.readme = scraped_data.get("readme", "")
                
                # 解析标签JSON字符串
                tags_json = scraped_data.get("tags", "[]")
                try:
                    tags = json.loads(tags_json)
                    model_info.tags = tags
                except json.JSONDecodeError:
                    print(f"⚠️ 标签JSON解析失败: {tags_json}")
                    model_info.tags = []
                
                print(f"✅ 成功获取模型信息: README长度={len(model_info.readme)}, 标签数={len(model_info.tags)}")
            else:
                print(f"❌ 爬虫获取失败: {model_info.url}")
                # 保持原有的空值
                model_info.readme = ""
                model_info.tags = []
            
            return model_info
            
        except Exception as e:
            print(f"❌ 爬虫获取模型详细信息失败 {model_info.url}: {e}")
            # 保持原有的空值
            model_info.readme = ""
            model_info.tags = []
            return model_info

    def get_model_detail_from_web(self, model_info: ModelInfo) -> ModelInfo:
        """
        从网页获取模型的详细信息（备用方法，已废弃）
        
        Args:
            model_info: 基础模型信息
            
        Returns:
            包含详细信息的ModelInfo对象
        """
        try:
            print(f"正在获取模型详细信息: {model_info.project_name}")
            
            response = self.session.get(model_info.url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取README内容
            readme = self._extract_readme(soup)
            model_info.readme = readme
            
            # 提取标签
            tags = self._extract_tags(soup)
            model_info.tags = tags
            
            return model_info
            
        except Exception as e:
            print(f"获取模型详细信息失败 {model_info.url}: {e}")
            return model_info
    
    def _extract_readme(self, soup: BeautifulSoup) -> str:
        """提取README内容"""
        readme_content = ""
        
        # 常见的README容器选择器
        readme_selectors = [
            'div[data-target="readme-toc.content"]',
            '.markdown-body',
            '#readme',
            '.readme',
            'article',
            '[class*="readme"]',
            '[id*="readme"]',
            '.description'
        ]
        
        for selector in readme_selectors:
            readme_div = soup.select_one(selector)
            if readme_div:
                readme_content = readme_div.get_text(strip=True)
                break
        
        # 如果没找到专门的README区域，尝试获取主要内容
        if not readme_content:
            content_selectors = [
                'main',
                '.content',
                '.main-content',
                'article',
                '.description'
            ]
            
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    readme_content = content_div.get_text(strip=True)
                    break
        
        return readme_content[:5000]  # 限制长度避免过大
    
    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """提取项目标签"""
        tags = []
        
        # 查找标签的常见结构
        tag_selectors = [
            '.tag', '.badge', '.label', '.topic-tag',
            '[class*="tag"]', '[class*="badge"]', '[class*="label"]',
            '.aiHubTag', '.model-tag'
        ]
        
        for selector in tag_selectors:
            tag_elements = soup.select(selector)
            for elem in tag_elements:
                tag_text = elem.get_text(strip=True)
                if tag_text and tag_text not in tags and len(tag_text) < 50:  # 过滤过长的文本
                    tags.append(tag_text)
            
            if tags:  # 如果找到标签就停止
                break
        
        return tags[:15]  # 限制标签数量
    
    def crawl_models(self, max_models: int = 100, fetch_details: bool = True) -> List[ModelInfo]:
        """
        从CSV文件获取模型信息，并使用爬虫获取详细信息
        
        Args:
            max_models: 最大模型数量
            fetch_details: 是否获取详细信息（现在默认为True）
            
        Returns:
            模型信息列表
        """
        # 从CSV读取基础数据
        csv_models = self.read_csv_data(max_models)
        
        if not csv_models:
            print("❌ 无法从CSV获取模型数据")
            return []
        
        # 转换为ModelInfo对象
        model_infos = []
        
        print(f"开始处理 {len(csv_models)} 个模型...")
        
        for i, csv_model in enumerate(csv_models, 1):
            try:
                print(f"\n进度: {i}/{len(csv_models)}")
                
                # 转换基本信息
                model_info = self.convert_csv_to_model_info(csv_model)
                
                # 使用爬虫获取详细信息
                if fetch_details:
                    model_info = self.get_model_detail_from_scraper(model_info)
                    
                    # 添加延迟避免请求过快
                    if i < len(csv_models):  # 最后一个不需要延迟
                        time.sleep(self.delay)
                
                model_infos.append(model_info)
                
            except Exception as e:
                print(f"❌ 处理模型失败: {e}")
                continue
        
        print(f"\n✅ 成功处理 {len(model_infos)} 个模型的信息")
        return model_infos


def test_csv_reader():
    """测试CSV读取器功能"""
    reader = CSVModelReader(delay=1.0)
    
    # 测试获取少量模型
    models = reader.crawl_models(max_models=5, fetch_details=True)
    
    for model in models:
        print(f"\nURL: {model.url}")
        print(f"项目名称: {model.project_name}")
        print(f"标签: {', '.join(model.tags)}")
        print(f"README长度: {len(model.readme)}")
        print(f"README预览: {model.readme[:200]}...")
        print("-" * 50)


if __name__ == "__main__":
    test_csv_reader()
