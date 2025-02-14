Here’s an updated and polished version of your `README.md` file for the **LeetCode Chatbot** extension. It includes all the relevant sections, clear descriptions, and placeholders for images or animations.

---

# LeetCode Chatbot README

The **LeetCode Chatbot** is a VS Code extension designed to assist you with solving LeetCode problems directly within your editor. It provides intelligent suggestions, analyzes your code, and helps you improve your problem-solving skills without leaving VS Code.

![LeetCode Chatbot in Action](images/extension-demo.gif)  
*Example: The chatbot analyzing code and providing suggestions.*

---

## Features

1. **Code Analysis and Suggestions**  
   Get actionable feedback on your current code. The chatbot identifies potential issues and suggests improvements to optimize your solution.

   ![Code Suggestions](images/code-suggestions.png)

2. **Integration with Local AI Models**  
   The extension works seamlessly with local AI models (e.g., Ollama's DeepSeek) to provide real-time assistance.

3. **Lightweight and Easy to Use**  
   No need for external tools or cloud APIs—everything runs locally for privacy and efficiency.

4. **Customizable Prompts**  
   Tailor the chatbot's behavior to focus on debugging, optimization, or explanation.

> Tip: Check out the [demo animation](images/extension-demo.gif) to see how the extension works in action!

---

## Requirements

To use this extension, ensure you have the following installed:

1. **VS Code**  
   Download and install [Visual Studio Code](https://code.visualstudio.com/).

2. **Ollama**  
   Install [Ollama](https://ollama.ai/) and pull the required model (e.g., `deepseek-r1:latest`):
   ```bash
   ollama pull deepseek-r1:latest
   ```

3. **Python Backend**  
   The extension communicates with a Flask backend that interacts with Ollama. Ensure you have Python and Flask installed:
   ```bash
   pip install flask requests
   ```

---

## Extension Settings

This extension contributes the following settings:

- `leetcode-chatbot.model`: Specify the AI model to use (default: `deepseek-r1:latest`).
- `leetcode-chatbot.backendUrl`: URL of the Flask backend (default: `http://localhost:5000`).
- `leetcode-chatbot.enableDebugLogs`: Enable debug logging for troubleshooting (default: `false`).

You can configure these settings in your VS Code `settings.json` file:
```json
{
  "leetcode-chatbot.model": "deepseek-coder:6.7b",
  "leetcode-chatbot.backendUrl": "http://localhost:5000",
  "leetcode-chatbot.enableDebugLogs": true
}
```

---

## Known Issues

- **Performance**: Large files or complex prompts may take longer to process.
- **Model Compatibility**: Some models may not support specific coding tasks. Experiment with different models if needed.
- **Local Setup**: Ensure Ollama and the Flask backend are running before using the extension.

If you encounter any other issues, please report them on the [GitHub repository](https://github.com/your-repo/leetcode-chatbot/issues).

---

## Release Notes

### 1.0.0 (Initial Release)
- Added basic functionality for code analysis and suggestions.
- Integrated with Ollama for local AI model support.

### 1.0.1
- Fixed bugs related to backend communication.
- Improved error handling and logging.

### 1.1.0
- Added support for multiple AI models.
- Introduced customizable settings for model selection and backend URL.

---

## Following Extension Guidelines

Ensure that you've read through the official [VS Code Extension Guidelines](https://code.visualstudio.com/api/references/extension-guidelines) to maintain best practices for creating and maintaining your extension.

---

## Working with Markdown

You can author your README using Visual Studio Code. Here are some useful editor keyboard shortcuts:

- Split the editor (`Cmd+\` on macOS or `Ctrl+\` on Windows/Linux).
- Toggle preview (`Shift+Cmd+V` on macOS or `Shift+Ctrl+V` on Windows/Linux).
- Press `Ctrl+Space` (Windows, Linux, macOS) to see a list of Markdown snippets.

---

## For More Information

- [Visual Studio Code's Markdown Support](http://code.visualstudio.com/docs/languages/markdown)
- [Markdown Syntax Reference](https://help.github.com/articles/markdown-basics/)

---

**Enjoy using the LeetCode Chatbot!**  
If you find this extension helpful, consider giving it a ⭐️ on GitHub or sharing it with others. Contributions and feedback are always welcome!

---

### Notes for You:
1. Replace `images/extension-demo.gif`, `images/code-suggestions.png`, and other image paths with actual screenshots or animations of your extension in action.
2. Update the links to your GitHub repository or other resources as needed.
3. If you plan to publish the extension, include the marketplace link in the README.

Let me know if you'd like help with creating animations or further refining the README! 😊