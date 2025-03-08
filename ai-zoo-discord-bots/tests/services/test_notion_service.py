"""
Tests for the Notion service.
"""
import os
import json
import time
from unittest import mock
import pytest
from typing import Dict, Any
import sys
from pathlib import Path

from services.notion_service import NotionService
from utils.config_loader import load_env_vars, get_env

# テスト開始時に .env ファイルから環境変数を読み込む
def load_test_env_vars():
    """テスト用の環境変数を設定する"""
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / "config" / ".env"
    
    if env_file.exists():
        # .envファイルがある場合はそこから読み込む
        print(f"Loading environment variables from {env_file}")
        load_env_vars(str(env_file))
    else:
        print(f"Warning: .env file not found at {env_file}")


# テスト実行前に環境変数を読み込む
load_test_env_vars()


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    
    # 実際の環境変数が設定されているかチェック
    notion_api_key = os.environ.get('NOTION_API_KEY')
    notion_db_id = os.environ.get('NOTION_DATABASE_ID')
    
    # 環境変数が設定されていない場合はモック値を使用
    if not notion_api_key:
        notion_api_key = 'test-api-key'
    if not notion_db_id:
        notion_db_id = 'test-database-id'
        
    with mock.patch.dict(os.environ, {
        'NOTION_API_KEY': notion_api_key,
        'NOTION_DATABASE_ID': notion_db_id
    }):
        yield


@pytest.fixture
def mock_config_path():
    """Mock the config path function."""
    with mock.patch('services.notion_service.get_config_path') as mock_get_path:
        mock_get_path.return_value = 'mock/path/notion_config.json'
        yield mock_get_path


@pytest.fixture
def mock_config():
    """Mock the config loading function."""
    config = {
        "database_id": "test-database-id",
        "character_properties": {
            "name": "Name",
            "personality": "Personality",
            "speaking_style": "Speaking Style",
            "language": "Language",
            "restrictions": "Restrictions", 
            "background": "Background",
            "interests": "Interests",
            "model": "Model"
        },
        "refresh_interval_minutes": 60,
        "cache_expiry_hours": 24
    }
    
    with mock.patch('services.notion_service.load_json_config') as mock_load:
        mock_load.return_value = config
        yield config


@pytest.fixture
def mock_notion_response():
    """Mock response from Notion API."""
    return {
        "results": [
            {
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "TestCharacter"}]
                    },
                    "Personality": {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "Friendly and helpful"}]
                    },
                    "Speaking Style": {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "Casual and clear"}]
                    },
                    "Language": {
                        "type": "select",
                        "select": {"name": "English"}
                    },
                    "Interests": {
                        "type": "multi_select",
                        "multi_select": [
                            {"name": "AI"},
                            {"name": "Programming"}
                        ]
                    },
                    "Background": {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "AI assistant background"}]
                    },
                    "Restrictions": {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "None"}]
                    }
                }
            }
        ]
    }


class MockResponse:
    """Mock aiohttp response."""
    
    def __init__(self, data, status=200):
        self.data = data
        self.status = status
    
    async def json(self):
        return self.data
    
    async def text(self):
        return json.dumps(self.data)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockClientSession:
    """Mock aiohttp ClientSession."""
    
    def __init__(self, response_data, status=200):
        self.response_data = response_data
        self.status = status
        self.post_calls = []
    
    def post(self, url, headers=None, json=None):
        """非同期ではないpostメソッド - コンテキストマネージャーを返す"""
        self.post_calls.append({"url": url, "headers": headers, "json": json})
        return MockResponse(self.response_data, self.status)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# 以下はモックを使用したテスト
@pytest.mark.asyncio
async def test_init_notion_service(mock_env, mock_config):
    """Test NotionService initialization."""
    service = NotionService()
    
    # 実際の環境変数が設定されている場合はスキップ
    if os.environ.get('NOTION_API_KEY') != 'test-api-key':
        assert service.api_key is not None
    else:
        assert service.api_key == 'test-api-key'
        
    assert 'character_properties' in service.config
    assert service.character_cache == {}


@pytest.mark.asyncio
async def test_get_character_no_cache_refresh(mock_env, mock_config):
    """Test getting character without needing cache refresh."""
    service = NotionService()
    
    # Set up cache with a test character
    service.character_cache = {
        'testcharacter': {
            'name': 'TestCharacter',
            'personality': 'Test personality'
        }
    }
    service.last_refresh_time = time.time()  # Set refresh time to now
    
    character = await service.get_character('TestCharacter')
    
    assert character is not None
    assert character['name'] == 'TestCharacter'


