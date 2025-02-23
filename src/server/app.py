from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
import re
import black
import json
from openai import OpenAI
from typing import Optional

app = Flask(__name__)
CORS(app)

# Ollama API URL
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Set up logging
logging.basicConfig(level=logging.INFO)

# In-memory storage for conversation context
conversation_context = {}


def get_client(provider: str, api_key: Optional[str] = None):
    if provider == 'openai':
        return OpenAI(api_key=api_key)
    elif provider == 'groq':
        return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    return None

def setup_openai_client(api_key: str) -> None:
    """Configure OpenAI client"""
    openai.api_key = api_key

def send_completion(client: OpenAI, model: str, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
    """
    Send a chat completion request to OpenAI's API
    
    Args:
        prompt: The input prompt
        api_key: OpenAI API key
        model: Model to use (e.g., "gpt-4", "gpt-3.5-turbo")
        max_tokens: Maximum tokens in response
        temperature: Temperature for response generation
    
    Returns:
        The generated response text or None if failed
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error sending chat completion: {str(e)}")
        return None

def get_openai_model(model: str):
    """Map frontend model selection to actual OpenAI model identifier"""
    model_mapping = {
        "openai-4o": "gpt-4" 
    }
    return model_mapping.get(model, model)

def get_response(prompt: str, provider: str, model: str, api_key: Optional[str] = None) -> str:
    """
    Sends a prompt to the specified provider and returns the response.

    Args:
        prompt (str): The prompt to send to the provider.
        provider (str): The provider ('openai', 'groq', or 'ollama').
        model (str): The model to use for the provider.
        api_key (Optional[str]): The API key for providers requiring authentication.

    Returns:
        str: The response from the provider.

    Raises:
        ValueError: If the provider is invalid.
        Exception: If the request to the provider fails.
    """
    
    # OLLAMA_API_URL = "http://localhost:11434/api/generate"
    print(f"Getting response for provider: {provider}, model: {model}")
    if provider in ['openai', 'groq']:
        client = get_client(provider, api_key)
        if client is None:
            raise ValueError("Invalid provider")
        response = send_completion(client, model, prompt)
        if response is None:
            raise Exception(f"Failed to get response from {provider}")
        return response
    elif provider == 'ollama':
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_API_URL, json=payload)
        response_data = response.json()
        return response_data.get("response", "").strip()
    else:
        raise ValueError("Invalid provider")


def format_code_with_black(code: str) -> str:
    """
    Format the given Python code using Black.
    """
    try:
        # Format the code using Black
        formatted_code = black.format_str(code, mode=black.Mode())
        return formatted_code
    except Exception as e:
        # Log the error and return the original code if formatting fails
        logging.error(f"Failed to format code with Black: {str(e)}")
        return code

def format_code_blocks_with_black(response_text: str) -> str:
    """
    Detect code blocks in the response and format them using Black.
    """
    code_block_regex = r"(```python\s*([\s\S]*?)\s*```)"
    def format_match(match):
        code_block = match.group(2).strip()
        formatted_code = format_code_with_black(code_block)
        return f"```\n{formatted_code}\n```"

    return re.sub(code_block_regex, format_match, response_text, flags=re.IGNORECASE)

def format_response(response_text):
    """
    Format the raw response text into a structured list of bullet points or preserve code blocks.
    """
    # Detect and preserve code blocks
    lines = response_text.split("\n")
    formatted_lines = []
    inside_code_block = False

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("```"):
            # Toggle the code block flag
            inside_code_block = not inside_code_block
            formatted_lines.append(stripped_line)  # Preserve ``` markers
        elif inside_code_block:
            # Preserve indentation inside code blocks
            formatted_lines.append(line)
        else:
            # Format non-code lines as bullet points if they are not empty
            if stripped_line:
                formatted_lines.append(f"- {stripped_line}")
            else:
                formatted_lines.append("")  # Preserve blank lines

    return "\n".join(formatted_lines)

@app.route('/get_suggestions', methods=['POST'])
def get_suggestions():
    """
    Analyzes the provided code and suggests improvements using the specified provider.

    Request JSON:
        - code (str): The code to analyze.
        - user_id (str, optional): The user ID (defaults to 'default_user').
        - file_name (str, optional): The file name (defaults to 'Untitled').
        - provider (str, optional): The provider ('openai', 'groq', or 'ollama'; defaults to 'ollama').
        - model (str, optional): The model to use (defaults to 'deepseek-coder:6.7b').
        - api_key (str, optional): The API key for providers requiring authentication.

    Returns:
        JSON response with the suggestion or an error message.
    """
    data = request.json
    code = data.get('code', '').strip()
    user_id = data.get('user_id', 'default_user')
    file_name = data.get('file_name', 'Untitled')
    provider = data.get('provider', 'ollama')
    model = data.get('model', 'deepseek-coder:6.7b')
    api_key = data.get('api_key')

    if not code:
        return jsonify({"error": "No code provided", "status": "failure"}), 400

    try:
        # Initialize or update conversation context
        if user_id not in conversation_context:
            conversation_context[user_id] = {
                "code": code,
                "file_name": file_name,
                "conversation": []
            }
        else:
            conversation_context[user_id]["code"] = code
            conversation_context[user_id]["file_name"] = file_name

        # Construct prompt for code analysis
        prompt = (
            f"Analyze the following Python code from file '{file_name}':\n\n"
            f"```python\n{code}\n```\n\n"
            "Provide suggestions for improvement."
        )

        # Get response from the provider
        suggestion = get_response(prompt, provider, model, api_key)

        # Format the response (ensure format_response and format_code_blocks_with_black are defined)
        formatted_suggestion = format_response(suggestion)
        formatted_suggestion = format_code_blocks_with_black(formatted_suggestion)

        # Store the response in conversation context
        conversation_context[user_id]["conversation"].append({
            "role": "assistant",
            "message": formatted_suggestion
        })

        return jsonify({
            "suggestion": formatted_suggestion,
            "status": "success"
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to get response: {str(e)}"}), 500

@app.route('/ask_question', methods=['POST'])
def ask_question():
    """
    Answers user questions, including code-related queries if applicable, using the specified provider.

    Request JSON:
        - question (str): The question to answer.
        - user_id (str, optional): The user ID (defaults to 'default_user').
        - file_name (str, optional): The file name (defaults to 'Untitled').
        - code (str, optional): The code related to the question.
        - provider (str, optional): The provider ('openai', 'groq', or 'ollama'; defaults to 'ollama').
        - model (str, optional): The model to use (defaults to 'deepseek-coder:6.7b').
        - api_key (str, optional): The API key for providers requiring authentication.

    Returns:
        JSON response with the answer or an error message.
    """
    data = request.json
    print(f"Received data: {data}")
    question = data.get('question', '').strip()
    user_id = data.get('user_id', 'default_user')
    file_name = data.get('file_name', 'Untitled')
    code = data.get('code', '').strip()
    provider = data.get('provider', 'ollama')
    model = data.get('model', 'deepseek-coder:6.7b')
    api_key = data.get('api_key')

    if not question:
        return jsonify({"error": "No question provided", "status": "failure"}), 400

    try:
        # Determine if the question is code-related
        is_code_related = any(
            phrase in question.lower() for phrase in ["code", "function", "variable", "implementation"]
        )

        # Construct prompt based on whether the question is code-related and code is provided
        if is_code_related and code:
            prompt = (
                f"File: {file_name}\nCode:\n```python\n{code}\n```\n\n"
                f"Question: {question}\n\n"
                "Provide a concise solution or explanation. "
                "If appropriate, include full code. Format the response using bullet points (max 5-6 points). "
                "Keep the response under 200 words."
            )
        else:
            prompt = (
                f"Question: {question}\n\n"
                "Provide a concise answer or explanation. "
                "Format the response using bullet points (max 5-6 points). "
                "Keep the response under 200 words."
            )

        # Get response from the provider
        answer = get_response(prompt, provider, model, api_key)

        # Format the response
        formatted_answer = format_response(answer)
        formatted_answer = format_code_blocks_with_black(formatted_answer)

        # Initialize or update conversation context
        if user_id not in conversation_context:
            conversation_context[user_id] = {"conversation": []}
        conversation_context[user_id]["conversation"].extend([
            {"role": "user", "message": question},
            {"role": "assistant", "message": formatted_answer}
        ])

        return jsonify({
            "answer": formatted_answer,
            "status": "success"
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to get response: {str(e)}"}), 500

@app.route('/general_help', methods=['POST'])
def general_help():
    """
    Provides general coding help, including code if provided, using the specified provider.

    Request JSON:
        - question (str): The question to answer.
        - user_id (str, optional): The user ID (defaults to 'default_user').
        - file_name (str, optional): The file name (defaults to 'Untitled').
        - code (str, optional): The code related to the question.
        - provider (str, optional): The provider ('openai', 'groq', or 'ollama'; defaults to 'ollama').
        - model (str, optional): The model to use (defaults to 'deepseek-coder:6.7b').
        - api_key (str, optional): The API key for providers requiring authentication.

    Returns:
        JSON response with the answer or an error message.
    """
    data = request.json
    question = data.get('question', '').strip()
    user_id = data.get('user_id', 'default_user')
    file_name = data.get('file_name', 'Untitled')
    code = data.get('code', '').strip()
    provider = data.get('provider', 'ollama')
    model = data.get('model', 'deepseek-coder:6.7b')
    api_key = data.get('api_key')

    if not question:
        return jsonify({"error": "No question provided", "status": "failure"}), 400

    try:
        # Construct prompt, including code if provided
        if code:
            prompt = (
                f"File: {file_name}\nCode:\n```python\n{code}\n```\n\n"
                f"Question: {question}\n\n"
                "Answer directly and concisely. Provide full code solutions when needed. "
                "Keep response under 200 words unless absolutely necessary."
            )
        else:
            prompt = (
                f"Question: {question}\n\n"
                "Answer directly and concisely. Provide full code solutions when needed. "
                "Keep response under 200 words unless absolutely necessary."
            )

        # Get response from the provider
        answer = get_response(prompt, provider, model, api_key)

        # Format the response
        formatted_answer = format_response(answer)
        formatted_answer = format_code_blocks_with_black(formatted_answer)

        # Initialize or update conversation context
        if user_id not in conversation_context:
            conversation_context[user_id] = {"conversation": []}
        conversation_context[user_id]["conversation"].extend([
            {"role": "user", "message": question},
            {"role": "assistant", "message": formatted_answer}
        ])

        return jsonify({
            "answer": formatted_answer,
            "status": "success"
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to get response: {str(e)}"}), 500

@app.route('/conversation_history', methods=['GET'])
def get_conversation_history():
    """
    Retrieve the conversation history for a specific user.
    """
    user_id = request.args.get('user_id', 'default_user')
    context = conversation_context.get(user_id, {})
    if not context:
        return jsonify({"history": []})
    return jsonify({"history": context["conversation"]})

@app.route('/clear_conversation', methods=['POST'])
def clear_conversation():
    """
    Clear the conversation history for a specific user.
    """
    data = request.json
    user_id = data.get('user_id', 'default_user')
    if user_id in conversation_context:
        del conversation_context[user_id]
        return jsonify({"status": "success", "message": "Conversation history cleared"})
    return jsonify({"status": "failure", "message": "No conversation history found"}), 404

if __name__ == '__main__':  
    app.run(debug=True, host='0.0.0.0', port=5000)