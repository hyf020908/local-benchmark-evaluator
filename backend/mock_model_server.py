from __future__ import annotations

import re

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Local Benchmark Evaluator Mock Model Server")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    temperature: float = 0.0


ANSWER_MAP = {
    "If a group has only one element, what is the order of the group?": "B",
    "Which of the following sets is closed under addition?": "C",
    "分页式存储管理的主要优点是？": "B",
    "死锁产生的必要条件中不包括以下哪一项？": "C",
    "月球本身是否发光？": "C",
    "下列哪一项最适合描述恒星“光年”这个概念？": "C",
    "A rectangle has length 8 and width 3. What is its area?": "D",
    "Which expression equals 15?": "B",
    "A baker made 20 cupcakes and sold 8 in the morning and 7 in the afternoon. How many cupcakes remain?": "5",
    "There are 9 buses and each bus carries 4 teachers. How many teachers are there in total?": "36",
}


def infer_answer(prompt: str) -> str:
    for question, answer in ANSWER_MAP.items():
        if question in prompt:
            if answer.isdigit():
                return f"Let's solve it carefully.\nFinal Answer: {answer}"
            return f"I compared the options.\nFinal Answer: {answer}"

    if "Final Answer:" in prompt and "Options:" in prompt:
        return "I am not fully certain.\nFinal Answer: A"

    numbers = [int(item) for item in re.findall(r"\b\d+\b", prompt)]
    if len(numbers) >= 2 and ("How many" in prompt or "总" in prompt):
        return f"Final Answer: {sum(numbers[:2])}"

    return "Final Answer: 0"


@app.post("/v1/chat/completions")
async def chat_completions(payload: ChatRequest) -> dict:
    prompt = payload.messages[-1].content if payload.messages else ""
    content = infer_answer(prompt)
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
    }
