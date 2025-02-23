import * as child_process from 'child_process';
import * as path from 'path';
import * as vscode from 'vscode';
import axios from 'axios';

export class FlaskServerManager {
    private serverProcess: child_process.ChildProcess | null = null;
    private readonly serverUrl = 'http://localhost:5000';
    private isStarting = false;

    constructor(private context: vscode.ExtensionContext) {}

    async startServer(): Promise<void> {
        if (this.serverProcess || this.isStarting) {
            return;
        }

        this.isStarting = true;

        try {
            // Try to check if server is already running
            try {
                await axios.get(`${this.serverUrl}/conversation_history?user_id=vscode_user`);
                console.log('Flask server is already running');
                this.isStarting = false;
                return;
            } catch (error) {
                // Only continue if the error is a connection error, not a 404 or other HTTP error
                if (!axios.isAxiosError(error) || error.code !== 'ECONNREFUSED') {
                    console.log('Server is running but returned error:', error);
                    this.isStarting = false;
                    return;
                }
                // Server is not running, continue with startup
            }

            // Get the path to the Python executable
            const pythonCommand = await this.getPythonCommand();
            
            // Get the path to the server script
            const serverScriptPath = path.join(this.context.extensionPath, 'src', 'server', 'app.py');
            console.log('Starting Flask server at:', serverScriptPath);

            // Spawn the Flask server process
            this.serverProcess = child_process.spawn(pythonCommand, [serverScriptPath], {
                detached: false,
                stdio: 'pipe'
            });

            // Handle server output
            this.serverProcess.stdout?.on('data', (data) => {
                console.log(`Flask server stdout: ${data}`);
            });

            this.serverProcess.stderr?.on('data', (data) => {
                const message = data.toString();
                // Only log errors, not startup messages
                if (!message.includes('Debugger is active') && 
                    !message.includes('Debugger PIN') && 
                    !message.includes('127.0.0.1')) {
                    console.error(`Flask server stderr: ${message}`);
                }
            });

            // Handle server process exit
            this.serverProcess.on('exit', (code, signal) => {
                console.log(`Flask server process exited with code ${code} and signal ${signal}`);
                this.serverProcess = null;
            });

            // Wait for server to start
            await this.waitForServer();
            console.log('Flask server started successfully');

        } catch (error) {
            console.error('Failed to start Flask server:', error);
            vscode.window.showErrorMessage('Failed to start Flask server. Please check the logs for details.');
            throw error;
        } finally {
            this.isStarting = false;
        }
    }

    private async getPythonCommand(): Promise<string> {
        // First try to get Python path from VSCode Python extension
        try {
            const extension = vscode.extensions.getExtension('ms-python.python');
            if (extension) {
                await extension.activate();
                const pythonPath = await vscode.commands.executeCommand<string>('python.interpreterPath');
                if (pythonPath && typeof pythonPath === 'string') {
                    return pythonPath;
                }
            }
        } catch (error) {
            console.warn('Failed to get Python path from Python extension:', error);
        }

        // Fallback to system Python
        return process.platform === 'win32' ? 'python' : 'python3';
    }

    private async waitForServer(timeout: number = 30000): Promise<void> {
        const startTime = Date.now();
        let lastError: Error | null = null;
        
        while (Date.now() - startTime < timeout) {
            try {
                // Check the conversation_history endpoint instead of root
                await axios.get(`${this.serverUrl}/conversation_history?user_id=vscode_user`);
                return;
            } catch (error) {
                lastError = error as Error;
                // If we get a 404 or other HTTP error (not connection refused), the server is actually running
                if (axios.isAxiosError(error) && error.response) {
                    if (error.response.status !== 404) {
                        return;
                    }
                }
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }
        
        if (lastError) {
            console.error('Last error while waiting for server:', lastError);
        }
        throw new Error('Server failed to start within timeout period');
    }

    async stopServer(): Promise<void> {
        if (this.serverProcess) {
            // Kill the process and all its children
            if (process.platform === 'win32') {
                child_process.exec(`taskkill /PID ${this.serverProcess.pid} /T /F`);
            } else {
                process.kill(-this.serverProcess.pid!, 'SIGKILL');
            }
            this.serverProcess = null;
        }
    }
}