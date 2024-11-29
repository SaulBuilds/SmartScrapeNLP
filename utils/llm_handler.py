import os
from openai import OpenAI
import json

class LLMHandler:
    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
        self.openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def process_user_input(self, user_message):
        """Process user input and return relevant websites and context"""
        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI assistant helping users find relevant websites 
                        for their research topics. Analyze the user's request and provide a list 
                        of relevant websites to scrape. Respond in JSON format with:
                        {
                            "message": "your response to user",
                            "websites": ["url1", "url2", ...],
                            "context": "additional context for processing"
                        }"""
                    },
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        
        except Exception as e:
            return {
                "message": f"Error processing request: {str(e)}",
                "websites": [],
                "context": "error"
            }

    def analyze_relevance(self, content, context):
        """Analyze content relevance using LLM"""
        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze the relevance of the content to the given context. 
                        Respond with a JSON object containing:
                        {
                            "relevance_score": float between 0 and 1,
                            "explanation": "brief explanation of the score"
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"Context: {context}\nContent: {content[:1000]}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {
                "relevance_score": 0.0,
                "explanation": f"Error analyzing relevance: {str(e)}"
            }
