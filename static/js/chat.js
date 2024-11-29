document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.querySelector('.chat-messages');
    const chatForm = document.querySelector('#chat-form');
    const userInput = document.querySelector('#user-input');
    const loadingIndicator = document.querySelector('.loading-indicator');
    const resultsContainer = document.querySelector('.results-container');

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
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
            
            // Display analyzed results
            if (data.analyzed_data) {
                displayResults(data);
            }

        } catch (error) {
            addMessage('Error processing your request. Please try again.');
            console.error('Error:', error);
        } finally {
            loadingIndicator.classList.remove('active');
        }
    });
});