@pytest.mark.asyncio
async def test_get_character_with_cache_refresh(mock_env, mock_config, mock_notion_response):
    """Test getting character with cache refresh."""
    service = NotionService()
    
    # Set last refresh time to force a cache refresh
    service.last_refresh_time = time.time() - 7200  # 2 hours ago
    
    # Mock the _query_notion_database method
    with mock.patch.object(
        service, '_query_notion_database', 
        return_value=[{
            'name': 'TestCharacter',
            'personality': 'Friendly and helpful'
        }]
    ):
        character = await service.get_character('TestCharacter')
    
    assert character is not None
    assert character['name'] == 'TestCharacter'
    assert character['personality'] == 'Friendly and helpful'


@pytest.mark.asyncio
async def test_refresh_character_cache(mock_env, mock_config, mock_notion_response):
    """Test refreshing the character cache."""
    service = NotionService()
    
    # Mock the _query_notion_database method
    with mock.patch.object(
        service, '_query_notion_database', 
        return_value=[{
            'name': 'TestCharacter',
            'personality': 'Friendly and helpful'
        }]
    ):
        await service.refresh_character_cache()
    
    assert 'testcharacter' in service.character_cache
    assert service.character_cache['testcharacter']['name'] == 'TestCharacter'
    assert service.last_refresh_time > 0


@pytest.mark.asyncio
async def test_query_notion_database(mock_env, mock_config, mock_notion_response):
    """Test querying the Notion database."""
    service = NotionService()
    
    # Mock aiohttp.ClientSession
    mock_session = MockClientSession(mock_notion_response)
    
    with mock.patch('aiohttp.ClientSession', return_value=mock_session):
        characters = await service._query_notion_database()
    
    assert len(characters) == 1
    assert characters[0]['name'] == 'TestCharacter'
    assert characters[0]['personality'] == 'Friendly and helpful'
    assert characters[0]['interests'] == ['AI', 'Programming']


def test_parse_notion_page(mock_env, mock_config):
    """Test parsing a Notion page."""
    service = NotionService()
    
    page = {
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "TestCharacter"}]
            },
            "Personality": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "Friendly and helpful"}]
            },
            "Language": {
                "type": "select",
                "select": {"name": "English"}
            }
        }
    }
    
    result = service._parse_notion_page(page)
    
    assert result['name'] == 'TestCharacter'
    assert result['personality'] == 'Friendly and helpful'
    assert result['language'] == 'English'


def test_extract_property_value(mock_env, mock_config):
    """Test extracting property values from different Notion property types."""
    service = NotionService()
    
    # Title property
    title_prop = {
        "type": "title",
        "title": [{"plain_text": "TestCharacter"}]
    }
    assert service._extract_property_value(title_prop) == "TestCharacter"
    
    # Rich text property
    text_prop = {
        "type": "rich_text",
        "rich_text": [{"plain_text": "Test description"}]
    }
    assert service._extract_property_value(text_prop) == "Test description"
    
    # Select property
    select_prop = {
        "type": "select",
        "select": {"name": "Option1"}
    }
    assert service._extract_property_value(select_prop) == "Option1"
    
    # Multi-select property
    multi_select_prop = {
        "type": "multi_select",
        "multi_select": [
            {"name": "Tag1"},
            {"name": "Tag2"}
        ]
    }
    assert service._extract_property_value(multi_select_prop) == ["Tag1", "Tag2"]


def test_format_character_prompt(mock_env, mock_config):
    """Test formatting character data into a prompt."""
    service = NotionService()
    
    character = {
        "name": "TestCharacter",
        "personality": "Friendly and helpful",
        "speaking_style": "Casual and clear",
        "language": "English",
        "background": "AI assistant background",
        "interests": ["AI", "Programming"],
        "restrictions": "None"
    }
    
    prompt = service.format_character_prompt(character)
    
    assert "You are TestCharacter." in prompt
    assert "Personality: Friendly and helpful" in prompt
    assert "Speaking style: Casual and clear" in prompt
    assert "You primarily communicate in English." in prompt
    assert "Background: AI assistant background" in prompt
    assert "Your interests include: AI, Programming" in prompt
    assert "Restrictions: None" in prompt
    assert "You are participating in a Discord chat" in prompt


