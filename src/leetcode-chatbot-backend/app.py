from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
import re
import black  
import json
import openai
from typing import Optional

app = Flask(__name__)
CORS(app)

# Ollama API URL
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Set up logging
logging.basicConfig(level=logging.INFO)

# In-memory storage for conversation context
conversation_context = {}


def get_client(model: str):
    """Return the appropriate client handler based on the model"""
    if model == "openai-4o":
        return "openai"
    return "ollama"

def setup_openai_client(api_key: str) -> None:
    """Configure OpenAI client"""
    openai.api_key = api_key

def send_openai_completion(
    prompt: str,
    api_key: str,
    model: str = "gpt-4",  
    max_tokens: int = 1000,
    temperature: float = 0.7
) -> Optional[str]:
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
        # Set up the client
        setup_openai_client(api_key)
        
        # Get the correct OpenAI model identifier
        actual_model = get_openai_model(model)
        
        # Create the chat completion
        response = openai.chat.completions.create(
            model=actual_model,
            messages=[{
                "role": "user",
                "content": prompt
            }],
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
    """Analyze the provided Python code and suggest improvements."""
    data = request.json
    code = data.get('code', '').strip()
    user_id = data.get('user_id', 'default_user')
    file_name = data.get('file_name', 'Untitled')
    model = data.get('model', 'deepseek-coder:6.7b')
    client_type = get_client(model)
    api_key = data.get('api_key')
    
    if not code:
        return jsonify({"error": "No code provided", "status": "failure"}), 400

    try:
        if user_id not in conversation_context:
            conversation_context[user_id] = {
                "code": code,
                "file_name": file_name,
                "conversation": []
            }
        else:
            conversation_context[user_id]["code"] = code
            conversation_context[user_id]["file_name"] = file_name

        prompt = (
            "You are a world-class Python programmer. Your goal is to assist and guide a junior Python programmer in writing code for projects or coding tasks, explain programming concepts, and write code snippets/full code when needed.\n\n"
            "You will assist a junior programmer with their coding needs and questions, providing answers to coding-related questions, debugging code, or providing steps to solve coding tasks as well as code when asked.\n\n"
            "Please use the following rules when giving a response:\n"
            "1) Keep the response concise and clear, meaning around 200 words max (does not include words for code snippets or examples) or 5-6 bullet points at most.\n"
            "Do not include comments in the code snippets. Only provide the code without any explanations or comments.\n"
            "3) Be engaging and encourage human interaction, asking follow-up questions or asking for clarification when necessary.\n"
            "4) If the user provides incorrect or incomplete code, help them debug it or suggest steps to solve their issue.\n"
            "5) Always prioritize clarity, accuracy, and user understanding.\n"
            "6) Maintain a friendly and approachable tone to make the user feel comfortable asking questions.\n"
            "7) Encourage the user to follow best practices, such as writing modular code, using meaningful variable names, and adding comments for clarity.\n"
            "8) If the user asks a question unrelated to Python programming, politely guide them back to coding topics or let them know you specialize in Python.\n"
            f"Analyze the following Python code from file '{file_name}':\n\n"
            f"```python\n{code}\n```\n\n"
        )

        if client_type == "openai":
            if not api_key:
                return jsonify({"error": "OpenAI API key required"}), 401
            
            suggestion = send_openai_completion(
                prompt=prompt,
                api_key=api_key,
                model=model
            )
            
            if suggestion is None:
                return jsonify({"error": "Failed to get response from OpenAI"}), 500
                
        else:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(OLLAMA_API_URL, json=payload)
            response_data = response.json()
            suggestion = response_data.get("response", "").strip()

        formatted_suggestion = format_response(suggestion)
        formatted_suggestion = format_code_blocks_with_black(formatted_suggestion)

        conversation_context[user_id]["conversation"].append({
            "role": "assistant",
            "message": formatted_suggestion
        })

        return jsonify({
            "suggestion": formatted_suggestion,
            "status": "success"
        })

    except Exception as e:
        error_source = "OpenAI" if client_type == "openai" else "Ollama"
        return jsonify({
            "error": f"Failed to communicate with {error_source}",
            "details": str(e)
        }), 500

@app.route('/ask_question', methods=['POST'])
def ask_question():
    """Answer a user's question based on the provided code and conversation history."""
    data = request.json
    question = data.get('question', '').strip()
    user_id = data.get('user_id', 'default_user')
    file_name = data.get('file_name', 'Untitled')
    code = data.get('code', '').strip()
    model = data.get('model', 'deepseek-coder:6.7b')
    client_type = get_client(model)
    api_key = data.get('api_key')
    
    if not question:
        return jsonify({"error": "No question provided", "status": "failure"}), 400

    try:
        is_code_related = any(
            phrase in question.lower() for phrase in ["code", "function", "variable", "implementation"]
        )
        
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

        if client_type == "openai":
            if not api_key:
                return jsonify({"error": "OpenAI API key required"}), 401
            
            answer = send_openai_completion(
                prompt=prompt,
                api_key=api_key,
                model=model
            )
            
            if answer is None:
                return jsonify({"error": "Failed to get response from OpenAI"}), 500
        else:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(OLLAMA_API_URL, json=payload)
            response_data = response.json()
            answer = response_data.get("response", "").strip()

        formatted_answer = format_response(answer)
        formatted_answer = format_code_blocks_with_black(formatted_answer)

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

    except Exception as e:
        error_source = "OpenAI" if client_type == "openai" else "Ollama"
        return jsonify({
            "error": f"Failed to communicate with {error_source}",
            "details": str(e)
        }), 500

@app.route('/general_help', methods=['POST'])
def general_help():
    """Handle general coding questions with direct answers"""
    data = request.json
    question = data.get('question', '').strip()
    user_id = data.get('user_id', 'default_user')
    file_name = data.get('file_name', 'Untitled')
    code = data.get('code', '').strip()
    model = data.get('model', 'deepseek-coder:6.7b')
    client_type = get_client(model)
    api_key = data.get('api_key')
    
    if not question:
        return jsonify({"error": "No question provided", "status": "failure"}), 400

    try:
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

        if client_type == "openai":
            if not api_key:
                return jsonify({"error": "OpenAI API key required"}), 401
            
            answer = send_openai_completion(
                prompt=prompt,
                api_key=api_key,
                model=model
            )
            
            if answer is None:
                return jsonify({"error": "Failed to get response from OpenAI"}), 500
        else:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(OLLAMA_API_URL, json=payload)
            response_data = response.json()
            answer = response_data.get("response", "").strip()

        formatted_answer = format_response(answer)
        formatted_answer = format_code_blocks_with_black(formatted_answer)

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

    except Exception as e:
        error_source = "OpenAI" if client_type == "openai" else "Ollama"
        return jsonify({
            "error": f"Failed to communicate with {error_source}",
            "details": str(e)
        }), 500

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