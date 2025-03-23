#!/home/fg/miniconda3/envs/llm/bin/python

import os, signal, sys, select, json, subprocess
from openai import OpenAI
import readline
from datetime import datetime
from pathlib import Path

API_PATH="/home/fg/import/ali_apikey"

# Set UTF-8 encoding
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

# Set up SIGQUIT handler for ^D
response_interrupted = False

def handle_quit(signum, frame):
    print("\nReceived SIGQUIT (^D), quitting gracefully...")
    exit(0)

# Set up SIGINT handler for ^C
def handle_interrupt(signum, frame):
    global response_interrupted
    response_interrupted = True
    print("\nResponse interrupted by ^C, stopping...")

signal.signal(signal.SIGQUIT, handle_quit)
signal.signal(signal.SIGINT, handle_interrupt)

script_path = Path(__file__).resolve()
script_dir = script_path.parent
# Create log directory if it doesn't exist
log_dir = os.path.join(script_dir, 'log')
os.makedirs(log_dir, exist_ok=True)

# Set up logging
current_time = datetime.now()
log_filename = current_time.strftime('%Y%m%d_%H%M.log')
log_path = os.path.join(log_dir, log_filename)

def write_to_log(conversation_pair):
    """Write a conversation pair to the log file"""
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(conversation_pair, ensure_ascii=False) + '\n')

with open(API_PATH, 'r') as file:
    my_api_key = file.read().strip() 

# OpenAI
client = OpenAI(
    api_key = my_api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

reasoning_content = ""
answer_content = ""  
is_answering = False 

# Initialize conversation history
conversation_history = []
MAX_HISTORY = 10  # Keep last 10 exchanges

emoji_laugh = "\U0001F606"
emoji_sad = "\U0001F62D"
emoji_thinking = "\U0001F914"

def format_message(role, content):
    return {"role": role, "content": content}

def read_file_content(file_spec):
    # Remove '@:' prefix and split by ':'
    parts = file_spec[2:].split(':')
    file_path = parts[0]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
            total_lines = len(content)
            
            # Default values
            start_line = 1
            end_line = total_lines
            
            # Parse start_line
            if len(parts) > 1 and parts[1]:
                start_line = int(parts[1])
            
            # Parse end_line
            if len(parts) > 2 and parts[2]:
                end_line = int(parts[2])
            
            # Adjust indices (convert to 0-based)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line)
            
            # Create metadata and get content
            metadata = f"\nFile: {file_path} (lines {start_line}-{end_line})\n"
            selected_content = content[start_idx:end_idx]
            print(f"{emoji_laugh} Add file: {file_path} (lines {start_line}-{end_line})\n")
            return metadata + ''.join(selected_content)
    except Exception as e:
        print(f"{emoji_sad} Error reading file: {e}\n")
        return None

def clear_input_buffer():
    # Clear any pending input
    while select.select([sys.stdin], [], [], 0.0)[0]:
        sys.stdin.read(1)

def execute_shell_command(command):
    """Execute a shell command and return its output"""
    try:
        # Execute the command and capture output
        result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=30)
        if result.returncode == 0:
            print(f"{emoji_laugh} Command Output: {command}\n{result.stdout}")
            return f"Command Output: {command}\n{result.stdout}"
        else:
            print(f"{emoji_thinking} Command Error: {command}\n{result.stderr}")
            return f"Command Error: {command}\n{result.stderr}"
    except subprocess.TimeoutExpired:
        print(f"{emoji_sad} Command timed out after 30 seconds: {command}")
    except Exception as e:
        print(f"{emoji_sad} Error executing command: {command}\n{str(e)}")
    return None

def get_multi_line_input_readline(prompt):
    # Clear any pending input before starting
    clear_input_buffer()
    print(prompt)
    lines = []
    try:
        while True:
            line = input().rstrip()  # Remove trailing whitespace
            if line.startswith('@:'):
                content = read_file_content(line)
                if content:
                    lines.append(content)
            elif line.startswith('@`') and line.endswith('`'):
                # Extract command between backticks
                command = line[2:-1]
                output = execute_shell_command(command)
                if output:
                    lines.append(output)
            elif line == '':
                if len(lines) >= 1 and lines[-1] == '\n':
                    break
                lines.append("\n")
            else:
                lines.append(line+"\n")
            # print(lines)
    except EOFError:
        handle_quit(0, None)
    return '\n'.join(lines)

while True:
    user_input = get_multi_line_input_readline('\U0001F60A User>> ')
    response_interrupted = False
    
    # Add user message to history
    conversation_history.append(format_message("user", user_input))
    
    # Keep only last MAX_HISTORY messages
    if len(conversation_history) > MAX_HISTORY * 2:  # *2 because each exchange has 2 messages
        conversation_history = conversation_history[-MAX_HISTORY * 2:]
    
    completion = client.chat.completions.create(
        model="deepseek-v3",  
        messages=conversation_history,  # Pass the entire conversation history
        stream=True,
    )

    has_thinking_content = False
    current_response = ""  # Collect the complete response
    
    try:
        for chunk in completion:
            if response_interrupted:
                break
                
            if not chunk.choices:
                print("\nUsage:")
                print(chunk.usage)
            else:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                    if not has_thinking_content:
                        print("\n\U0001F916 Thinking:\n")
                        has_thinking_content = True
                    print(delta.reasoning_content, end='', flush=True)
                    reasoning_content += delta.reasoning_content
                else:
                    if delta.content != "" and is_answering == False:
                        print("\n\U0001F916 Answer:\n")
                        is_answering = True
                    print(delta.content, end='', flush=True)
                    answer_content += delta.content
                    current_response += delta.content
    except Exception as e:
        print(f"\nError during response generation: {e}")
        response_interrupted = True

    # Only add assistant's response to history if not interrupted
    if not response_interrupted:
        assistant_message = format_message("assistant", current_response)
        conversation_history.append(assistant_message)
        # Log the successful conversation pair
        write_to_log(conversation_history[-2])  # User message
        write_to_log(conversation_history[-1])  # Assistant response
    else:
        # Remove the user's prompt if response was interrupted
        conversation_history.pop()
    
    print("\n")
    reasoning_content = ""
    answer_content = ""
    is_answering = False