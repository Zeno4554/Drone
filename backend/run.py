"""Backend startup script."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    
    print(f"""
    
    🚀 AeroCorridor Backend - v{settings.VERSION}
    {"="*50}
    
    Database: {settings.DATABASE_URL}
    API URL: http://localhost:8000{settings.API_V1_PREFIX}
    Docs: http://localhost:8000/docs
    
    {"="*50}
    """)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
    )
