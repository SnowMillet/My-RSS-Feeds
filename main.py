import json
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import dateparser
from datetime import datetime
import pytz
import os

# 1. 读取配置文件
with open('sites.json', 'r', encoding='utf-8') as f:
    sites = json.load(f)

# 创建输出目录
if not os.path.exists('rss_output'):
    os.makedirs('rss_output')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

# 2. 遍历所有配置的网站
for site in sites:
    print(f"正在处理: {site['title']}")
    
    # 初始化 RSS 生成器
    fg = FeedGenerator()
    fg.id(site['url'])
    fg.title(site['title'])
    fg.description(site.get('description', '自动生成的RSS订阅源'))
    fg.link(href=site['url'], rel='alternate')
    fg.language('zh-cn')

    try:
        # 获取网页内容
        response = requests.get(site['url'], headers=headers, timeout=15)
        response.encoding = response.apparent_encoding # 解决潜在乱码
        soup = BeautifulSoup(response.text, 'html.parser')

        # 获取外层列表
        items = soup.select(site['selectors']['item'])
        
        for element in items[:20]: # 限制只抓取前20条，避免RSS过大
            fe = fg.add_entry()
            
            # 提取标题
            title_el = element.select_one(site['selectors']['title'])
            title_text = title_el.get_text(strip=True) if title_el else "无标题"
            
            # 提取日期
            date_el = element.select_one(site['selectors']['date'])
            date_text = date_el.get_text(strip=True) if date_el else ""
            
            # 尝试智能解析日期，如果解析失败则用当前时间
            parsed_date = dateparser.parse(date_text) if date_text else None
            if parsed_date:
                # 确保有本地时区信息
                if parsed_date.tzinfo is None:
                    parsed_date = pytz.utc.localize(parsed_date)
                fe.pubDate(parsed_date)
            else:
                fe.pubDate(datetime.now(pytz.utc))
            
            # 提取链接 (如果没有独立链接，就用原网页的链接)
            link_el = element.select_one(site['selectors']['link'])
            if link_el and link_el.has_attr('href'):
                # 处理相对路径
                href = link_el['href']
                if href.startswith('/'):
                    href = site['url'].split('/', 3)[0] + '//' + site['url'].split('/')[2] + href
                fe.link(href=href)
                fe.id(href)
            else:
                fe.link(href=site['url'])
                # 为了防止多条没有链接的内容ID冲突，用 标题+原网址 做唯一ID
                fe.id(site['url'] + "#" + title_text)

            # 你的需求是只需要标题和时间，所以这里把原网页的日期写在摘要里备用
            fe.title(title_text)
            fe.description(f"发布时间: {date_text}")

        # 保存为 XML 文件
        output_file = f"rss_output/{site['id']}.xml"
        fg.rss_file(output_file)
        print(f"成功生成: {output_file}")

    except Exception as e:
        print(f"处理 {site['title']} 时出错: {e}")

print("所有任务执行完毕！")