# 新しいテスト: ボット名からキャラクターを取得するテスト
@pytest.mark.asyncio
async def test_get_character_by_bot_name(mock_env, mock_config):
    """Test retrieving a character by bot name."""
    service = NotionService()
    
    # Set up character cache with multiple test characters
    service.character_cache = {
        'aizoobot1': {
            'name': 'AI Zoo Bot 1',
            'personality': 'Friendly and outgoing',
            'model': 'gpt-4'
        },
        'aizoobot2': {
            'name': 'AI Zoo Bot 2',
            'personality': 'Curious and analytical',
            'model': 'claude-2'
        },
        'aizoobot3': {
            'name': 'AI Zoo Bot 3',
            'personality': 'Witty and sarcastic',
            'model': 'gpt-3.5-turbo'
        }
    }
    service.last_refresh_time = time.time()  # Set refresh time to now
    
    # Test retrieving existing characters
    character1 = await service.get_character('AI Zoo Bot 1')
    assert character1 is not None
    assert character1['name'] == 'AI Zoo Bot 1'
    assert character1['personality'] == 'Friendly and outgoing'
    assert character1['model'] == 'gpt-4'
    
    character2 = await service.get_character('AI Zoo Bot 2')
    assert character2 is not None
    assert character2['name'] == 'AI Zoo Bot 2'
    assert character2['model'] == 'claude-2'
    
    # Test case insensitivity
    character3 = await service.get_character('ai zoo bot 3')
    assert character3 is not None
    assert character3['name'] == 'AI Zoo Bot 3'
    assert character3['personality'] == 'Witty and sarcastic'
    
    # Test non-existent character
    character4 = await service.get_character('AI Zoo Bot 4')
    assert character4 is None


@pytest.mark.asyncio
async def test_get_character_with_spaces_and_special_format(mock_env, mock_config):
    """Test retrieving a character using various name formats."""
    service = NotionService()
    
    # Set up cache with characters that have spaces and special formatting
    test_characters = [
        {
            'name': 'Professor Einstein',
            'personality': 'Brilliant and eccentric',
            'model': 'gpt-4'
        },
        {
            'name': 'Marie Curie',
            'personality': 'Determined and meticulous',
            'model': 'claude-2'
        }
    ]
    
    # Manually populate cache with various formats
    service.character_cache = {}
    for character in test_characters:
        name = character['name']
        key = name.lower()
        transformed_key = key.replace(' ', '')
        service.character_cache[key] = character
        service.character_cache[transformed_key] = character
    
    service.last_refresh_time = time.time()
    
    # Test retrieving by exact name
    char1 = await service.get_character('Professor Einstein')
    assert char1 is not None
    assert char1['name'] == 'Professor Einstein'
    
    # Test retrieving by lowercase name
    char2 = await service.get_character('professor einstein')
    assert char2 is not None
    assert char2['name'] == 'Professor Einstein'
    
    # Test retrieving by name without spaces
    char3 = await service.get_character('professoreinstein')
    assert char3 is not None
    assert char3['name'] == 'Professor Einstein'
    
    # Same tests for second character
    char4 = await service.get_character('Marie Curie')
    assert char4 is not None
    assert char4['model'] == 'claude-2'
    
    char5 = await service.get_character('mariecurie')
    assert char5 is not None
    assert char5['personality'] == 'Determined and meticulous'


@pytest.mark.asyncio
async def test_character_cache_with_transformed_keys(mock_env, mock_config):
    """Test that the character cache is properly populated with transformed keys."""
    service = NotionService()
    
    # Mock the query function to return test characters
    test_characters = [
        {
            'name': 'AI Zoo Bot 1',
            'personality': 'Friendly',
            'model': 'gpt-4'
        },
        {
            'name': 'Dr. Watson',
            'personality': 'Logical',
            'model': 'claude-2'
        }
    ]
    
    with mock.patch.object(service, '_query_notion_database', return_value=test_characters):
        await service.refresh_character_cache()
    
    # Check that cache contains both original and transformed keys
    assert 'ai zoo bot 1' in service.character_cache
    assert 'aizoobot1' in service.character_cache
    assert 'dr. watson' in service.character_cache
    assert 'dr.watson' in service.character_cache
    
    # Verify the character data is correctly mapped
    assert service.character_cache['ai zoo bot 1']['name'] == 'AI Zoo Bot 1'
    assert service.character_cache['aizoobot1']['name'] == 'AI Zoo Bot 1'
    assert service.character_cache['dr. watson']['model'] == 'claude-2'
    assert service.character_cache['dr.watson']['model'] == 'claude-2'


# =====================================================
# 以下は実際のNotion APIに接続するテスト
# =====================================================

