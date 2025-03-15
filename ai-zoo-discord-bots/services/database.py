"""
Database module for storing LLM request logs.
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float

# Create base class for declarative models
Base = declarative_base()

class LLMRequest(Base):
    """Model for storing LLM API request logs."""
    __tablename__ = 'llm_requests'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    model = Column(String(50), nullable=False)
    messages = Column(JSON, nullable=False)  # Store full message history
    response = Column(Text, nullable=False)  # Store API response
    response_time = Column(Float, nullable=False)  # Response time in seconds
    total_time = Column(Float, nullable=False)   # Total processing time
    bot_name = Column(String(100), nullable=False)  # Name of the bot making request
    error = Column(Text, nullable=True)  # Store error message if request failed

# Create async engine
engine = create_async_engine(
    os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///data/llm_requests.db'),
    echo=True  # Set to False in production
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database and create tables."""
    logging.info("Starting database initialization...")
    try:
        # データディレクトリの存在確認
        db_path = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///data/llm_requests.db')
        logging.info(f"Using database path: {db_path}")
        
        if db_path.startswith('sqlite'):
            # SQLiteの場合、ファイルパスを抽出
            import re
            match = re.search(r'sqlite\+aiosqlite:///(.+)', db_path)
            if match:
                db_file_path = match.group(1)
                logging.info(f"Extracted SQLite database file path: {db_file_path}")
                # ディレクトリ部分を抽出
                db_dir = os.path.dirname(db_file_path)
                if db_dir:
                    logging.info(f"Checking database directory: {db_dir}")
                    if not os.path.exists(db_dir):
                        logging.info(f"Database directory does not exist. Creating: {db_dir}")
                        os.makedirs(db_dir, exist_ok=True)
                        logging.info(f"Created database directory: {db_dir}")
                    else:
                        logging.info(f"Database directory already exists: {db_dir}")
        
        # エンジンの接続確認
        logging.info("Testing database engine connection...")
        async with engine.begin() as conn:
            logging.info("Database connection successful")
            
            # テーブル作成前の確認
            logging.info("Checking existing tables...")
            await conn.run_sync(lambda sync_conn: logging.info(f"Current tables: {Base.metadata.tables.keys()}"))
            
            # テーブル作成
            logging.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Database tables created successfully")
        
        return True
    except Exception as e:
        logging.error(f"Database initialization failed: {e}", exc_info=True)
        return False

async def get_db_session() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def log_llm_request(
    session: AsyncSession,
    model: str,
    messages: Dict[str, Any],
    response: str,
    response_time: float,
    total_time: float,
    bot_name: str,
    error: Optional[str] = None
) -> None:
    """
    Log an LLM API request to the database.
    
    Args:
        session: Database session
        model: Name of the LLM model used
        messages: Full message history sent to the API
        response: API response text
        response_time: Time taken by the API to respond
        total_time: Total processing time including post-processing
        bot_name: Name of the bot making the request
        error: Error message if request failed
    """
    logging.info(f"Logging LLM request for bot: {bot_name}")
    logging.info(f"Model: {model}, Response time: {response_time:.2f}s, Total time: {total_time:.2f}s")
    
    try:
        llm_request = LLMRequest(
            model=model,
            messages=messages,
            response=response,
            response_time=response_time,
            total_time=total_time,
            bot_name=bot_name,
            error=error
        )
        
        logging.info("Created LLMRequest object, attempting to add to session...")
        session.add(llm_request)
        logging.info("Added to session, attempting to commit...")
        
        await session.commit()
        logging.info("Successfully committed LLM request to database")
        
    except Exception as e:
        logging.error(f"Failed to log LLM request: {e}", exc_info=True)
        # セッションをロールバック
        await session.rollback()
        logging.info("Session rolled back after error")
        raise  # エラーを再度発生させて、呼び出し元で処理できるようにする
