# VS Code Chatbot Extension

A helpful VS Code extension that provides AI-powered coding assistance directly within your editor. The chatbot helps with both LeetCode problems and general coding questions, leveraging multiple AI models for comprehensive support.

## Features

1. **Multi-Model AI Support**
   - Support for multiple AI models:
     - DeepSeek Coder (6.7B)
     - DeepSeek R1
     - OpenAI GPT-4
     - Custom LLM options

2. **Dual-Mode Operation**
   - LeetCode Mode: Specialized assistance for solving LeetCode problems
   - General Coding Mode: Broader programming support and code analysis

3. **Smart Code Analysis**
   - Code analysis and explanations on request
   - Human-readable responses with automatically formatted code examples
   - Contextual understanding of your current file

4. **Interactive Chat Interface**
   - Clean, VS Code-native design
   - Conversation history management
   - Code block highlighting with copy functionality
   - Markdown support for better readability

5. **Secure API Key Management**
   - Secure storage of OpenAI API keys
   - Easy key management through VS Code's secure storage

## Installation

### VS Code Marketplace
1. Open VS Code
2. Go to the Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X`)
3. Search for "LeetCode Chatbot"
4. Click Install
5. Or visit the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=kebinLin.leetcode-chatbot)

### Requirements

1. **Python Dependencies**
   ```bash
   pip install Flask==3.1.0 Flask-Cors==5.0.0 requests==2.32.3 black==25.1.0 openai==1.63.0 typing-extensions==4.12.2
   ```

2. **Ollama** (Required for DeepSeek models)
   - Install [Ollama](https://ollama.ai/)
   - Pull the required models:
     ```bash
     ollama pull deepseek-coder:6.7b
     ollama pull deepseek-r1
     ```

### Backend Setup

Start the Flask backend:
```bash
python app.py
```

## Extension Settings

This extension contributes the following settings:

- `leetcode-chatbot.model`: Select the AI model (default: `deepseek-coder:6.7b`)
- `leetcode-chatbot.backendUrl`: Backend URL (default: `http://localhost:5000`)
- `leetcode-chatbot.enableDebugLogs`: Enable debugging (default: `false`)

Example configuration in `settings.json`:
```json
{
  "leetcode-chatbot.model": "deepseek-coder:6.7b",
  "leetcode-chatbot.backendUrl": "http://localhost:5000",
  "leetcode-chatbot.enableDebugLogs": true
}
```

## Usage

1. Open the chatbot panel using:
   - Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
   - Search for "LeetCode Chatbot"
   - Or click the lightbulb icon in the status bar

2. Select your preferred mode:
   - Toggle between "General Coding" and "LeetCode Help"
   - Choose your AI model from the dropdown

3. Start chatting:
   - Ask questions about your code
   - Get help with LeetCode problems
   - Receive explanations and examples

## Features in Detail

### Chat Interface
- Code block syntax highlighting
- Copy-to-clipboard functionality
- Conversation history management
- New chat creation
- Automatically formatted code examples in responses

### Model Selection
- Easy switching between AI models
- Secure API key management for OpenAI
- Support for custom LLM configurations

## Known Issues

- The backend server must be running for the extension to work
- Large files may experience slight processing delays
- OpenAI models require a valid API key
- Deepseek R1 may take a while to produce a response

## License

[MIT License](LICENSE)

## Release Notes

### 1.0.0
- Initial release
- Basic chat functionality
- Support for DeepSeek models

### 1.1.0
- Added OpenAI GPT-4 support
- Implemented secure API key storage
- Added mode switching (LeetCode/General)

### 1.2.0
- Enhanced response formatting
- Improved chat interface
- Added conversation history management

---

## Support

For issues, feature requests, or contributions, please visit the [GitHub repository](https://github.com/perrylin32/vscode-chatbot-extension).

---

**Enjoy coding with LeetCode Chatbot!** 🚀

Remember to star ⭐ the repository if you find it helpful!