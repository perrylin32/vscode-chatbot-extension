import * as vscode from 'vscode';
import axios from 'axios';
import * as path from 'path';
import * as fs from 'fs';
import { FlaskServerManager } from './server';

const API_URL = 'http://localhost:5000';

interface ChatMessage {
    role: string;
    message: string;
}

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

export async function activate(context: vscode.ExtensionContext) {
    console.log('LeetCode Chatbot is now active');

    const serverManager = new FlaskServerManager(context);
    try {
        await serverManager.startServer();
    } catch (error) {
        vscode.window.showErrorMessage('Failed to start Flask server. The extension may not work properly.');
        console.error('Failed to start Flask server:', error);
    }

    // Register the server manager to be stopped when the extension is deactivated
    context.subscriptions.push({
        dispose: () => {
            serverManager.stopServer().catch(error => {
                console.error('Failed to stop Flask server:', error);
            });
        }
    });

    const provider = new ChatWebviewProvider(context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('chatbot-panel', provider)
    );

    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(light-bulb) Code Analysis';
    statusBarItem.command = 'leetcode-chatbot.analyzeCode';
    statusBarItem.show();

    // Listen for active editor changes
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) {
                provider.updateContext(
                    editor.document.getText(),
                    editor.document.fileName
                );
            }
        })
    );

    // Listen for text document changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument(event => {
            const editor = vscode.window.activeTextEditor;
            if (editor && event.document === editor.document) {
                provider.updateContext(
                    editor.document.getText(),
                    editor.document.fileName
                );
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('leetcode-chatbot.analyzeCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('Please open a file to use the LeetCode Chatbot.');
                return;
            }
            const code = editor.document.getText();
            const fileName = editor.document.fileName;
            try {
                // Get current model and API key
                const currentModel = context.workspaceState.get('currentModel') || 'deepseek-coder:6.7b';
                let apiKey: string | undefined;
                
                if (currentModel === 'openai-4o') {
                    apiKey = await context.secrets.get('openai-api-key');
                    if (!apiKey) {
                        vscode.window.showErrorMessage('OpenAI API key required. Use "Update OpenAI API Key" command first.');
                        return;
                    }
                }
    
                await axios.post(`${API_URL}/get_suggestions`, {
                    code: code,
                    user_id: 'vscode_user',
                    file_name: fileName,
                    model: currentModel,
                    api_key: apiKey
                });
                
                provider.updateContext(code, fileName);
                vscode.commands.executeCommand('chatbot-panel.focus');
            } catch (error: any) {
                vscode.window.showErrorMessage(`Error analyzing code: ${error.message}`);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('leetcode-chatbot.updateApiKey', async () => {
            console.log('Update OpenAI Key command triggered');
            const input = await vscode.window.showInputBox({
                prompt: 'Enter OpenAI API Key',
                password: true
            });
            
            if (input) {
                await context.secrets.store('openai-api-key', input);
                vscode.window.showInformationMessage('OpenAI API key updated successfully');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('leetcode-chatbot.updateGroqApiKey', async () => {
            const input = await vscode.window.showInputBox({
                prompt: 'Enter Groq API Key',
                password: true
            });
            if (input) {
                await context.secrets.store('groq-api-key', input);
                vscode.window.showInformationMessage('Groq API key updated successfully');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('leetcode-chatbot.setCustomModel', async () => {
            const input = await vscode.window.showInputBox({
                prompt: 'Enter Groq model name (e.g., llama-3.1-8b)',
                placeHolder: 'e.g., llama-3.1-8b'
            });
            if (input) {
                await context.workspaceState.update('customModel', input);
                vscode.window.showInformationMessage('Custom model set successfully');
                provider.refreshModelDisplay('custom-llm');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('leetcode-chatbot.setOllamaModel', async () => {
            const input = await vscode.window.showInputBox({
                prompt: 'Enter Ollama model name (e.g., llama2:7b). Ensure the model is installed locally via Ollama.',
                placeHolder: 'e.g., llama2:7b'
            });
            if (input) {
                await context.workspaceState.update('ollamaCustomModel', input);
                vscode.window.showInformationMessage('Ollama custom model set successfully');
                provider.refreshModelDisplay('ollama-custom');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('leetcode-chatbot.logCurrentModel', () => {
            const currentModel = context.workspaceState.get('currentModel');
            console.log('Current model:', currentModel);
        })
    );
}

class ChatWebviewProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private _context: vscode.ExtensionContext;
    private _currentCode = '';
    private _currentFileName = '';
    private _currentModel = 'deepseek-coder:6.7b';

    constructor(context: vscode.ExtensionContext) {
        this._context = context;
        this._currentModel = context.workspaceState.get('currentModel') || 'deepseek-coder:6.7b';
    }

    public updateContext(code: string, fileName: string) {
        this._currentCode = code;
        this._currentFileName = fileName;

        if (this._view) {
            this._view.webview.postMessage({
                command: 'updateContext',
                file: fileName
            });
        }
    }

    public resolveWebviewView(webviewView: vscode.WebviewView) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._context.extensionUri]
        };

        webviewView.webview.html = this._getWebviewContent();

        webviewView.webview.onDidReceiveMessage(async message => {
            switch (message.command) {
                case 'modelSelected':
                    await this._handleModelSelection(message.model);
                    break;
                case 'askQuestion':
                    await this._handleQuestion(message.text, message.mode);
                    break;
                case 'loadHistory':
                    await this._loadHistory();
                    break;
                case 'newChat':
                    try {
                        await axios.post(`${API_URL}/clear_conversation`, {
                            user_id: 'vscode_user'
                        });
                        this._updateWebview([], true);
                    } catch (error: any) {
                        vscode.window.showErrorMessage(`Error clearing chat history: ${error.message}`);
                    }
                    break;
            }
        });

        webviewView.webview.postMessage({
            command: 'updateModel',
            model: this._currentModel,
            displayName: this._getModelDisplayName(this._currentModel)
        });

        this._loadHistory();
    }

    public refreshModelDisplay(modelType: 'custom-llm' | 'ollama-custom') {
        const displayName = this._getModelDisplayName(modelType);
        if (this._view) {
            this._view.webview.postMessage({
                command: 'updateOptionDisplay',
                model: modelType,
                displayName: displayName
            });
        }
    }

    private async _loadHistory() {
        try {
            const response = await axios.get(`${API_URL}/conversation_history?user_id=vscode_user`);
            this._updateWebview(response.data.history || []);
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }

    private _getModelDisplayName(model: string): string {
        if (model === 'custom-llm') {
            const customModel = this._context.workspaceState.get('customModel');
            return customModel ? `Custom LLM (${customModel})` : 'Custom LLM';
        } else if (model === 'ollama-custom') {
            const ollamaModel = this._context.workspaceState.get('ollamaCustomModel');
            return ollamaModel ? `Ollama Custom (${ollamaModel})` : 'Ollama Custom';
        }
        return model;
    }

    private async _handleModelSelection(model: string) {
        this._currentModel = model;
        await this._context.workspaceState.update('currentModel', model);

        const displayName = this._getModelDisplayName(model);

        if (this._view) {
            this._view.webview.postMessage({
                command: 'updateModel',
                model: model,
                displayName: displayName
            });
        }
    
        if (model === 'openai-4o') {
            const apiKey = await this._context.secrets.get('openai-api-key');
            if (!apiKey) {
                const input = await vscode.window.showInputBox({
                    prompt: 'Enter OpenAI API Key (will be stored securely)',
                    password: true,
                    ignoreFocusOut: true
                });
                if (input) {
                    await this._context.secrets.store('openai-api-key', input);
                } else {
                    this._currentModel = 'deepseek-coder:6.7b';
                    await this._context.workspaceState.update('currentModel', this._currentModel);
                    if (this._view) {
                        this._view.webview.postMessage({
                            command: 'updateModel',
                            model: this._currentModel
                        });
                    }
                }
            }
        } else if (model === 'custom-llm') {
            const groqApiKey = await this._context.secrets.get('groq-api-key');
            const customModel = this._context.workspaceState.get('customModel');
            if (!groqApiKey || !customModel) {
                vscode.window.showErrorMessage('Groq API key and model name are required. Run "LeetCode Chatbot: Update Groq API Key" and "LeetCode Chatbot: Set Custom Model" from the command palette.');
                this._currentModel = 'deepseek-coder:6.7b';
                await this._context.workspaceState.update('currentModel', this._currentModel);
                if (this._view) {
                    this._view.webview.postMessage({
                        command: 'updateModel',
                        model: this._currentModel
                    });
                }
            }
        } else if (model === 'ollama-custom') {
            const ollamaModel = this._context.workspaceState.get('ollamaCustomModel');
            if (!ollamaModel) {
                vscode.window.showErrorMessage('Ollama custom model not set. Run "LeetCode Chatbot: Set Ollama Model" from the command palette.');
                this._currentModel = 'deepseek-coder:6.7b';
                await this._context.workspaceState.update('currentModel', this._currentModel);
                if (this._view) {
                    this._view.webview.postMessage({
                        command: 'updateModel',
                        model: this._currentModel
                    });
                }
            }
        }
    }

    private async _handleQuestion(question: string, mode: string) {
        try {
            const editor = vscode.window.activeTextEditor;
            const currentCode = editor?.document.getText() || this._currentCode;
            const currentFile = editor?.document.fileName || this._currentFileName;
            const endpoint = mode === 'leetcode' ? 'ask_question' : 'general_help';
    
            let provider;
            let actualModel;
            let apiKey;

            if (this._currentModel === 'openai-4o') {
                provider = 'openai';
                actualModel = 'gpt-4';
                apiKey = await this._context.secrets.get('openai-api-key');
                if (!apiKey) { throw new Error('No API key found for OpenAI'); }
            } else if (this._currentModel === 'custom-llm') {
                provider = 'groq';
                actualModel = this._context.workspaceState.get('customModel');
                if (!actualModel) { throw new Error('Custom model not set. Run "LeetCode Chatbot: Set Custom Model"'); }
                apiKey = await this._context.secrets.get('groq-api-key');
                if (!apiKey) { throw new Error('No API key found for Groq'); }
            } else if (this._currentModel === 'ollama-custom') {
                provider = 'ollama';
                actualModel = this._context.workspaceState.get('ollamaCustomModel');
                if (!actualModel) { throw new Error('Ollama custom model not set. Run "LeetCode Chatbot: Set Ollama Model"'); }
                apiKey = undefined;
            } else {
                provider = 'ollama';
                actualModel = this._currentModel;
                apiKey = undefined;
            }

            console.log('Provider:', provider, 'Model:', actualModel, 'API Key:', apiKey ? 'Set' : 'Not set');
    
            const response = await axios.post(`${API_URL}/${endpoint}`, {
                question: question,
                user_id: 'vscode_user',
                file_name: currentFile,
                code: currentCode,
                provider: provider,
                model: actualModel,
                api_key: apiKey
            });
    
            if (!response.data?.answer) {
                throw new Error('Invalid response from server');
            }
    
            this._updateWebview([
                { role: 'user', message: question },
                { role: 'assistant', message: response.data.answer }
            ]);
        } catch (error: any) {
            vscode.window.showErrorMessage(`Error: ${error.message}`);
            this._updateWebview([
                { role: 'assistant', message: `Error: ${error.message}` }
            ]);
        }
    }

    private _updateWebview(messages: ChatMessage[], clear = false) {
        if (this._view) {
            this._view.webview.postMessage({
                command: 'appendMessages',
                messages: messages.map(msg => ({
                    role: msg.role,
                    message: this._formatCodeBlocks(msg.message)
                })),
                clear: clear
            });
        }
    }

    private _formatCodeBlocks(message: string): string {
        const codeBlockRegex = /(```[\s\S]*?```)/g;
        return message.replace(codeBlockRegex, (match) => {
            const codeContent = match.replace(/```/g, "").trim();
            const uniqueId = `code-block-${Math.random().toString(36).substr(2, 9)}`;
            return `
            <div style="position: relative;">
            <pre><code id="${uniqueId}">${codeContent}</code></pre>
            <button 
                style="position: absolute; top: 5px; right: 5px; padding: 5px 10px; background-color: #007acc; color: white; border: none; border-radius: 4px; cursor: pointer;"
                onclick="navigator.clipboard.writeText(document.getElementById('${uniqueId}').innerText).then(() => alert('Copied to clipboard!'), () => alert('Failed to copy!'));">
                Copy
            </button>
            </div>`;
        });
    }

    private _getWebviewContent() {
        const webview = this._view?.webview;
        if (!webview) {
            return '';
        }

        // Update path to include 'src' directory
        const htmlPath = path.join(this._context.extensionPath, 'src', 'webview', 'index.html');
        let htmlContent: string;

        try {
            // Read the HTML file
            htmlContent = fs.readFileSync(htmlPath, 'utf8');
        } catch (error) {
            console.error(`Failed to read HTML file: ${error}`);
            return `<html><body>Failed to load webview content: ${error}</body></html>`;
        }

        // Update resource loading to include 'src' directory
        const webviewUri = (fileName: string) => {
            return webview.asWebviewUri(
                vscode.Uri.file(
                    path.join(this._context.extensionPath, 'src', 'webview', fileName)
                )
            );
        };

        // Configure webview content security policy
        const nonce = getNonce();
        const csp = `
            default-src 'none';
            style-src ${webview.cspSource} 'unsafe-inline';
            script-src 'nonce-${nonce}' 'unsafe-eval';
            font-src ${webview.cspSource};
            img-src ${webview.cspSource} https:;
        `;

        // Replace placeholders in the HTML content
        htmlContent = htmlContent
            .replace('${nonce}', nonce)
            .replace('${webview.cspSource}', webview.cspSource)
            .replace(/<script/g, `<script nonce="${nonce}"`);

        // Add CSP meta tag
        htmlContent = htmlContent.replace(
            '</head>',
            `<meta http-equiv="Content-Security-Policy" content="${csp}"></head>`
        );

        return htmlContent;
    }
}

export function deactivate() {}