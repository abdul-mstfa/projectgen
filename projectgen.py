#!/usr/bin/env python3
import os
import sys
import argparse
import json
import subprocess
import readline
import textwrap
import glob
from pathlib import Path
import openai

class ProjectAssistant:
    def __init__(self, api_key=None, projects_dir=None, model="gpt-4o"):
        # Set up API key from env or argument
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("No API key provided. Set OPENAI_API_KEY environment variable or pass with --api-key")
        
        # Set up client and model
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        
        # Set up projects directory
        self.projects_dir = Path(projects_dir or os.environ.get("PROJECT_GEN_DIR", os.path.expanduser("~/projects")))
        self.projects_dir.mkdir(exist_ok=True, parents=True)
        
        # Current project attributes
        self.current_project_path = None
        self.current_project_name = None
        self.current_project_technologies = []
        
        # Chat history for interactive mode
        self.messages = []
    
    def build_project(self, prompt):
        """Build a new project based on the prompt"""
        # Generate project plan
        project_plan = self._generate_project_plan(prompt)
        
        # Print project summary
        print("\n" + "="*50)
        print(f"Project: {project_plan['project_name']}")
        print(f"Description: {project_plan['description']}")
        print(f"Technologies: {', '.join(project_plan.get('technologies', []))}")
        print("="*50 + "\n")
        
        # Create the project
        project_path = self._create_project(project_plan)
        
        if project_path:
            # Store current project details
            self.current_project_path = project_path
            self.current_project_name = project_plan['project_name']
            self.current_project_technologies = project_plan.get('technologies', [])
            
            print(f"\nProject created at: {project_path}")
            
            # Initialize git repository
            if self._initialize_git(project_path):
                print("Git repository initialized")
            
            print("\nNext steps:")
            print(f"1. cd {project_path}")
            
            # Suggest next steps based on technologies
            if "python" in project_plan.get('technologies', []):
                print("2. python -m venv venv")
                print("3. source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
                print("4. pip install -r requirements.txt")
            elif "node" in project_plan.get('technologies', []) or "javascript" in project_plan.get('technologies', []):
                print("2. npm install")
                
            return True
        
        return False
    
    def _generate_project_plan(self, prompt):
        """Generate a project plan based on the user prompt"""
        system_prompt = """
        You are a software architect tasked with creating a detailed project structure.
        Based on the user's project idea, generate a JSON structure that includes:
        1. A project name (short, descriptive, kebab-case)
        2. A brief project description
        3. A complete file structure with directories and files
        4. Technologies and dependencies to use
        5. For each file, provide the full file content with complete implementation code
        
        Make sure you implement fully working code, not just placeholders.
        The code should be complete, functional, and follow best practices.

        Return ONLY valid JSON with this structure:
        {
          "project_name": "example-project",
          "description": "Brief description of the project",
          "technologies": ["python", "flask", "etc"],
          "dependencies": ["requests", "flask", "etc"],
          "structure": [
            {
              "path": "src/main.py",
              "type": "file",
              "content": "# Full implementation code here\\n..."
            },
            {
              "path": "src/utils",
              "type": "directory"
            },
            ...more files and directories...
          ]
        }
        """
        
        print("Generating project plan...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a project structure for: {prompt}"}
            ],
            response_format={"type": "json_object"},
            max_tokens=4096
        )
        
        # Extract the JSON from the response
        try:
            content = response.choices[0].message.content
            project_plan = json.loads(content)
            return project_plan
        except Exception as e:
            print(f"Error parsing project plan: {e}")
            sys.exit(1)
    
    def _create_project(self, project_plan):
        """Create the project files and directories"""
        project_name = project_plan['project_name']
        project_path = self.projects_dir / project_name
        
        # Create project directory
        if project_path.exists():
            confirm = input(f"Project directory {project_path} already exists. Overwrite? (y/n): ")
            if confirm.lower() != 'y':
                print("Aborted.")
                return None
            
        project_path.mkdir(exist_ok=True, parents=True)
        
        # Create README.md with project description
        with open(project_path / "README.md", "w") as f:
            f.write(f"# {project_name}\n\n{project_plan['description']}\n\n")
            f.write("## Technologies\n\n")
            for tech in project_plan.get('technologies', []):
                f.write(f"- {tech}\n")
            f.write("\n## Setup\n\n")
            
            # Add setup instructions based on technologies
            if "python" in project_plan.get('technologies', []):
                f.write("```bash\n")
                f.write("# Create virtual environment\n")
                f.write("python -m venv venv\n")
                f.write("source venv/bin/activate  # On Windows: venv\\Scripts\\activate\n\n")
                f.write("# Install dependencies\n")
                f.write("pip install -r requirements.txt\n")
                f.write("```\n")
        
        # Create requirements.txt if Python is used
        if "python" in project_plan.get('technologies', []):
            with open(project_path / "requirements.txt", "w") as f:
                for dep in project_plan.get('dependencies', []):
                    f.write(f"{dep}\n")
        
        # Create all files and directories
        for item in project_plan['structure']:
            full_path = project_path / item['path']
            
            if item['type'] == 'directory':
                full_path.mkdir(exist_ok=True, parents=True)
            elif item['type'] == 'file':
                # Ensure parent directory exists
                full_path.parent.mkdir(exist_ok=True, parents=True)
                
                # Write file content
                with open(full_path, "w") as f:
                    f.write(item.get('content', ''))
        
        return project_path
    
    def _initialize_git(self, project_path):
        """Initialize git repository"""
        try:
            subprocess.run(["git", "init"], cwd=project_path, check=True)
            
            # Create .gitignore
            gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/
