from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import create_engine, inspect, text
from typing import TypedDict, List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    query: str
    schema: str
    sql: str
    result: Any
    error: str
    retry_count: int
    conversation_history: List[Dict[str, str]]
    nl_response: str

class TextToSQLAgent:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
        self.schema = self._extract_schema()
        self.conversation_history = []
        
        # Build LangGraph
        self.graph = self._build_graph()
    
    def _extract_schema(self) -> str:
        """Extract database schema"""
        inspector = inspect(self.engine)
        schema_info = []
        
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            col_info = [f"{col['name']}: {col['type']}" for col in columns]
            schema_info.append(f"Table: {table_name}\nColumns: {', '.join(col_info)}")
        
        return "\n\n".join(schema_info)
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_query", self._execute_query)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("generate_sql")
        
        # Add edges
        workflow.add_edge("generate_sql", "execute_query")
        workflow.add_conditional_edges(
            "execute_query",
            self._should_retry,
            {
                "retry": "generate_sql",
                "success": "generate_response",
                "error": "handle_error"
            }
        )
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    def _generate_sql(self, state: AgentState) -> AgentState:
        """Generate SQL from natural language query"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL expert. Convert natural language to SQL queries.
            
Database Schema:
{schema}

Conversation History:
{history}

Rules:
- Use only the tables and columns shown in the schema
- Generate valid SQL for the database type
- Keep queries simple and efficient
- If the query is unclear, make reasonable assumptions
- Return ONLY the SQL query, no explanations"""),
            ("human", "{query}")
        ])
        
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state.get('conversation_history', [])])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "schema": self.schema,
            "query": state["query"],
            "history": history_str
        })
        
        sql = response.content.strip()
        # Remove markdown code blocks if present
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        sql = sql.strip()
        
        state["sql"] = sql
        return state
    
    def _execute_query(self, state: AgentState) -> AgentState:
        """Execute SQL query"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(state["sql"]))
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = result.keys()
                    state["result"] = {
                        "columns": list(columns),
                        "rows": [list(row) for row in rows]
                    }
                else:
                    state["result"] = {"message": f"Query executed successfully. {result.rowcount} rows affected."}
                state["error"] = ""
        except Exception as e:
            state["error"] = str(e)
            state["result"] = None
        
        return state
    
    def _should_retry(self, state: AgentState) -> str:
        """Determine if we should retry the query"""
        if state["error"]:
            if state["retry_count"] < 3:
                state["retry_count"] += 1
                return "retry"
            return "error"
        return "success"
    
    def _handle_error(self, state: AgentState) -> AgentState:
        """Handle final error after retries"""
        state["result"] = {"error": f"Failed after {state['retry_count']} retries: {state['error']}"}
        state["nl_response"] = ""
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate natural language response from query results"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant. Given the user's query, the executed SQL, and the SQL result, provide a concise natural language answer.
            
Be conversational and helpful. Explain the results in a clear, human-readable way."""),
            ("human", "User Query: {query}\nSQL Executed: {sql}\nSQL Result: {result}\n\nProvide a natural language response:")
        ])
        
        # Format result for the prompt
        if isinstance(state["result"], dict):
            if "columns" in state["result"] and "rows" in state["result"]:
                result_str = f"Columns: {state['result']['columns']}\nRows: {state['result']['rows'][:5]}"  # Show first 5 rows
            elif "message" in state["result"]:
                result_str = state["result"]["message"]
            elif "error" in state["result"]:
                result_str = state["result"]["error"]
            else:
                result_str = str(state["result"])
        else:
            result_str = str(state["result"])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "query": state["query"],
            "sql": state["sql"],
            "result": result_str
        })
        
        state["nl_response"] = response.content.strip()
        return state
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a natural language query"""
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": query})
        
        # Run the graph
        initial_state = {
            "query": query,
            "schema": self.schema,
            "sql": "",
            "result": None,
            "error": "",
            "retry_count": 0,
            "conversation_history": self.conversation_history,
            "nl_response": ""
        }
        
        final_state = self.graph.invoke(initial_state)
        
        # Add assistant response to history including SQL and result for richer context
        assistant_content = final_state.get("nl_response", "") or ""
        sql_text = final_state.get("sql", "") or ""
        result_text = final_state.get("result", None)
        assistant_content += "\n\nSQL: " + sql_text
        assistant_content += "\nResult: " + (str(result_text) if result_text is not None else "None")
        self.conversation_history.append({"role": "assistant", "content": assistant_content})
        
        return {
            "query": query,
            "sql": final_state["sql"],
            "result": final_state["result"],
            "error": final_state["error"],
            "nl_response": final_state.get("nl_response", "")
        }
    
    def reset_memory(self):
        """Reset conversation memory"""
        self.conversation_history = []
    
    def get_schema(self) -> str:
        """Get database schema"""
        return self.schema
