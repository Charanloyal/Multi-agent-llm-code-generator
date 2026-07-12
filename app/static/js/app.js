let eventSource = null;

document.addEventListener('DOMContentLoaded', () => {
    updateCacheIndicator();
});

async function updateCacheIndicator() {
    try {
        const response = await fetch('/api/v1/cache/status');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('cache-indicator').innerText = `Cache: ${data.cache_size} items`;
        }
    } catch (err) {
        console.error('Failed to load cache status:', err);
    }
}

async function clearCache() {
    try {
        const response = await fetch('/api/v1/cache/clear', { method: 'POST' });
        if (response.ok) {
            updateCacheIndicator();
            logToTerminal('System Cache: In-memory query cache cleared successfully.', 'cache');
        }
    } catch (err) {
        logToTerminal(`System Error: Cache clear failed: ${err.message}`, 'critique');
    }
}

function logToTerminal(message, type = 'system') {
    const logsContainer = document.getElementById('terminal-logs');
    const logDiv = document.createElement('div');
    logDiv.className = `log-line ${type}`;
    
    // Prefix tags based on logger types
    let prefix = '> ';
    if (type === 'cache') prefix = '[CACHE] ';
    else if (type === 'rag') prefix = '[RAG ENGINE] ';
    else if (type === 'synthesis') prefix = '[SYNTHESIS AGENT] ';
    else if (type === 'critique') prefix = '[CRITIQUE AGENT] ';
    
    logDiv.innerText = `${prefix}${message}`;
    logsContainer.appendChild(logDiv);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function handleGeneration(event) {
    event.preventDefault();
    
    // Close existing connection if any
    if (eventSource) {
        eventSource.close();
    }
    
    const generateBtn = document.getElementById('generate-btn');
    const formInputs = document.querySelectorAll('#generator-form input, #generator-form textarea, #generator-form select');
    const codeBlock = document.getElementById('code-block');
    const terminalLogs = document.getElementById('terminal-logs');
    
    // Reset display UI
    terminalLogs.innerHTML = '';
    codeBlock.innerText = '';
    logToTerminal('Initializing generation lifecycle...', 'system');
    
    // Disable inputs
    formInputs.forEach(input => input.disabled = true);
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner"></span> Streaming...';
    
    // Build query params
    const prompt = document.getElementById('prompt').value;
    const max_critiques = document.getElementById('max_critiques').value;
    const hops = document.getElementById('hops').value;
    const temperature = document.getElementById('temperature').value;
    
    const url = `/api/v1/generate/stream?prompt=${encodeURIComponent(prompt)}&max_critiques=${max_critiques}&hops=${hops}&temperature=${temperature}`;
    
    eventSource = new EventSource(url);
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Map logs
            if (data.log) {
                let logType = 'system';
                if (data.status === 'RETRIEVING') {
                    if (data.log.includes('Cache')) logType = 'cache';
                    else logType = 'rag';
                }
                else if (data.status === 'SYNTHESIZING') logType = 'synthesis';
                else if (data.status === 'CRITIQUING') logType = 'critique';
                else if (data.status === 'COMPLETED') logType = 'system';
                
                logToTerminal(data.log, logType);
            }
            
            // Map code streams
            if (data.status === 'SYNTHESIZING_STREAM' && data.code) {
                if (data.clear) {
                    codeBlock.innerText = data.code;
                } else {
                    codeBlock.innerText += data.code;
                }
            }
            
            // Check completed lifecycle
            if (data.status === 'COMPLETED') {
                if (data.final_code) {
                    codeBlock.innerText = data.final_code;
                }
                eventSource.close();
                enableInputs();
                updateCacheIndicator();
            }
            
        } catch (err) {
            console.error('Error parsing SSE event data:', err);
        }
    };
    
    eventSource.onerror = (err) => {
        logToTerminal('Connection closed or interrupted.', 'system');
        eventSource.close();
        enableInputs();
    };

    function enableInputs() {
        formInputs.forEach(input => input.disabled = false);
        generateBtn.disabled = false;
        generateBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            Run Pipeline
        `;
    }
}

function copyCode() {
    const codeBlock = document.getElementById('code-block');
    const copyBtn = document.getElementById('copy-btn');
    const originalText = copyBtn.innerHTML;
    
    navigator.clipboard.writeText(codeBlock.innerText).then(() => {
        copyBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Copied!
        `;
        copyBtn.style.borderColor = '#10b981';
        copyBtn.style.color = '#10b981';
        
        setTimeout(() => {
            copyBtn.innerHTML = originalText;
            copyBtn.style.borderColor = '';
            copyBtn.style.color = '';
        }, 2000);
    });
}
