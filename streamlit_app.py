import streamlit as st
import requests
import os

st.set_page_config(page_title="Text-to-SQL Agent", page_icon="🗄️", layout="wide")

st.title("🗄️ Text-to-SQL Agent")
st.markdown("Query your SQLite database using natural language")

# Sidebar for database upload
with st.sidebar:
    st.header("Database Connection")
    # Check API key status on load
    if 'api_set' not in st.session_state:
        try:
            status = requests.get('http://localhost:8000/api/get_api_key_status', timeout=2)
            st.session_state.api_set = status.ok and status.json().get('set', False)
        except Exception:
            st.session_state.api_set = False

    st.subheader("Groq API Key")
    api_input = st.text_input("Enter your GROQ API key", type='password')
    if st.button("Save API Key"):
        if not api_input:
            st.error("Please enter an API key before saving")
        else:
            try:
                resp = requests.post('http://localhost:8000/api/set_api_key', json={'api_key': api_input})
                if resp.status_code == 200:
                    st.success("API key saved on server")
                    st.session_state.api_set = True
                else:
                    st.error(f"Failed to save API key: {resp.text}")
            except Exception as e:
                st.error(f"Error saving API key: {str(e)}")
    
    uploaded_file = st.file_uploader("Upload SQLite database", type=['db', 'sqlite'])
    
    if uploaded_file:
        # Save uploaded file
        # Require API key to be set on server first
        if not st.session_state.get('api_set', False):
            st.error("Please save your GROQ API key before uploading a database.")
        else:
            upload_dir = 'uploads'
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, uploaded_file.name)

            with open(filepath, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            st.success(f"Database uploaded: {uploaded_file.name}")

            # Connect to database
            try:
                response = requests.post(
                    'http://localhost:8000/api/upload',
                    files={'file': uploaded_file}
                )

                if response.status_code == 200:
                    st.session_state.connected = True
                    st.success("Database connected successfully!")

                    # Get schema
                    schema_response = requests.get('http://localhost:8000/api/schema')
                    if schema_response.status_code == 200:
                        schema = schema_response.json().get('schema', '')
                        with st.expander("View Database Schema"):
                            st.text(schema)
                else:
                    st.error(f"Connection failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    if st.button("Reset Conversation"):
        requests.post('http://localhost:8000/api/reset')
        st.session_state.messages = []
        st.rerun()

# Main chat interface
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message['role']):
        if message['role'] == 'assistant':
            if 'nl_response' in message and message['nl_response']:
                st.markdown(message['nl_response'])
            if 'sql' in message:
                st.code(message['sql'], language='sql')
            if 'result' in message:
                if 'columns' in message['result'] and 'rows' in message['result']:
                    import pandas as pd
                    df = pd.DataFrame(message['result']['rows'], columns=message['result']['columns'])
                    st.dataframe(df)
                elif 'message' in message['result']:
                    st.info(message['result']['message'])
            if 'error' in message:
                st.error(message['error'])
        else:
            st.markdown(message['content'])

# Chat input
if prompt := st.chat_input("Ask a question about your data..."):
    if not st.session_state.get('connected', False):
        st.error("Please upload a database first")
        st.stop()
    
    # Add user message
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message('assistant'):
        with st.spinner('Generating SQL and executing query...'):
            try:
                response = requests.post(
                    'http://localhost:8000/api/chat',
                    json={'query': prompt}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Display SQL
                    if data.get('sql'):
                        st.code(data['sql'], language='sql')
                    
                    # Display results
                    if data.get('result'):
                        if 'columns' in data['result'] and 'rows' in data['result']:
                            import pandas as pd
                            df = pd.DataFrame(data['result']['rows'], columns=data['result']['columns'])
                            st.dataframe(df)
                        elif 'message' in data['result']:
                            st.info(data['result']['message'])
                    
                    # Display error
                    if data.get('error'):
                        st.error(data['error'])
                    
                    # Add to message history
                    st.session_state.messages.append({
                        'role': 'assistant',
                        'nl_response': data.get('nl_response', ''),
                        'sql': data.get('sql', ''),
                        'result': data.get('result'),
                        'error': data.get('error')
                    })
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
