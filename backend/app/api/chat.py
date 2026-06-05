"""Chat API — ask questions about collected data for a specific topic."""

import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.database import Payment, Post, Comment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat")

MAX_QUESTIONS_PER_REPORT = 3


class ChatRequest(BaseModel):
    topic_id: int
    question: str
    access_token: str  # payment token to verify access


class ChatResponse(BaseModel):
    answer: str
    questions_remaining: int


@router.post("", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    """Ask a question about collected data for a topic. Requires paid access."""
    # Verify payment
    result = await session.execute(
        select(Payment).where(
            Payment.access_token == request.access_token,
            Payment.status == "paid",
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=403, detail="Доступ запрещён. Требуется оплаченный отчёт.")

    # Check questions limit
    questions_used = payment.questions_used or 0
    if questions_used >= MAX_QUESTIONS_PER_REPORT:
        raise HTTPException(status_code=429, detail="Лимит вопросов исчерпан (3 из 3)")

    # Load relevant posts for context (top 50 by comments)
    posts_result = await session.execute(
        select(Post)
        .where(Post.topic_id == request.topic_id)
        .order_by(Post.comments_count.desc())
        .limit(50)
    )
    posts = posts_result.scalars().all()

    if not posts:
        raise HTTPException(status_code=404, detail="Нет данных для этой категории")

    # Build context from posts
    context_parts = []
    for post in posts:
        await session.refresh(post, ["comments"])
        post_text = f"Пост: {post.title}\n{post.body or ''}"
        comments_text = "\n".join([f"  Коммент: {c.body}" for c in post.comments[:10]])
        context_parts.append(f"{post_text}\n{comments_text}")
        # Limit context size (~80K tokens)
        if len("\n".join(context_parts)) > 300000:
            break

    context = "\n---\n".join(context_parts)

    # Call LLM
    import httpx

    system_prompt = (
        "Ты — аналитик бизнес-ниш. Тебе даны реальные посты и комментарии с русскоязычных площадок. "
        "Отвечай на вопрос пользователя ТОЛЬКО на основе предоставленных данных. "
        "Если в данных нет ответа — так и скажи. Отвечай на русском, кратко и по делу."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Данные:\n{context}\n\n---\nВопрос: {request.question}"},
    ]

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "max_tokens": 2000,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("Chat LLM error: %s", e)
        raise HTTPException(status_code=500, detail="Ошибка генерации ответа")

    # Increment questions counter
    payment.questions_used = questions_used + 1
    await session.commit()

    return ChatResponse(
        answer=answer,
        questions_remaining=MAX_QUESTIONS_PER_REPORT - payment.questions_used,
    )
