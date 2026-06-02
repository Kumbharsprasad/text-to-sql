from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from agent import TextToSQLAgent
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Text-to-SQL Agent")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent = None

class ChatRequest(BaseModel):
    query: str


class ApiKeyRequest(BaseModel):
    api_key: str

@app.post("/api/upload")
async def upload_database(file: UploadFile = File(...)):
    """Upload and connect to SQLite database file"""
    global agent
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not file.filename.endswith('.db') and not file.filename.endswith('.sqlite'):
        raise HTTPException(status_code=400, detail="Only .db or .sqlite files are supported")
    
    try:
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, file.filename)
        
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        db_url = f'sqlite:///{filepath}'
        agent = TextToSQLAgent(db_url)
        return {"success": True, "message": "Database uploaded successfully"}
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Process natural language query"""
    global agent
    if not agent:
        raise HTTPException(status_code=400, detail="Please connect to a database first")
    
    if not request.query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        result = agent.process_query(request.query)
        return result
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/reset")
async def reset_conversation():
    """Reset conversation memory"""
    global agent
    if agent:
        agent.reset_memory()
    return {"success": True, "message": "Conversation reset"}

@app.get("/api/schema")
async def get_schema():
    """Get database schema"""
    global agent
    if not agent:
        raise HTTPException(status_code=400, detail="Please connect to a database first")
    
    try:
        schema = agent.get_schema()
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/set_api_key")
async def set_api_key(request: ApiKeyRequest):
    """Set GROQ API key (saved to .env and process env)."""
    try:
        key = request.api_key.strip()
        if not key:
            raise HTTPException(status_code=400, detail="api_key is required")

        # Update or create .env file with GROQ_API_KEY
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()

        updated = False
        for i, line in enumerate(lines):
            if line.startswith("GROQ_API_KEY="):
                lines[i] = f"GROQ_API_KEY={key}"
                updated = True
                break

        if not updated:
            lines.append(f"GROQ_API_KEY={key}")

        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Set in process environment for immediate use
        os.environ["GROQ_API_KEY"] = key

        return {"success": True, "message": "API key set"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_api_key_status")
async def get_api_key_status():
    """Return whether GROQ API key is set on the server (does not return the key)."""
    key = os.getenv("GROQ_API_KEY")
    return {"set": bool(key)}