@pytest.fixture
def real_notion_service():
    """
    実際のNotionサービスを返すフィクスチャ。
    環境変数に実際のAPI KEYとデータベースIDが設定されている必要があります。
    """
    # 環境変数が設定されているか確認
    skip_message = None
    if 'NOTION_API_KEY' not in os.environ or not os.environ['NOTION_API_KEY']:
        skip_message = "環境変数NOTION_API_KEYが設定されていないためスキップします"
    elif 'NOTION_DATABASE_ID' not in os.environ or not os.environ['NOTION_DATABASE_ID']:
        skip_message = "環境変数NOTION_DATABASE_IDが設定されていないためスキップします"
    
    if skip_message:
        pytest.skip(skip_message)
    
    print(f"Using Notion API with key: {os.environ['NOTION_API_KEY'][:5]}... and database ID: {os.environ['NOTION_DATABASE_ID'][:5]}...")
    
    # 実際のNotionServiceインスタンスを返す
    return NotionService()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_notion_connection(real_notion_service):
    """実際のNotion APIへの接続をテストします。"""
    # データベースからキャラクターを取得
    characters = await real_notion_service._query_notion_database()
    
    # 少なくとも1つのキャラクターが取得できることを確認
    assert len(characters) > 0
    
    # 各キャラクターが必要なプロパティを持っていることを確認
    for character in characters:
        assert 'name' in character
        # 名前が空でないことを確認
        assert character['name'].strip()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_character_cache_refresh(real_notion_service):
    """実際のNotion APIを使用してキャラクターキャッシュを更新するテスト。"""
    # キャッシュを更新
    await real_notion_service.refresh_character_cache()
    
    # キャッシュが更新されたことを確認
    assert real_notion_service.last_refresh_time > 0
    assert len(real_notion_service.character_cache) > 0
    
    # キャッシュにキャラクターが正しく格納されていることを確認
    for char_id, character in real_notion_service.character_cache.items():
        assert 'name' in character
        assert character['name'].lower() == char_id or character['name'].lower().replace(' ', '') == char_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_get_character(real_notion_service):
    """実際のNotion APIを使用して特定のキャラクターを取得するテスト。"""
    # まずキャッシュを更新
    await real_notion_service.refresh_character_cache()
    
    # キャッシュから最初のキャラクター名を取得
    if not real_notion_service.character_cache:
        pytest.skip("キャラクターが取得できませんでした")
    
    first_character_name = next(iter(real_notion_service.character_cache.values()))['name']
    
    # そのキャラクターを取得
    character = await real_notion_service.get_character(first_character_name)
    
    # キャラクターが正しく取得できたことを確認
    assert character is not None
    assert character['name'] == first_character_name
    
    # 基本的なプロパティが含まれていることを確認
    expected_properties = ['personality', 'speaking_style', 'language']
    for prop in expected_properties:
        assert prop in character, f"キャラクターに {prop} プロパティがありません"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_get_character_by_bot_name(real_notion_service):
    """実際のAPIを使用してbot名からキャラクターを取得するテスト。"""
    # キャッシュを更新
    await real_notion_service.refresh_character_cache()
    
    # キャッシュにデータがあるか確認
    if not real_notion_service.character_cache:
        pytest.skip("キャラクターが取得できませんでした")
    
    # 特定のボット名でのテスト
    bot_names = ["GPT-4o-animal", "claude-animal"]
    for bot_name in bot_names:
        # 通常の名前でキャラクターを取得
        character = await real_notion_service.get_character(bot_name)
        
        # キャッシュにこのボット名のキャラクターがある場合、正しく取得できることを確認
        if character:
            assert character['name'] == bot_name
            
            # 小文字でも取得できることを確認
            lowercase_character = await real_notion_service.get_character(bot_name.lower())
            assert lowercase_character is not None
            assert lowercase_character['name'] == bot_name
            
            # スペースなしでも取得できることを確認
            nospace_name = bot_name.replace(' ', '')
            nospace_character = await real_notion_service.get_character(nospace_name)
            assert nospace_character is not None
            assert nospace_character['name'] == bot_name


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_format_character_prompt(real_notion_service):
    """実際のキャラクターデータを使用してプロンプト生成をテストします。"""
    # キャラクターを取得
    await real_notion_service.refresh_character_cache()
    
    if not real_notion_service.character_cache:
        pytest.skip("キャラクターが取得できませんでした")
    
    # 最初のキャラクターを取得
    character = next(iter(real_notion_service.character_cache.values()))
    
    # プロンプトを生成
    prompt = real_notion_service.format_character_prompt(character)
    
    # 基本的な検証
    assert prompt
    assert f"You are {character['name']}." in prompt
    
    # キャラクターの主要属性がプロンプトに含まれているか確認
    if 'personality' in character:
        assert f"Personality: {character['personality']}" in prompt
    
    if 'speaking_style' in character:
        assert f"Speaking style: {character['speaking_style']}" in prompt
    
    if 'language' in character:
        assert f"You primarily communicate in {character['language']}." in prompt
