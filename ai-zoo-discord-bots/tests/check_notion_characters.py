"""
Notionから取得したキャラクター設定を確認するためのスクリプト。
標準出力に詳細情報を出力します。
"""
import os
import sys
import asyncio
import logging
import json
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from services.notion_service import NotionService
from utils.config_loader import load_env_vars

# ロギングの設定（標準出力に詳細情報を表示）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("notion_check")
logger.setLevel(logging.DEBUG)

async def check_character_settings():
    """Notionから取得したキャラクター設定を標準出力に表示します"""
    
    # 環境変数を読み込み
    env_path = project_root / 'config' / '.env'
    if env_path.exists():
        load_env_vars(str(env_path))
        logger.info(f"環境変数を読み込みました: {env_path}")
    else:
        logger.warning(f"環境変数ファイルが見つかりません: {env_path}")

    # APIキーが設定されているか確認
    notion_api_key = os.environ.get('NOTION_API_KEY')
    notion_db_id = os.environ.get('NOTION_DATABASE_ID')
    
    if not notion_api_key:
        logger.error("NOTION_API_KEYが設定されていません")
        return
    if not notion_db_id:
        logger.error("NOTION_DATABASE_IDが設定されていません")
        return
    
    logger.info(f"Notion API Key: {notion_api_key[:5]}...{notion_api_key[-5:]}")
    logger.info(f"Notion Database ID: {notion_db_id}")
    
    # NotionServiceのインスタンスを作成
    service = NotionService()
    
    # キャラクターキャッシュを更新
    logger.info("キャラクターキャッシュを更新しています...")
    await service.refresh_character_cache()
    
    # キャッシュに保存されたキャラクター一覧を表示
    logger.info("==== キャッシュに保存されたキャラクター一覧 ====")
    for key, character in service.character_cache.items():
        logger.info(f"キャッシュキー: {key}")
    
    # 特定のキャラクター名を指定して詳細情報を表示
    character_names = ["GPT-4o-animal", "claude-animal", "AI Zoo Bot 1", "AI Zoo Bot 2"]
    
    for name in character_names:
        logger.info(f"\n=== キャラクター '{name}' の詳細情報の検索 ===")
        character = await service.get_character(name)
        
        if character:
            logger.info(f"キャラクター '{name}' が見つかりました")
            logger.info("属性:")
            
            # 属性を整形して表示
            for key, value in character.items():
                if isinstance(value, list):
                    value_str = ", ".join(value)
                else:
                    value_str = str(value)
                logger.info(f"  - {key}: {value_str}")
            
            # システムプロンプトを生成して表示
            prompt = service.format_character_prompt(character)
            logger.info("\nシステムプロンプト:")
            logger.info(f"{prompt}")
        else:
            logger.warning(f"キャラクター '{name}' は見つかりませんでした")

if __name__ == "__main__":
    asyncio.run(check_character_settings())