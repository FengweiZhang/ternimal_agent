#!/home/fg/miniconda3/envs/llm/bin/python

import os
from openai import OpenAI

API_PATH="/home/fg/import/ali_apikey"

with open(API_PATH, 'r') as file:
    my_api_key = file.read().strip() 

# 初始化OpenAI客户端
client = OpenAI(
    # 如果没有配置环境变量，请用百炼API Key替换：api_key="sk-xxx"
    api_key = my_api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

reasoning_content = ""  # 定义完整思考过程
answer_content = ""     # 定义完整回复
is_answering = False   # 判断是否结束思考过程并开始回复

def get_multi_line_input(prompt):
    print(prompt)
    lines = []
    while True:
        line = input()
        if line == '' and len(lines) >= 1 and (lines[-1] == 'quit' or lines[-1] == 'q'):
            exit(0)
        if line == '' and len(lines) >= 1 and lines[-1] == '':
            break
        lines.append(line)
    return '\n'.join(lines)

while True:
    user_input = get_multi_line_input('>> 用户 <<:')
    # 创建聊天完成请求
    completion = client.chat.completions.create(
        model="deepseek-v3",  # 此处以 deepseek-r1 为例，可按需更换模型名称
        messages=[
            {"role": "user", "content": user_input}
        ],
        stream=True,
        # 解除以下注释会在最后一个chunk返回Token使用量
        # stream_options={
        #     "include_usage": True
        # }
    )

    print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

    for chunk in completion:
        # 如果chunk.choices为空，则打印usage
        if not chunk.choices:
            print("\nUsage:")
            print(chunk.usage)
        else:
            delta = chunk.choices[0].delta
            # 打印思考过程
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                print(delta.reasoning_content, end='', flush=True)
                reasoning_content += delta.reasoning_content
            else:
                # 开始回复
                if delta.content != "" and is_answering == False:
                    print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                    is_answering = True
                # 打印回复过程
                print(delta.content, end='', flush=True)
                answer_content += delta.content

    print("\n")

    reasoning_content = ""
    answer_content = ""
    is_answering = False