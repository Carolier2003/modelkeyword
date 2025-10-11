#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace 模型信息爬虫
支持爬取模型名称、标签列表和README内容
"""

import re
import asyncio
import json
from typing import Dict, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scrape_hf_model(url: str, token: Optional[str] = None) -> Dict[str, str]:
    """
    爬取 HuggingFace 模型信息
    
    Args:
        url: 模型页面URL
        token: 可选的认证token
    
    Returns:
        Dict包含以下字段:
        - url: 原始URL
        - name: 模型全称
        - tags: 标签列表(JSON字符串)
        - readme: README内容
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            # 加载页面，使用更宽松的等待条件
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # 设置认证token（如果提供）
            if token:
                await page.evaluate(f"""
                    localStorage.setItem('token', '{token}');
                    localStorage.setItem('auth_token', '{token}');
                    localStorage.setItem('access_token', '{token}');
                """)
                
                # 刷新页面以应用token
                await page.reload(wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
            
            # 等待页面完全加载
            await page.wait_for_timeout(5000)
            
            # 尝试直接获取README内容
            try:
                readme_md = await page.evaluate("""
                    () => {
                        // 尝试多个选择器
                        const selectors = [
                            'div.dp-editor-md-preview-container',
                            'div.gitCode-MdRender-container',
                            'div[class*=\"readme\"]',
                            'div[class*=\"markdown\"]',
                            '.repo-file-markdown-content'
                        ];
                        
                        for (const selector of selectors) {
                            const element = document.querySelector(selector);
                            if (element) {
                                const text = element.innerText || element.textContent || '';
                                if (text.length > 100) {  // 确保有足够的内容
                                    return text;
                                }
                            }
                        }
                        return '';
                    }
                """)
                # print(f"🔍 直接获取README，长度: {len(readme_md)}")
            except Exception as e:
                print(f"❌ 直接获取README失败: {e}")
                readme_md = ""
            
            # 获取页面内容用于解析其他信息
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 如果直接获取失败，使用BeautifulSoup作为备用
            if len(readme_md) == 0:
                # 尝试多种文本提取方法
                readme_div = soup.find("div", class_=re.compile(r"dp-editor-md-preview-container"))
                if readme_div:
                    readme_md = readme_div.get_text(strip=False)
                    if len(readme_md) == 0:
                        # 如果get_text为空，尝试获取所有文本节点
                        readme_md = ""
                        for text_node in readme_div.find_all(text=True):
                            readme_md += text_node
                    # print(f"🔍 BeautifulSoup找到README，长度: {len(readme_md)}")
                else:
                    # 备用选择器：使用更精确的选择器
                    readme_div = soup.find("div", class_=re.compile(r"gitCode-MdRender-container"))
                    if readme_div:
                        readme_md = readme_div.get_text(strip=False)
                        if len(readme_md) == 0:
                            readme_md = ""
                            for text_node in readme_div.find_all(text=True):
                                readme_md += text_node
                        # print(f"🔍 备用选择器找到README，长度: {len(readme_md)}")
                    else:
                        readme_md = ""
                        # print("❌ 未找到README div")

            # 1. 模型名称 ----------------------------------------------------------
            # 面包屑最后一节 <a><span class="linkTx font-bold ...">GLM-4.6</span></a>
            model_name_element = soup.select_one("div.breadcrumb p a span.linkTx")
            if model_name_element:
                model_name = model_name_element.get_text(strip=True)
            else:
                # 备用方案：从标题提取
                title = await page.title()
                model_match = re.search(r"GLM[-\w\.]*", title)
                model_name = model_match.group() if model_match else "Unknown"
            
            # 从URL提取组织名和仓库名
            url_parts = url.rstrip('/').split('/')
            if len(url_parts) >= 2:
                org_name = url_parts[-2]
                repo_name = url_parts[-1]
                full_name = f"{org_name}/{repo_name}"
            else:
                full_name = model_name

            # 2. 标签列表 ----------------------------------------------------------
            # 每个标签对应一个 <div class="topic-tag ..."> 下的 <span>
            tag_elements = soup.select("div.topic-tag span")
            if tag_elements:
                tags = [span.get_text(strip=True) for span in tag_elements]
            else:
                # 备用选择器
                tags = [elem.get_text(strip=True) for elem in soup.select(".tag, .label, .badge")]
            
            # 3. README Markdown 原文 ----------------------------------------------
            # GitCode 把 README 塞在一个 <div class="dp-editor-md-preview-container ...">
            readme_div = soup.find("div", class_=re.compile(r"dp-editor-md-preview-container"))
            if readme_div:
                # 尝试多种文本提取方法
                readme_md = readme_div.get_text(strip=False)
                if len(readme_md) == 0:
                    # 如果get_text为空，尝试获取所有文本节点
                    readme_md = ""
                    for text_node in readme_div.find_all(text=True):
                        readme_md += text_node
                print(f"🔍 找到README div，长度: {len(readme_md)}")
            else:
                # 备用选择器：使用更精确的选择器
                readme_div = soup.find("div", class_=re.compile(r"gitCode-MdRender-container"))
                if readme_div:
                    readme_md = readme_div.get_text(strip=False)
                    if len(readme_md) == 0:
                        readme_md = ""
                        for text_node in readme_div.find_all(text=True):
                            readme_md += text_node
                    print(f"🔍 备用选择器找到README，长度: {len(readme_md)}")
                else:
                    readme_md = ""
                    print("❌ 未找到README div")
            
            # 返回结果
            result = {
                "url": url,
                "name": full_name,
                "tags": json.dumps(tags, ensure_ascii=False),
                "readme": readme_md
            }
            
            return result

        except Exception as e:
            # 返回错误信息
            return {
                "url": url,
                "name": "Error",
                "tags": json.dumps([]),
                "readme": f"Error: {str(e)}"
            }
        
        finally:
            await browser.close()

def scrape_hf_model_sync(url: str, token: Optional[str] = None) -> Dict[str, str]:
    """
    同步版本的爬虫函数
    
    Args:
        url: 模型页面URL
        token: 可选的认证token
    
    Returns:
        Dict包含模型信息
    """
    return asyncio.run(scrape_hf_model(url, token))

async def main():
    """测试函数"""
    url = "https://ai.gitcode.com/hf_mirrors/zai-org/GLM-4.6"
    token = "eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI2NzMwNTkzOTY4ZjYwYzcyYTZkNjY0YjAiLCJzdWIiOiJDYXJvbGllciIsImF1dGhvcml0aWVzIjpbXSwib2JqZWN0SWQiOiI2OGU3NjAwMmEzYzAyMjFmZTc5NTQ0NzgiLCJpYXQiOjE3NTk5OTM4NTgsImV4cCI6MTc2MDA4MDI1OH0.Gx_-yrMRyUhqHDg7TjDQkAY5QK2z-l2ZHHNdQD9K0DgKShp0qrjHLpNlQEfjZJMokQm5-gzMsbvXZwHKB2sdeQ"
    
    result = await scrape_hf_model(url, token)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
