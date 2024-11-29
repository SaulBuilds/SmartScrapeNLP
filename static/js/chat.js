document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.querySelector('.chat-messages');
    const chatForm = document.querySelector('#chat-form');
    const userInput = document.querySelector('#user-input');
    const loadingIndicator = document.querySelector('.loading-indicator');
    const resultsContainer = document.querySelector('.results-container');
    const websiteSelection = document.querySelector('#website-selection');
    const websiteList = document.querySelector('.website-list');
    const websiteForm = document.querySelector('#website-form');
    const scrapeSelectedBtn = document.querySelector('#scrape-selected');

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function displayWebsites(websites) {
        if (!websites || websites.length === 0) return;
        
        websiteList.innerHTML = websites.map((url, index) => `
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" value="${url}" id="website-${index}">
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
                            <p>Title: ${item.metadata.title}</p>
                            <p>Description: ${item.metadata.description}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        resultsContainer.innerHTML = resultsHtml;
    }

    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, true);
        userInput.value = '';

        // Show loading indicator
        loadingIndicator.classList.add('active');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            // Add bot response
            addMessage(data.response);
            
            // Display website selection
            if (data.websites && data.websites.length > 0) {
                displayWebsites(data.websites);
            }

        } catch (error) {
            addMessage('Error processing your request. Please try again.');
            console.error('Error:', error);
        } finally {
            loadingIndicator.classList.remove('active');
        }
    });

    websiteForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const selectedWebsites = Array.from(websiteList.querySelectorAll('input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);
            
        if (selectedWebsites.length === 0) {
            addMessage('Please select at least one website to scrape.');
            return;
        }

        loadingIndicator.classList.add('active');
        scrapeSelectedBtn.disabled = true;

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ websites: selectedWebsites })
            });

            const data = await response.json();
            
            // Display analyzed results
            if (data.analyzed_data) {
                displayResults(data);
            }

            // Hide website selection after scraping
            websiteSelection.classList.add('d-none');
            scrapeSelectedBtn.classList.add('d-none');

        } catch (error) {
            addMessage('Error processing your request. Please try again.');
            console.error('Error:', error);
        } finally {
            loadingIndicator.classList.remove('active');
            scrapeSelectedBtn.disabled = false;
        }
    });
});
