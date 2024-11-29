document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements with null checks
    const elements = {
        chatForm: document.getElementById('chat-form'),
        userInput: document.getElementById('user-input'),
        chatMessages: document.querySelector('.chat-messages'),
        websiteSelection: document.getElementById('website-selection'),
        websiteList: document.querySelector('.website-list'),
        websiteForm: document.getElementById('website-form'),
        scrapeSelectedBtn: document.getElementById('scrape-selected'),
        loadingIndicator: document.querySelector('.loading-indicator'),
        progressBar: document.querySelector('.progress-bar'),
        statusText: document.querySelector('.status-text'),
        resultsContainer: document.querySelector('.results-container'),
        logWindow: document.querySelector('.log-window'),
        logContent: document.querySelector('.log-content'),
        drawer: document.getElementById('left-drawer'),
        drawerWrapper: document.querySelector('.drawer-wrapper'),
        drawerToggle: document.getElementById('drawer-toggle'),
        drawerClose: document.querySelector('.drawer-close'),
        scrapingProgress: document.querySelector('.scraping-progress'),
        currentTask: document.querySelector('.current-task'),
        statsContainer: document.querySelector('.stats-container'),
        pauseScrapingBtn: document.querySelector('.pause-scraping'),
        cancelScrapingBtn: document.querySelector('.cancel-scraping')
    };

    // Initialize progress state
    let isScrapingPaused = false;
    let currentProgress = 0;

    // Event Listeners with null checks
    if (elements.drawerToggle && elements.drawer && elements.drawerWrapper) {
        elements.drawerToggle.addEventListener('click', () => {
            elements.drawer.classList.toggle('open');
            elements.drawerWrapper.classList.toggle('drawer-open');
            updateFolderStructure();
        });
    }

    if (elements.drawerClose && elements.drawer && elements.drawerWrapper) {
        elements.drawerClose.addEventListener('click', () => {
            elements.drawer.classList.remove('open');
            elements.drawerWrapper.classList.remove('drawer-open');
        });
    }

    if (elements.logWindow) {
        const logCloseBtn = elements.logWindow.querySelector('.log-close-btn');
        if (logCloseBtn) {
            logCloseBtn.addEventListener('click', () => {
                elements.logWindow.classList.add('d-none');
            });
        }
    }

    // Message Functions
    function addMessage(message, isUser = false) {
        if (!elements.chatMessages) {
            console.warn('Chat messages container not found');
            return;
        }
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.textContent = message;
        elements.chatMessages.appendChild(messageDiv);
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }

    // SSE Setup with improved error handling
    let eventSource = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 3;

    function setupEventSource() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource("/stream");
        
        eventSource.addEventListener('log', function(e) {
            try {
                const data = JSON.parse(e.data);
                addLogMessage(data.message, data.level);
            } catch (error) {
                console.warn('Error processing log event:', error);
            }
        });

        eventSource.addEventListener('progress', function(e) {
            try {
                const data = JSON.parse(e.data);
                updateProgress(data);
            } catch (error) {
                console.warn('Error processing progress event:', error);
            }
        });

        eventSource.addEventListener('error', function(e) {
            console.warn('SSE Connection error:', e);
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                setTimeout(setupEventSource, 1000 * reconnectAttempts);
            } else {
                console.error('Max reconnection attempts reached');
                addLogMessage('Lost connection to server', 'error');
            }
        });

        eventSource.addEventListener('open', function() {
            reconnectAttempts = 0;
            console.log('SSE Connection established');
        });
    }

    setupEventSource();

    function updateProgress(data) {
        if (!elements.scrapingProgress || !elements.progressBar || !elements.currentTask) {
            console.warn('Progress elements not found');
            return;
        }
        
        elements.scrapingProgress.classList.remove('d-none');
        
        if (data.progress !== undefined) {
            currentProgress = data.progress;
            elements.progressBar.style.width = `${data.progress}%`;
            elements.progressBar.setAttribute('aria-valuenow', data.progress);
        }

        if (data.message) {
            elements.currentTask.textContent = data.message;
        }

        if (data.stats) {
            updateStats(data.stats);
        }

        if (data.status === 'complete') {
            elements.scrapingProgress.classList.add('d-none');
            currentProgress = 0;
        }
    }

    function updateStats(stats) {
        if (!elements.statsContainer) return;

        const statsElements = {
            processed: elements.statsContainer.querySelector('.processed span'),
            successful: elements.statsContainer.querySelector('.successful span'),
            failed: elements.statsContainer.querySelector('.failed span')
        };

        Object.entries(stats).forEach(([key, value]) => {
            if (statsElements[key]) {
                statsElements[key].textContent = value;
            }
        });
    }

    async function updateFolderStructure() {
        try {
            const response = await fetch('/api/folder-structure');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const structure = await response.json();
            const folderTree = document.querySelector('.folder-tree');
            if (!folderTree) {
                console.warn('Folder tree element not found');
                return;
            }
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

    function addLogMessage(message, level = 'info') {
        if (!elements.logContent) {
            console.warn('Log content element not found');
            return;
        }
        const msgDiv = document.createElement('div');
        msgDiv.className = `log-message ${level}`;
        msgDiv.textContent = message;
        elements.logContent.appendChild(msgDiv);
        elements.logContent.scrollTop = elements.logContent.scrollHeight;
    }

    function displayWebsites(websites) {
        if (!websites || !websites.length || !elements.websiteList || !elements.websiteSelection || !elements.scrapeSelectedBtn) {
            console.warn('Website display elements not found or empty website list');
            return;
        }
        
        elements.websiteList.innerHTML = websites.map((url, index) => `
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" value="${url}" id="website-${index}" checked>
                <label class="form-check-label" for="website-${index}">
                    ${url}
                </label>
            </div>
        `).join('');
        
        elements.websiteSelection.classList.remove('d-none');
        elements.scrapeSelectedBtn.classList.remove('d-none');
    }

    function displayResults(data) {
        if (!elements.resultsContainer) {
            console.warn('Results container not found');
            return;
        }
        
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
        elements.resultsContainer.innerHTML = resultsHtml;
    }

    // Form Handlers
    if (elements.chatForm) {
        elements.chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!elements.userInput || !elements.loadingIndicator) {
                console.warn('Required form elements not found');
                return;
            }

            const message = elements.userInput.value.trim();
            if (!message) return;

            addMessage(message, true);
            elements.userInput.value = '';
            elements.loadingIndicator.classList.add('active');

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
                elements.loadingIndicator.classList.remove('active');
            }
        });
    }

    if (elements.websiteForm) {
        elements.websiteForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!elements.logWindow || !elements.websiteList || !elements.loadingIndicator || !elements.scrapeSelectedBtn) {
                console.warn('Required form elements not found');
                return;
            }

            elements.logWindow.classList.remove('d-none');
            
            const selectedWebsites = Array.from(elements.websiteList.querySelectorAll('input[type="checkbox"]:checked'))
                .map(checkbox => checkbox.value);
                
            if (selectedWebsites.length === 0) {
                addMessage('Please select at least one website to scrape.');
                return;
            }

            elements.loadingIndicator.classList.add('active');
            elements.scrapeSelectedBtn.disabled = true;
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

                if (elements.websiteSelection && elements.scrapeSelectedBtn) {
                    elements.websiteSelection.classList.add('d-none');
                    elements.scrapeSelectedBtn.classList.add('d-none');
                }

            } catch (error) {
                addLogMessage(`Scraping error: ${error.message}`, 'error');
                addMessage('An error occurred during scraping. Please try again.');
            } finally {
                elements.loadingIndicator.classList.remove('active');
                elements.scrapeSelectedBtn.disabled = false;
            }
        });
    }

    // Initialize pause/cancel buttons
    if (elements.pauseScrapingBtn) {
        elements.pauseScrapingBtn.addEventListener('click', function() {
            isScrapingPaused = !isScrapingPaused;
            this.textContent = isScrapingPaused ? 'Resume' : 'Pause';
            this.classList.toggle('btn-warning');
            this.classList.toggle('btn-success');
            addLogMessage(isScrapingPaused ? 'Scraping paused' : 'Scraping resumed', 'info');
        });
    }

    if (elements.cancelScrapingBtn) {
        elements.cancelScrapingBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to cancel the scraping process?')) {
                addLogMessage('Scraping cancelled by user', 'info');
                if (elements.scrapingProgress) {
                    elements.scrapingProgress.classList.add('d-none');
                }
                // Additional cleanup as needed
            }
        });
    }
});
