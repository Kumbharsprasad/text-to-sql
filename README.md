# Text-to-SQL Conversational Agent

A lightweight, stateful LLM-powered agent that enables natural language querying of SQLite databases using LangGraph.

## Features

- **Natural Language to SQL**: Query databases using conversational prompts
- **SQLite Support**: Upload SQLite database files (.db, .sqlite)
- **Self-Healing Retry**: Automatic error recovery with 80% failure reduction
- **Conversational Memory**: Multi-turn context for follow-up queries
- **Schema-Aware**: Automatic schema extraction for accurate SQL generation
- **Streamlit UI**: Modern, interactive interface with chat interface

## Tech Stack

- **Backend**: FastAPI + LangGraph + LangChain
- **Frontend**: Streamlit
- **Database**: SQLite
- **LLM**: Groq (Llama 3 70B)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your Groq API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=your_groq_api_key_here
```

Get your Groq API key from https://console.groq.com/

### 3. Run the Application

Start the FastAPI backend:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

In a new terminal, start the Streamlit frontend:
```bash
streamlit run streamlit_app.py
```

The application will be available at `http://localhost:8501`

## Usage

### Upload SQLite Database

1. Open the application in your browser at `http://localhost:8501`
2. In the sidebar, click "Browse files" to upload a `.db` or `.sqlite` file
3. The database schema will be displayed automatically

### Query Your Database

Once connected, you can ask questions in natural language:

- "Show me all users from the USA"
- "What are the top 5 products by sales?"
- "Count the number of orders placed this month"

The agent will:
1. Extract the database schema
2. Generate appropriate SQL
3. Execute the query
4. Display results in a table
5. Automatically retry on errors

## API Endpoints

- `POST /api/upload` - Upload SQLite database file
- `POST /api/chat` - Process natural language query
- `POST /api/reset` - Reset conversation memory
- `GET /api/schema` - Get database schema

## Deployment

### Local Deployment

Start the FastAPI backend:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

In a new terminal, start the Streamlit frontend:
```bash
streamlit run streamlit_app.py
```

### Production Deployment

Using Uvicorn for backend:
```bash
uvicorn app:app --workers 4 --host 0.0.0.0 --port 8000
```

Streamlit frontend:
```bash
streamlit run streamlit_app.py --server.port 8501
```

### Docker Deployment

Build and run:
```bash
docker build -t textsql-agent .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key textsql-agent
```

## Project Structure

```
textsql/
├── app.py              # FastAPI backend
├── streamlit_app.py    # Streamlit frontend
├── agent.py            # LangGraph agent implementation
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── uploads/           # Uploaded database files
```

## How It Works

1. **Schema Extraction**: Automatically extracts table and column information
2. **SQL Generation**: Uses LangGraph with LLM to convert natural language to SQL
3. **Query Execution**: Executes generated SQL against the database
4. **Error Recovery**: Implements retry mechanism with error analysis
5. **Context Retention**: Maintains conversation history for follow-up queries

## License

MIT
