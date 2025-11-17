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
            
            # 检查是否跳转到了/model-inference页面，如果是则点击"模型介绍"按钮返回主页面
            current_url = page.url
            if '/model-inference' in current_url:
                print(f"⚠️  检测到跳转到/model-inference页面: {current_url}")
                print("   正在点击'模型介绍'按钮返回主页面...")
                
                try:
                    # 等待页面完全加载，"模型介绍"按钮出现
                    await page.wait_for_timeout(3000)
                    
                    # 使用Playwright的locator API查找并点击"模型介绍"按钮
                    intro_button_clicked = False
                    
                    try:
                        # 方法1: 使用get_by_text查找包含"模型介绍"文本的元素
                        try:
                            intro_button = page.get_by_text("模型介绍", exact=False)
                            if await intro_button.count() > 0:
                                # 找到父div并点击
                                await intro_button.first.click(timeout=5000)
                                intro_button_clicked = True
                                print("   ✅ 成功点击'模型介绍'按钮（方法1：get_by_text）")
                        except Exception as e1:
                            # 方法2: 使用JavaScript查找并点击
                            try:
                                clicked = await page.evaluate("""
                                    () => {
                                        // 查找包含"模型介绍"文本的span元素
                                        const spans = Array.from(document.querySelectorAll('span'));
                                        const introSpan = spans.find(span => {
                                            const text = span.textContent || span.innerText || '';
                                            return text.trim() === '模型介绍' || text.includes('模型介绍');
                                        });
                                        
                                        if (introSpan) {
                                            // 找到可点击的父元素（通常是包含flex class的div）
                                            let clickable = introSpan.closest('div');
                                            // 向上查找，直到找到包含flex的div
                                            while (clickable && !clickable.classList.contains('flex')) {
                                                clickable = clickable.parentElement;
                                            }
                                            
                                            if (clickable) {
                                                clickable.click();
                                                return true;
                                            }
                                        }
                                        
                                        // 通过class查找包含flex gap-2的div
                                        const flexDivs = Array.from(document.querySelectorAll('div.flex.gap-2.items-center'));
                                        for (const div of flexDivs) {
                                            const span = div.querySelector('span');
                                            if (span && (span.textContent || span.innerText || '').includes('模型介绍')) {
                                                div.click();
                                                return true;
                                            }
                                        }
                                        
                                        // 通过SVG的xlink:href查找
                                        const allUses = Array.from(document.querySelectorAll('use'));
                                        const svgUse = allUses.find(use => {
                                            const href = use.getAttribute('xlink:href') || use.getAttribute('href');
                                            return href === '#gt-plane-models';
                                        });
                                        if (svgUse) {
                                            const svg = svgUse.closest('svg');
                                            if (svg) {
                                                const parentDiv = svg.closest('div');
                                                if (parentDiv) {
                                                    parentDiv.click();
                                                    return true;
                                                }
                                            }
                                        }
                                        
                                        return false;
                                    }
                                """)
                                
                                if clicked:
                                    intro_button_clicked = True
                                    print("   ✅ 成功点击'模型介绍'按钮（方法2：JavaScript）")
                                else:
                                    print("   ⚠️  未找到'模型介绍'按钮")
                            except Exception as e2:
                                print(f"   ⚠️  JavaScript方法失败: {e2}")
                    except Exception as e:
                        print(f"   ❌ 点击'模型介绍'按钮失败: {e}")
                    
                    if intro_button_clicked:
                        # 等待页面跳转回主页面
                        await page.wait_for_timeout(2000)
                        
                        # 等待URL变化（去掉/model-inference）
                        try:
                            await page.wait_for_function(
                                "() => !window.location.href.includes('/model-inference')",
                                timeout=10000
                            )
                            print("   ✅ 已跳转回主页面（等待URL变化）")
                        except Exception:
                            # 如果等待超时，检查当前URL
                            current_url_after = page.url
                            if '/model-inference' not in current_url_after:
                                print("   ✅ 已跳转回主页面（URL检查）")
                            else:
                                print(f"   ⚠️  仍在/model-inference页面: {current_url_after}")
                        
                        # 等待页面完全加载
                        await page.wait_for_timeout(5000)
                    else:
                        print("   ⚠️  未能点击'模型介绍'按钮，尝试直接访问主页面URL...")
                        # 如果点击失败，尝试直接访问主页面URL
                        base_url = url.rstrip('/')
                        if '/model-inference' in base_url:
                            base_url = base_url.split('/model-inference')[0]
                        try:
                            await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
                            await page.wait_for_timeout(5000)
                            
                            # 检查是否又跳转回了/model-inference
                            current_url_check = page.url
                            if '/model-inference' in current_url_check:
                                print(f"   ⚠️  直接访问后仍跳转到/model-inference，再次尝试点击按钮...")
                                # 再次尝试点击按钮
                                try:
                                    intro_button = page.get_by_text("模型介绍", exact=False)
                                    if await intro_button.count() > 0:
                                        await intro_button.first.click(timeout=5000)
                                        await page.wait_for_timeout(3000)
                                        print("   ✅ 再次点击'模型介绍'按钮成功")
                                except Exception:
                                    pass
                            else:
                                print(f"   ✅ 直接访问主页面成功: {base_url}")
                        except Exception as e:
                            print(f"   ⚠️  直接访问主页面失败: {e}")
                except Exception as e:
                    print(f"   ⚠️  处理/model-inference页面时出错: {e}")
            
            # 再次等待页面完全加载（确保README内容已渲染）
            await page.wait_for_timeout(5000)
            
            # 确保当前不在/model-inference页面
            final_url = page.url
            if '/model-inference' in final_url:
                print(f"   ⚠️  最终仍在/model-inference页面，README可能无法获取")
            
            # 尝试直接获取README内容
            try:
                readme_md = await page.evaluate("""
                    () => {
                        // 尝试多个选择器，按优先级排序
                        const selectors = [
                            'div.markdown-card',
                            'div[class*="markdown-card"]',
                            'div.dp-editor-md-preview-container',
                            'div.gitCode-MdRender-container',
                            'div[class*="readme"]',
                            'div[class*="markdown"]',
                            '.repo-file-markdown-content',
                            'article',
                            'main div[class*="content"]'
                        ];
                        
                        for (const selector of selectors) {
                            const element = document.querySelector(selector);
                            if (element) {
                                const text = element.innerText || element.textContent || '';
                                if (text.length > 50) {  // 降低长度要求
                                    return text;
                                }
                            }
                        }
                        
                        // 如果上述选择器都失败，尝试查找所有包含大量文本的div
                        const allDivs = Array.from(document.querySelectorAll('div'));
                        for (const div of allDivs) {
                            const text = div.innerText || div.textContent || '';
                            // 如果div包含大量文本（可能是README），且不是导航栏等
                            if (text.length > 200 && 
                                !div.classList.contains('header') && 
                                !div.classList.contains('nav') &&
                                !div.classList.contains('footer')) {
                                return text;
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
                # 尝试多种文本提取方法，按优先级排序
                selectors_to_try = [
                    r"markdown-card",
                    r"dp-editor-md-preview-container", 
                    r"gitCode-MdRender-container"
                ]
                
                for selector_pattern in selectors_to_try:
                    readme_div = soup.find("div", class_=re.compile(selector_pattern))
                    if readme_div:
                        readme_md = readme_div.get_text(strip=False)
                        if len(readme_md) == 0:
                            # 如果get_text为空，尝试获取所有文本节点
                            readme_md = ""
                            for text_node in readme_div.find_all(text=True):
                                readme_md += text_node
                        if len(readme_md) > 50:  # 确保有足够内容
                            # print(f"🔍 BeautifulSoup找到README，长度: {len(readme_md)}")
                            break
                        else:
                            readme_md = ""  # 重置，继续尝试下一个选择器
                
                if len(readme_md) == 0:
                    # print("❌ 未找到README div")
                    pass

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
            # README内容已经在上面提取过了，这里不需要重复提取
            
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
