let isConnected = false;

// Toggle connection methods
document.querySelectorAll('.method-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.method-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        const method = btn.dataset.method;
        document.querySelectorAll('.method-content').forEach(content => {
            content.classList.add('hidden');
        });
        document.getElementById(`${method}-method`).classList.remove('hidden');
    });
});

// Connect to database via URL
async function connectDatabase() {
    const dbUrl = document.getElementById('db-url').value.trim();
    
    if (!dbUrl) {
        alert('Please enter a database URL');
        return;
    }
    
    try {
        const response = await fetch('/api/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ database_url: dbUrl })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            isConnected = true;
            showConnectedUI();
            loadSchema();
        } else {
            const errorMsg = data.detail || data.error || 'Connection failed';
            alert('Error: ' + errorMsg);
        }
    } catch (error) {
        alert('Connection failed: ' + error.message);
    }
}

// Upload database file
async function uploadDatabase() {
    const fileInput = document.getElementById('db-file');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a database file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            isConnected = true;
            showConnectedUI();
            loadSchema();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Upload failed: ' + error.message);
    }
}

// Show connected UI
function showConnectedUI() {
    document.getElementById('connection-panel').classList.add('hidden');
    document.getElementById('schema-panel').classList.remove('hidden');
    document.getElementById('chat-panel').classList.remove('hidden');
}

// Load database schema
async function loadSchema() {
    try {
        const response = await fetch('/api/schema');
        const data = await response.json();
        
        if (data.schema) {
            document.getElementById('schema-content').textContent = data.schema;
        }
    } catch (error) {
        console.error('Failed to load schema:', error);
    }
}

// Toggle schema visibility
function toggleSchema() {
    const content = document.getElementById('schema-content');
    content.classList.toggle('hidden');
}

// Send message
async function sendMessage() {
    const input = document.getElementById('user-query');
    const query = input.value.trim();
    
    if (!query) return;
    
    if (!isConnected) {
        alert('Please connect to a database first');
        return;
    }
    
    // Add user message to chat
    addMessage('user', query);
    input.value = '';
    
    // Add loading indicator
    const loadingId = addLoading();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        // Remove loading indicator
        removeLoading(loadingId);
        
        // Add assistant response
        addAssistantMessage(data);
    } catch (error) {
        removeLoading(loadingId);
        addMessage('assistant', 'Error: ' + error.message);
    }
}

// Add message to chat
function addMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Add loading indicator
function addLoading() {
    const messagesDiv = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    const loadingId = 'loading-' + Date.now();
    loadingDiv.id = loadingId;
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = '<div class="loading"></div>';
    messagesDiv.appendChild(loadingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return loadingId;
}

// Remove loading indicator
function removeLoading(id) {
    const element = document.getElementById(id);
    if (element) element.remove();
}

// Add assistant message with SQL and results
function addAssistantMessage(data) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    
    let html = '';
    
    if (data.sql) {
        html += `<div class="sql"><strong>SQL:</strong><br>${escapeHtml(data.sql)}</div>`;
    }
    
    if (data.error) {
        html += `<div class="error"><strong>Error:</strong> ${escapeHtml(data.error)}</div>`;
    } else if (data.result) {
        if (data.result.columns && data.result.rows) {
            html += '<div class="result"><strong>Results:</strong><br>';
            html += '<table><thead><tr>';
            data.result.columns.forEach(col => {
                html += `<th>${escapeHtml(col)}</th>`;
            });
            html += '</tr></thead><tbody>';
            data.result.rows.forEach(row => {
                html += '<tr>';
                row.forEach(cell => {
                    html += `<td>${escapeHtml(String(cell))}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>';
        } else if (data.result.message) {
            html += `<div class="result">${escapeHtml(data.result.message)}</div>`;
        }
    }
    
    messageDiv.innerHTML = html;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Handle enter key
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Reset conversation
async function resetConversation() {
    try {
        await fetch('/api/reset', { method: 'POST' });
        document.getElementById('chat-messages').innerHTML = '';
    } catch (error) {
        console.error('Failed to reset:', error);
    }
}