.env
.venv
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/

# Node.js
node_modules/
npm-debug.log
yarn-error.log
yarn-debug.log
package-lock.json

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
            """
            
            with open(project_path / ".gitignore", "w") as f:
                f.write(gitignore_content)
            
            subprocess.run(["git", "add", "."], cwd=project_path, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit: Project scaffolding"], cwd=project_path, check=True)
            
            return True
        except Exception as e:
            print(f"Warning: Failed to initialize git repository: {e}")
            return False
    
    def chat_mode(self, project_path=None):
        """Start an interactive chat session about the project with file editing capabilities"""
        # If project_path is provided, use it; otherwise use the current project
        if project_path:
            # Try to load project information
            if not self._load_project_info(project_path):
                print(f"Could not load project information from {project_path}")
                return False
        elif not self.current_project_path:
            # No current project and no path provided
            print("No project selected. Please use @build first or specify a project path.")
            return False
        
        # Initialize chat history
        tech_string = ', '.join(self.current_project_technologies)
        
        # Generate project file listing for context
        file_list = self._get_project_files()
        file_listing = "\n".join(file_list)
        
        self.messages = [
            {"role": "system", "content": f"""You are a helpful AI coding assistant for a project called '{self.current_project_name}' 
            using {tech_string}. The project is located at {self.current_project_path}.
            
            Project files:
            {file_listing}
            
            The user may report issues or request changes to the code. You can suggest solutions and DIRECTLY MODIFY FILES 
            when instructed to do so.
            
            When modifying files:
            1. Be precise about which file you're editing
            2. If creating a new file, mention that explicitly
            3. Make only the necessary changes to fix the issue
            4. Explain what changes you made and why
            
            When the user asks you to edit a file, respond in this format:
            1. Brief explanation of what changes you're making
            2. Start the file edit with "FILE_EDIT: [filepath]"
            3. Include the COMPLETE new file content, not just the changes
            4. End with "END_FILE_EDIT"
            5. Explain the changes and what they'll fix
            
            Keep your answers concise but complete. Assume the user is working on macOS in the terminal.
            """},
            {"role": "assistant", "content": f"I'm your coding assistant for the {self.current_project_name} project at {self.current_project_path}. I can help you with code issues and make direct changes to your files. What would you like to discuss or modify?"}
        ]
        
        # Print welcome message
        print("\n" + "="*50)
        print(f"Interactive chat for {self.current_project_name} at {self.current_project_path}")
        print("Type '@exit' to quit, '@files' to list files, '@read [filepath]' to read a file")
        print("="*50 + "\n")
        
        print(self.messages[-1]["content"])
        
        # Main chat loop
        while True:
            # Get user input
            try:
                user_input = input("\n> ")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting chat...")
                break
            
            # Check for special commands
            if user_input.lower() in ['@exit', '@quit', '@bye']:
                print("Exiting chat...")
                break
            elif user_input.lower() == '@files':
                self._list_project_files()
                continue
            elif user_input.lower().startswith('@read '):
                filepath = user_input[6:].strip()
                self._read_file(filepath)
                continue
            elif user_input.lower() == '@help':
                self._show_help()
                continue
            
            # Add user input to messages
            self.messages.append({"role": "user", "content": user_input})
            
            # Get response from OpenAI
            print("\nThinking...")
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    max_tokens=4096
                )
                
                # Get response content
                assistant_response = response.choices[0].message.content
                
                # Check for file edits in the response
                edited_response = self._process_file_edits(assistant_response)
                
                # Add assistant response to messages
                self.messages.append({"role": "assistant", "content": assistant_response})
                
                # Print response with nice formatting
                formatted_response = self._format_terminal_text(edited_response)
                print(formatted_response)
                
            except Exception as e:
                print(f"Error getting response: {e}")
    
    def _load_project_info(self, project_path):
        """Load information about an existing project"""
        project_path = Path(project_path).resolve()
        
        if not project_path.exists() or not project_path.is_dir():
            return False
        
        # Set the current project path
        self.current_project_path = project_path
        self.current_project_name = project_path.name
        
        # Try to determine technologies
        self.current_project_technologies = []
        
        # Check for package.json (Node.js)
        if (project_path / "package.json").exists():
            self.current_project_technologies.append("javascript")
            self.current_project_technologies.append("node")
            
            # Try to read dependencies from package.json
            try:
                with open(project_path / "package.json") as f:
                    package_data = json.load(f)
                    if "dependencies" in package_data:
                        for dep in package_data["dependencies"]:
                            if dep not in self.current_project_technologies:
                                self.current_project_technologies.append(dep)
            except:
                pass
        
        # Check for requirements.txt (Python)
        if (project_path / "requirements.txt").exists():
            self.current_project_technologies.append("python")
            
            # Try to read dependencies from requirements.txt
            try:
                with open(project_path / "requirements.txt") as f:
                    for line in f:
                        dep = line.strip().split("==")[0].split(">=")[0]
                        if dep and dep not in self.current_project_technologies:
                            self.current_project_technologies.append(dep)
            except:
                pass
        
        # If we couldn't determine technologies, set a generic value
        if not self.current_project_technologies:
            # Check for file extensions to guess language
            py_files = list(project_path.glob("**/*.py"))
            js_files = list(project_path.glob("**/*.js"))
            
            if py_files:
                self.current_project_technologies.append("python")
            if js_files:
                self.current_project_technologies.append("javascript")
                
            if not self.current_project_technologies:
                self.current_project_technologies = ["unknown"]
        
        return True
    
    def _get_project_files(self):
        """Get a list of files in the project"""
        file_list = []
        
        for root, _, files in os.walk(self.current_project_path):
            for file in files:
                if file.startswith('.'):
                    continue  # Skip hidden files
                
                rel_path = os.path.relpath(os.path.join(root, file), self.current_project_path)
                file_list.append(rel_path)
        
        return file_list
    
    def _list_project_files(self):
        """Print a list of files in the project"""
        print("\n===== Project Files =====")
        for file in self._get_project_files():
            print(file)
        print("=======================\n")
    
    def _read_file(self, filepath):
        """Print the contents of a file"""
        try:
            full_path = self.current_project_path / filepath
            with open(full_path, 'r') as f:
                content = f.read()
            
            print(f"\n===== File: {filepath} =====")
            print(content)
            print("=======================\n")
        except Exception as e:
            print(f"Error reading file: {e}")
    
    def _process_file_edits(self, response):
        """Process file edits in the response"""
        edited_response = response
        
        # Find all file edits
        file_edit_start = response.find("FILE_EDIT: ")
        while file_edit_start != -1:
            # Find the file path
            file_path_end = response.find("\n", file_edit_start)
            if file_path_end == -1:
                break
                
            file_path_str = response[file_edit_start + 11:file_path_end].strip()
            
            # Find the end of the file edit
            file_edit_end = response.find("END_FILE_EDIT", file_path_end)
            if file_edit_end == -1:
                break
                
            # Extract the file content
            file_content = response[file_path_end + 1:file_edit_end].strip()
            
            # Apply the file edit
            full_path = self.current_project_path / file_path_str
            
            try:
                # Ensure the directory exists
                full_path.parent.mkdir(exist_ok=True, parents=True)
                
                # Write the file
                with open(full_path, 'w') as f:
                    f.write(file_content)
                
                # Format the edited response
                edited_response = edited_response.replace(
                    response[file_edit_start:file_edit_end + 14],
                    f"🔄 APPLIED CHANGES TO: {file_path_str} 🔄"
                )
                
                # Commit the changes if git is initialized
                try:
                    subprocess.run(["git", "add", file_path_str], cwd=self.current_project_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["git", "commit", "-m", f"Update {file_path_str}"], cwd=self.current_project_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass  # Ignore git errors
                
            except Exception as e:
                # Format the edited response with error
                edited_response = edited_response.replace(
                    response[file_edit_start:file_edit_end + 14],
                    f"❌ ERROR UPDATING {file_path_str}: {str(e)} ❌"
                )
            
            # Find the next file edit
            file_edit_start = response.find("FILE_EDIT: ", file_edit_end)
        
        return edited_response
    
    def _format_terminal_text(self, text):
        """Format text for terminal display with proper wrapping and code block handling"""
        result = []
        in_code_block = False
        code_lines = []
        
        for line in text.split('\n'):
            # Handle code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    # Start of code block - get the language if specified
                    lang = line.strip()[3:].strip()
                    result.append(f"\n\033[1m# {lang} code:\033[0m" if lang else "\n\033[1m# Code:\033[0m")
                else:
                    # End of code block - append collected code
                    result.append("\n" + "\n".join(code_lines))
                    code_lines = []
                    result.append("\033[1m# End of code\033[0m\n")
                continue
            
            if in_code_block:
                # Collect code lines
                code_lines.append(line)
            else:
                # Wrap normal text for better readability
                wrapped_text = textwrap.fill(line, width=80) if line.strip() else line
                result.append(wrapped_text)
        
        return "\n".join(result)
    
    def _show_help(self):
        """Show help for the chat mode"""
        print("\n===== Chat Mode Commands =====")
        print("@build [prompt] - Build a new project")
        print("@chat [project_path] - Start chat mode for a project")
        print("@exit - Exit the current mode")
        print("@files - List files in the current project")
        print("@read [filepath] - Read the contents of a file")
        print("@help - Show this help message")
        print("============================\n")

def main():
    parser = argparse.ArgumentParser(description="AI Project Assistant")
    parser.add_argument("command", nargs="?", choices=["build", "chat"], help="Command to run")
    parser.add_argument("prompt", nargs="?", help="Project idea prompt or project path")
    parser.add_argument("--api-key", help="OpenAI API key")
    parser.add_argument("--projects-dir", help="Directory to create projects in")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")
    
    args = parser.parse_args()
    
    try:
        assistant = ProjectAssistant(api_key=args.api_key, projects_dir=args.projects_dir, model=args.model)
        
        # Interactive terminal mode
        if not args.command:
            print("\n===== AI Project Assistant =====")
            print("Type '@build [prompt]' to create a new project")
            print("Type '@chat [project_path]' to chat about an existing project")
            print("Type '@exit' to quit")
            print("==============================\n")
            
            while True:
                try:
                    user_input = input("> ")
                except (KeyboardInterrupt, EOFError):
                    print("\nExiting...")
                    break
                
                if user_input.lower() in ['@exit', '@quit', '@bye']:
                    print("Exiting...")
                    break
                elif user_input.lower().startswith('@build '):
                    prompt = user_input[7:].strip()
                    if prompt:
                        assistant.build_project(prompt)
                    else:
                        print("Please provide a project idea")
                elif user_input.lower().startswith('@chat '):
                    project_path = user_input[6:].strip()
                    if project_path:
                        assistant.chat_mode(project_path)
                    else:
                        assistant.chat_mode()
                elif user_input.lower() == '@help':
                    assistant._show_help()
                else:
                    print("Unknown command. Type '@help' for a list of commands.")
        
        # Command line mode
        elif args.command == "build":
            if not args.prompt:
                prompt = input("Describe your project idea: ")
            else:
                prompt = args.prompt
                
            assistant.build_project(prompt)
            
        elif args.command == "chat":
            if args.prompt:
                assistant.chat_mode(args.prompt)
            else:
                assistant.chat_mode()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()