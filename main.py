import os
import json
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

load_dotenv()

# ============== App Setup ==============

app = FastAPI(
    title="Pydantic AI Chat",
    description="AI Chat powered by Pydantic AI and OpenAI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Agent Setup ==============

class AgentDeps(BaseModel):
    user_id: str = "default"
    session_id: str = "default"

    class Config:
        arbitrary_types_allowed = True


model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

agent = Agent(
    model=f"openai:{model_name}",
    system_prompt="""Ты полезный AI-ассистент. 
Отвечай кратко и по делу на русском языке.
Используй инструменты когда это необходимо.""",
    deps_type=AgentDeps,
)


# ============== Tools ==============

@agent.tool
async def get_current_time(ctx: RunContext[AgentDeps]) -> str:
    """Получить текущую дату и время."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@agent.tool
async def calculate(ctx: RunContext[AgentDeps], expression: str) -> str:
    """
    Вычислить математическое выражение.
    Например: "2 + 2", "10 * 5", "100 / 4"
    """
    try:
        # Безопасное вычисление
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Ошибка: недопустимые символы в выражении"
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Ошибка вычисления: {str(e)}"


@agent.tool
async def save_note(ctx: RunContext[AgentDeps], title: str, content: str) -> str:
    """Сохранить заметку пользователя."""
    user_id = ctx.deps.user_id
    # В реальном приложении здесь сохранение в БД
    return f"✅ Заметка '{title}' сохранена для пользователя {user_id}"


# ============== API Models ==============

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str


# ============== API Endpoints ==============

@app.get("/health")
async def health_check():
    return {"status": "ok", "model": model_name}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Обычный (не streaming) чат."""
    try:
        deps = AgentDeps(
            user_id=request.user_id,
            session_id=request.session_id,
        )
        result = await agent.run(request.message, deps=deps)
        return ChatResponse(
            response=result.data,
            user_id=request.user_id,
            session_id=request.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming чат с Server-Sent Events."""
    
    async def generate() -> AsyncIterator[str]:
        try:
            deps = AgentDeps(
                user_id=request.user_id,
                session_id=request.session_id,
            )
            async with agent.run_stream(request.message, deps=deps) as result:
                async for chunk in result.stream_text():
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============== Web UI ==============

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Chat</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .message-enter { animation: fadeIn 0.3s ease-out; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .typing-indicator span {
            animation: blink 1.4s infinite both;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink {
            0%, 80%, 100% { opacity: 0; }
            40% { opacity: 1; }
        }
        pre code {
            display: block;
            padding: 1rem;
            overflow-x: auto;
        }
    </style>
</head>
<body class="bg-gray-900 text-white min-h-screen flex flex-col">
    
    <!-- Header -->
    <header class="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div class="max-w-4xl mx-auto flex items-center justify-between">
            <h1 class="text-xl font-semibold">🤖 AI Chat</h1>
            <span class="text-sm text-gray-400">Powered by Pydantic AI</span>
        </div>
    </header>

    <!-- Chat Container -->
    <main class="flex-1 overflow-hidden flex flex-col max-w-4xl mx-auto w-full">
        
        <!-- Messages -->
        <div id="messages" class="flex-1 overflow-y-auto p-4 space-y-4">
            <div class="text-center text-gray-500 py-8">
                <p class="text-4xl mb-4">👋</p>
                <p>Привет! Я AI-ассистент. Чем могу помочь?</p>
                <p class="text-sm mt-2">Я могу: отвечать на вопросы, считать, сохранять заметки</p>
            </div>
        </div>

        <!-- Input Area -->
        <div class="border-t border-gray-700 p-4 bg-gray-800">
            <form id="chatForm" class="flex gap-3">
                <input 
                    type="text" 
                    id="messageInput"
                    placeholder="Напишите сообщение..."
                    class="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 
                           focus:outline-none focus:border-blue-500 transition-colors"
                    autocomplete="off"
                >
                <button 
                    type="submit"
                    id="sendButton"
                    class="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 
                           disabled:cursor-not-allowed px-6 py-3 rounded-lg 
                           font-medium transition-colors"
                >
                    Отправить
                </button>
            </form>
        </div>
    </main>

    <script>
        const messagesContainer = document.getElementById('messages');
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');

        let isFirstMessage = true;

        function addMessage(content, isUser = false, isStreaming = false) {
            if (isFirstMessage) {
                messagesContainer.innerHTML = '';
                isFirstMessage = false;
            }

            const messageDiv = document.createElement('div');
            messageDiv.className = `message-enter flex ${isUser ? 'justify-end' : 'justify-start'}`;
            
            const bubble = document.createElement('div');
            bubble.className = `max-w-[80%] rounded-2xl px-4 py-3 ${
                isUser 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-700 text-gray-100'
            }`;
            
            if (isStreaming) {
                bubble.id = 'streaming-message';
                bubble.innerHTML = '<div class="typing-indicator"><span>●</span><span>●</span><span>●</span></div>';
            } else {
                bubble.innerHTML = formatMessage(content);
            }
            
            messageDiv.appendChild(bubble);
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            return bubble;
        }

        function formatMessage(text) {
            // Simple markdown-like formatting
            return text
                .replace(/```([\s\S]*?)```/g, '<pre><code class="bg-gray-800 rounded">$1</code></pre>')
                .replace(/`([^`]+)`/g, '<code class="bg-gray-800 px-1 rounded">$1</code>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
        }

        function updateStreamingMessage(content) {
            const bubble = document.getElementById('streaming-message');
            if (bubble) {
                bubble.innerHTML = formatMessage(content);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }

        function finalizeStreamingMessage() {
            const bubble = document.getElementById('streaming-message');
            if (bubble) {
                bubble.removeAttribute('id');
            }
        }

        async function sendMessage(message) {
            sendButton.disabled = true;
            messageInput.disabled = true;

            // Add user message
            addMessage(message, true);

            // Add streaming placeholder
            addMessage('', false, true);

            let fullResponse = '';

            try {
                const response = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message }),
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ') && !line.includes('[DONE]')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.content) {
                                    fullResponse += data.content;
                                    updateStreamingMessage(fullResponse);
                                }
                            } catch (e) {
                                // Skip invalid JSON
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('Error:', error);
                updateStreamingMessage('❌ Ошибка: ' + error.message);
            } finally {
                finalizeStreamingMessage();
                sendButton.disabled = false;
                messageInput.disabled = false;
                messageInput.focus();
            }
        }

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (!message) return;
            
            messageInput.value = '';
            await sendMessage(message);
        });

        // Focus input on load
        messageInput.focus();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
