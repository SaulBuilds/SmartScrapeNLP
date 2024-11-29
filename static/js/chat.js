document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.querySelector('.chat-messages');
    const websiteSelection = document.getElementById('website-selection');
    const websiteList = document.querySelector('.website-list');
    const websiteForm = document.getElementById('website-form');
    const scrapeSelectedBtn = document.getElementById('scrape-selected');
    const loadingIndicator = document.querySelector('.loading-indicator');
    const progressBar = document.querySelector('.progress-bar');
    const statusText = document.querySelector('.status-text');
    const resultsContainer = document.querySelector('.results-container');
    const logWindow = document.querySelector('.log-window');
    const logContent = document.querySelector('.log-content');
    const logCloseBtn = document.querySelector('.log-close-btn');
    const drawer = document.getElementById('left-drawer');
    const drawerWrapper = document.querySelector('.drawer-wrapper');
    const drawerToggle = document.getElementById('drawer-toggle');
    const drawerClose = document.querySelector('.drawer-close');

    // Event Listeners
    drawerToggle.addEventListener('click', () => {
        drawer.classList.toggle('open');
        drawerWrapper.classList.toggle('drawer-open');
        updateFolderStructure();
    });

    drawerClose.addEventListener('click', () => {
        drawer.classList.remove('open');
        drawerWrapper.classList.remove('drawer-open');
    });

    if (logCloseBtn) {
        logCloseBtn.addEventListener('click', () => {
            logWindow.classList.add('d-none');
        });
    }

    // Message Functions
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // SSE Setup
    const eventSource = new EventSource("/stream");
    
    eventSource.addEventListener('log', function(e) {
        const data = JSON.parse(e.data);
        addLogMessage(data.message, data.level);
    });

    eventSource.addEventListener('progress', function(e) {
        const data = JSON.parse(e.data);
        updateProgress(data);
    });

    eventSource.onerror = function(e) {
        console.error('SSE Error:', e);
        eventSource.close();
    };

    function updateProgress(data) {
        if (data.progress !== null) {
            progressBar.style.width = `${data.progress}%`;
            progressBar.setAttribute('aria-valuenow', data.progress);
        }
        if (data.message) {
            statusText.textContent = data.message;
        }
        if (data.status === 'complete') {
            setTimeout(() => {
                loadingIndicator.classList.remove('active');
                progressBar.style.width = '0%';
                progressBar.setAttribute('aria-valuenow', 0);
            }, 1000);
        }
    }

    async function updateFolderStructure() {
        try {
            const response = await fetch('/api/folder-structure');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const structure = await response.json();
            const folderTree = document.querySelector('.folder-tree');
            folderTree.innerHTML = '';
            folderTree.appendChild(renderFolderTree(structure));
        } catch (error) {
            console.error('Error fetching folder structure:', error);
            addLogMessage(`Failed to update folder structure: ${error.message}`, 'error');
        }
    }

    function renderFolderTree(node, level = 0) {
        const div = document.createElement('div');
        div.className = 'folder-item';
        div.style.paddingLeft = `${level * 1.5}rem`;

        const icon = document.createElement('i');
        icon.className = `fas ${node.type === 'directory' ? 'fa-folder' : 'fa-file'} folder-icon`;
        
        div.appendChild(icon);
        div.appendChild(document.createTextNode(node.name));

        if (node.type === 'directory' && node.children) {
            const childrenDiv = document.createElement('div');
            childrenDiv.className = 'folder-children';
            node.children.forEach(child => {
                childrenDiv.appendChild(renderFolderTree(child, level + 1));
            });
            div.appendChild(childrenDiv);
        }

        return div;
    }

    function displayWebsites(websites) {
        if (!websites || websites.length === 0) return;
        
        websiteList.innerHTML = websites.map((url, index) => `
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" value="${url}" id="website-${index}" checked>
                <label class="form-check-label" for="website-${index}">
                    ${url}
                </label>
            </div>
        `).join('');
        
        websiteSelection.classList.remove('d-none');
        scrapeSelectedBtn.classList.remove('d-none');
    }

    function displayResults(data) {
        const resultsHtml = `
            <h3>Analysis Results</h3>
            <div class="results-content">
                ${data.analyzed_data.map(item => `
                    <div class="result-item mb-3">
                        <h4>Source: ${item.url}</h4>
                        <p>Relevance Score: ${item.relevance_score.toFixed(2)}</p>
                        <p>Found ${item.images.length} relevant images</p>
                        <div class="metadata">
                            <h5>Metadata:</h5>
                            <p>Title: ${item.metadata.title || 'N/A'}</p>
                            <p>Description: ${item.metadata.description || 'N/A'}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        resultsContainer.innerHTML = resultsHtml;
    }

    function addLogMessage(message, level = 'info') {
        const msgDiv = document.createElement('div');
        msgDiv.className = `log-message ${level}`;
        msgDiv.textContent = message;
        logContent.appendChild(msgDiv);
        logContent.scrollTop = logContent.scrollHeight;
    }

    // Form Handlers
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = userInput.value.trim();
        if (!message) return;

        addMessage(message, true);
        userInput.value = '';
        loadingIndicator.classList.add('active');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            addMessage(data.response);
            
            if (data.websites && data.websites.length > 0) {
                displayWebsites(data.websites);
            }
        } catch (error) {
            addMessage('Error processing your request. Please try again.');
            addLogMessage(`Chat error: ${error.message}`, 'error');
        } finally {
            loadingIndicator.classList.remove('active');
        }
    });

    websiteForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        logWindow.classList.remove('d-none');
        
        const selectedWebsites = Array.from(websiteList.querySelectorAll('input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);
            
        if (selectedWebsites.length === 0) {
            addMessage('Please select at least one website to scrape.');
            return;
        }

        loadingIndicator.classList.add('active');
        scrapeSelectedBtn.disabled = true;
        addLogMessage('Starting web scraping process...', 'info');

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ websites: selectedWebsites })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.analyzed_data) {
                displayResults(data);
                addLogMessage('Analysis completed successfully', 'info');
            }

            websiteSelection.classList.add('d-none');
            scrapeSelectedBtn.classList.add('d-none');

        } catch (error) {
            addLogMessage(`Scraping error: ${error.message}`, 'error');
            
            if (error.response) {
                const errorData = await error.response.json();
                const errorMessage = errorData.message || errorData.error || 'Unknown error occurred';
                addMessage(`Error: ${errorMessage}`);
                
                if (errorData.errors && errorData.errors.length > 0) {
                    errorData.errors.forEach(err => {
                        addLogMessage(`Failed to scrape ${err.url}: ${err.error}`, 'error');
                    });
                }
            } else {
                addMessage('Network error occurred. Please check your connection and try again.');
            }
        } finally {
            loadingIndicator.classList.remove('active');
            scrapeSelectedBtn.disabled = false;
        }
    });
});
