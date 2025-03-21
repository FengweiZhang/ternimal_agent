#!/home/fg/miniconda3/envs/llm/bin/python

import os, signal, sys
from openai import OpenAI
import readline

# Set UTF-8 encoding
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

# Set up SIGQUIT handler for ^D
def handle_quit(signum, frame):
    print("\nReceived SIGQUIT (^D), quitting gracefully...")
    exit(0)

# Set up SIGINT handler for ^C
def handle_interrupt(signum, frame):
    print("\nReceived SIGINT (^C), quitting...")
    exit(0)

signal.signal(signal.SIGQUIT, handle_quit)
signal.signal(signal.SIGINT, handle_interrupt)

API_PATH="/home/fg/import/ali_apikey"

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
            return metadata + ''.join(selected_content)
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def get_multi_line_input_readline(prompt):
    print(prompt)
    lines = []
    try:
        while True:
            line = input()
            if line in ['quit', 'q']:
                exit(0)
            elif line.startswith('@:'):
                content = read_file_content(line)
                if content:
                    lines.append(content)
            elif line == '':
                print()  
                if len(lines) >= 1 and lines[-1] == '\n':
                    break
                lines.append("\n")
            else:
                lines.append(line+"\n")
            # print(lines)
    except EOFError:
        exit(0)
    return '\n'.join(lines)

while True:
    user_input = get_multi_line_input_readline('>> ')
    completion = client.chat.completions.create(
        model="deepseek-v3",  
        messages=[
            {"role": "user", "content": user_input}
        ],
        stream=True,
    )

    has_thinking_content = False
    for chunk in completion:
        if not chunk.choices:
            print("\nUsage:")
            print(chunk.usage)
        else:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                if not has_thinking_content:
                    print("\n>>Thinking<<:\n")
                    has_thinking_content = True
                print(delta.reasoning_content, end='', flush=True)
                reasoning_content += delta.reasoning_content
            else:
                if delta.content != "" and is_answering == False:
                    print("\n>>Answer<<:\n")
                    is_answering = True
                print(delta.content, end='', flush=True)
                answer_content += delta.content

    print("\n")

    reasoning_content = ""
    answer_content = ""
    is_answering = False