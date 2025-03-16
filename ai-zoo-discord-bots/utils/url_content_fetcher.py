"""
Utility for fetching and processing URL content.
"""
import re
import logging
import asyncio
import aiohttp
from typing import List, Tuple, Optional

# BeautifulSoup4が利用可能かどうかを確認
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logging.warning("BeautifulSoup4 is not available. HTML parsing will be limited.")

# Playwrightが利用可能かどうかを確認
try:
    import playwright.async_api
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright is not available. Dynamic content rendering will not work.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URLを検出する正規表現パターン
URL_PATTERN = re.compile(r'https?://\S+')

# JavaScriptを使用する可能性の高いドメインのリスト
DYNAMIC_CONTENT_DOMAINS = [
    'notion.so',
    'notion.site',
    'twitter.com',
    'x.com',
    'facebook.com',
    'instagram.com',
    'linkedin.com',
    'react',  # 部分一致で判定
    'angular',
    'vue',
    'spa'
]

def is_dynamic_content_url(url: str) -> bool:
    """
    URLが動的コンテンツを持つ可能性が高いかどうかを判定する
    
    Args:
        url: 評価するURL
        
    Returns:
        動的コンテンツの可能性が高い場合はTrue
    """
    return any(domain in url.lower() for domain in DYNAMIC_CONTENT_DOMAINS)

def extract_urls(content: str) -> List[str]:
    """
    メッセージからURLを抽出する
    
    Args:
        content: メッセージ内容
        
    Returns:
        抽出されたURLのリスト
    """
    return URL_PATTERN.findall(content)

def extract_text_from_html(html: str) -> str:
    """
    HTMLからテキストを抽出する
    
    Args:
        html: HTMLコンテンツ
        
    Returns:
        抽出されたテキスト
    """
    if BEAUTIFULSOUP_AVAILABLE:
        # BeautifulSoup4が利用可能な場合は、それを使用
        soup = BeautifulSoup(html, 'html.parser')
        
        # スクリプトとスタイル要素を削除
        for script in soup(["script", "style"]):
            script.extract()
        
        # テキストを取得
        text = soup.get_text()
        
        # 余分な空白を削除
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    else:
        # BeautifulSoup4が利用できない場合は、簡易的なテキスト抽出を行う
        # タグを除去する簡易的な方法
        text = re.sub(r'<[^>]+>', ' ', html)
        # 余分な空白を削除
        text = re.sub(r'\s+', ' ', text).strip()
        # 長すぎる場合は切り詰める
        if len(text) > 1000:
            text = text[:1000] + "..."
        return text

