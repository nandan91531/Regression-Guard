import requests
from typing import Optional

class LLMClientError(Exception):
    """Custom exception raised when LLM generation fails."""
    pass

class LLMClient:
    """
    HTTP Client for local Ollama server or compatible LLM APIs with timeout handling and diagnostics.
    """
    def __init__(self, model: str = "llama3.2", ollama_url: str = "http://localhost:11434", timeout: int = 60):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """
        Sends a prompt to the Ollama API server and returns the response string.
        """
        endpoint = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            raise LLMClientError(
                f"Could not connect to Ollama server at {self.ollama_url}.\n"
                "Please make sure Ollama is installed and running (`ollama serve`)."
            ) from e
        except requests.exceptions.Timeout as e:
            raise LLMClientError(
                f"Ollama server timed out after {self.timeout} seconds at {endpoint}."
            ) from e
        except requests.exceptions.RequestException as e:
            raise LLMClientError(f"HTTP request to Ollama failed: {e}") from e

        if response.status_code != 200:
            raise LLMClientError(
                f"Ollama API returned HTTP status {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
            if "response" not in data:
                raise LLMClientError(f"Unexpected response payload format from Ollama: {data}")
            return data["response"]
        except Exception as e:
            raise LLMClientError(f"Failed to parse Ollama JSON response: {e}") from e