async def fetch_with_playwright(url: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    Playwrightを使用して動的コンテンツをレンダリングし、内容を取得する
    
    Args:
        url: 取得するURL
        timeout: タイムアウト時間（秒）
        
    Returns:
        (タイトル, 取得したコンテンツのHTML)のタプル
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None, "[Playwright is not installed. Cannot render dynamic content.]"
        
    try:
        # PlaywrightでChromiumを起動
        async with playwright.async_api.async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # タイムアウト設定
            page.set_default_timeout(timeout * 1000)
            
            # ページ読み込み
            await page.goto(url)
            
            # JavaScriptが実行されるのを待つ
            await asyncio.sleep(2)  # 最低2秒待機
            
            # ページが完全に読み込まれるのを待つ
            await page.wait_for_load_state('networkidle')
            
            # タイトルとコンテンツを取得
            title = await page.title()
            content = await page.content()
            
            # ブラウザを閉じる
            await browser.close()
            
            return title, content
    except Exception as e:
        logger.error(f"Playwright error fetching {url}: {str(e)}")
        return None, f"[動的コンテンツ取得エラー: {str(e)}]"

async def fetch_url_content(url: str, max_length: int = 1000, timeout: int = 5) -> Tuple[str, Optional[str]]:
    """
    URLからコンテンツを取得し、要約または切り詰めたテキストを返す
    
    Args:
        url: 取得するURL
        max_length: 最大文字数
        timeout: リクエストのタイムアウト時間（秒）
        
    Returns:
        (タイトル, 取得したコンテンツのテキスト（切り詰め済み）)のタプル
        エラーの場合はタイトルはNone
    """
    # 動的コンテンツの可能性が高いURLの場合はPlaywrightを使用
    if is_dynamic_content_url(url) and PLAYWRIGHT_AVAILABLE:
        try:
            logger.info(f"Using Playwright for dynamic content URL: {url}")
            title, html = await fetch_with_playwright(url, timeout=timeout)
            if html and not html.startswith('['):  # エラーでない場合
                text = extract_text_from_html(html)
                # テキストを切り詰める
                if len(text) > max_length:
                    text = text[:max_length] + "..."
                return title or "No title", text
            elif html:  # エラーメッセージの場合
                return None, html
        except Exception as e:
            logger.error(f"Error with Playwright for URL {url}: {str(e)}")
            # 失敗した場合は通常のリクエストにフォールバック
    
    # 通常のHTTPリクエストでコンテンツを取得
    try:
        # タイムアウト処理を強化
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        try:
                            # HTMLコンテンツの場合
                            if 'text/html' in content_type:
                                html = await response.text()
                                
                                # BeautifulSoup4が利用可能な場合のみBeautifulSoupを使用
                                if BEAUTIFULSOUP_AVAILABLE:
                                    soup = BeautifulSoup(html, 'html.parser')
                                    
                                    # タイトルを取得
                                    title_tag = soup.find('title')
                                    title = title_tag.get_text() if title_tag else "No title"
                                    
                                    # テキストを抽出（extract_text_from_html関数を使用）
                                    text = extract_text_from_html(html)
                                else:
                                    # BeautifulSoup4が利用できない場合は、簡易的なタイトル抽出
                                    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                                    title = title_match.group(1).strip() if title_match else "No title"
                                    
                                    # 簡易的なテキスト抽出（extract_text_from_html関数を使用）
                                    text = extract_text_from_html(html)
                                
                            # プレーンテキストの場合
                            elif 'text/plain' in content_type:
                                text = await response.text()
                                title = url.split('/')[-1] or "Text document"
                                
                            # JSONの場合
                            elif 'application/json' in content_type:
                                json_text = await response.text()
                                title = url.split('/')[-1] or "JSON document"
                                text = f"JSON content: {json_text}"
                                
                            # その他のコンテンツタイプ
                            else:
                                title = url.split('/')[-1] or "Unknown document"
                                text = f"[リンク先のコンテンツタイプ: {content_type}]"
                            
                            # テキストを切り詰める
                            if len(text) > max_length:
                                text = text[:max_length] + "..."
                                
                            return title, text
                        except Exception as content_error:
                            logger.error(f"Error processing content from URL {url}: {str(content_error)}")
                            return None, f"[コンテンツ処理エラー: {str(content_error)}]"
                    else:
                        return None, f"[リンク先のステータスコード: {response.status}]"
            except asyncio.TimeoutError:
                logger.warning(f"Timeout while fetching URL {url}")
                return None, f"[リンク取得タイムアウト: URLの読み込みに時間がかかりすぎました]"
            except aiohttp.ClientError as client_error:
                logger.error(f"Client error while fetching URL {url}: {str(client_error)}")
                return None, f"[リンク取得エラー: 接続に問題が発生しました]"
    except Exception as e:
        logger.error(f"Unexpected error fetching URL {url}: {str(e)}", exc_info=True)
        return None, f"[リンク取得エラー: {str(e)}]"

async def process_message_urls(message_content: str, max_urls: int = 3, max_length_per_url: int = 1000, timeout: int = 5) -> Optional[str]:
    """
    メッセージ内のURLを処理し、コンテンツを取得する
    
    Args:
        message_content: メッセージ内容
        max_urls: 処理する最大URL数
        max_length_per_url: URL毎の最大文字数
        
    Returns:
        取得したURLコンテンツの文字列、またはNone（URLが見つからない場合）
    """
    # メッセージからURLを抽出
    urls = extract_urls(message_content)
    
    if not urls:
        return None
    
    # 最大URL数に制限
    urls = urls[:max_urls]
    
    # 各URLからコンテンツを取得
    url_contents = []
    for url in urls:
        try:
            title, content = await fetch_url_content(url, max_length_per_url, timeout)
            if title:
                url_contents.append(f"URL: {url}\nタイトル: {title}\nコンテンツ:\n{content}")
            else:
                url_contents.append(f"URL: {url}\nコンテンツ:\n{content}")
        except Exception as e:
            logger.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
            url_contents.append(f"URL: {url}\n[処理エラー: URLの取得中に問題が発生しました]")
    
    # 結果を結合
    if url_contents:
        return "\n\n".join(url_contents)
    
    return None
