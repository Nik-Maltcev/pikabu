"""
MiroFish Sender — отправка спарсенных данных в MiroFish.

Берёт посты и комментарии из БД PIKABU Topic Analyzer
и отправляет их в MiroFish API для построения графа знаний
и запуска мультиагентной симуляции.
"""

import logging
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import Post, Topic

logger = logging.getLogger(__name__)

# Таймаут для запроса к MiroFish (генерация онтологии может быть долгой)
MIROFISH_TIMEOUT = 300.0  # 5 минут


class MirofishSendError(Exception):
    """Ошибка отправки данных в MiroFish."""
    pass


class MirofishSender:
    """
    Отправляет спарсенные данные из PIKABU в MiroFish API.

    Использование:
        sender = MirofishSender(session)
        result = await sender.send_topic(
            topic_id=1,
            mirofish_url="http://localhost:5001",
            simulation_requirement="Проанализировать общественное мнение...",
        )
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def send_topic(
        self,
        topic_id: int,
        mirofish_url: str,
        simulation_requirement: str,
        project_name: Optional[str] = None,
        source: Optional[str] = None,
        habr_topic_id: Optional[int] = None,
        vcru_topic_id: Optional[int] = None,
    ) -> dict:
        """
        Загружает посты из БД и отправляет в MiroFish.

        Args:
            topic_id: ID основной темы в БД PIKABU
            mirofish_url: Base URL MiroFish (например http://localhost:5001)
            simulation_requirement: Описание задачи для симуляции
            project_name: Название проекта в MiroFish (опционально)
            source: Источник данных (pikabu/habr/vcru/...), определяется автоматически
            habr_topic_id: ID темы Habr (для комбинированного режима)
            vcru_topic_id: ID темы VC.ru (для комбинированного режима)

        Returns:
            Ответ MiroFish API (project_id, ontology, etc.)

        Raises:
            MirofishSendError: При ошибке отправки
        """
        # Загружаем тему
        topic = await self._get_topic(topic_id)
        if not topic:
            raise MirofishSendError(f"Тема не найдена: topic_id={topic_id}")

        # Определяем источник
        if source is None:
            source = topic.source or "pikabu"

        # Собираем посты из всех указанных тем
        topic_ids = [topic_id]
        sources_parts = [source]

        if habr_topic_id and habr_topic_id != topic_id:
            topic_ids.append(habr_topic_id)
            if "habr" not in source:
                sources_parts.append("habr")

        if vcru_topic_id and vcru_topic_id != topic_id:
            topic_ids.append(vcru_topic_id)
            if "vcru" not in source:
                sources_parts.append("vcru")

        source_label = ",".join(sources_parts) if len(sources_parts) > 1 else source

        # Загружаем посты
        posts_data = []
        for tid in topic_ids:
            posts = await self._load_posts(tid)
            posts_data.extend(posts)

        if not posts_data:
            raise MirofishSendError(
                f"Нет постов для отправки. Сначала запустите парсинг темы."
            )

        total_comments = sum(len(p.get("comments", [])) for p in posts_data)
        logger.info(
            f"Подготовлено для MiroFish: {len(posts_data)} постов, "
            f"{total_comments} комментариев, source={source_label}"
        )

        # Формируем запрос
        payload = {
            "posts": posts_data,
            "topic_name": topic.name,
            "source": source_label,
            "simulation_requirement": simulation_requirement,
            "project_name": project_name or f"Pikabu: {topic.name}",
        }

        # Отправляем в MiroFish
        endpoint = f"{mirofish_url.rstrip('/')}/api/graph/ontology/generate-from-pikabu"
        logger.info(f"Отправка в MiroFish: {endpoint}")

        try:
            async with httpx.AsyncClient(timeout=MIROFISH_TIMEOUT) as client:
                response = await client.post(endpoint, json=payload)

            if response.status_code != 200:
                error_detail = response.text[:500]
                raise MirofishSendError(
                    f"MiroFish вернул {response.status_code}: {error_detail}"
                )

            result = response.json()
            if not result.get("success"):
                raise MirofishSendError(
                    f"MiroFish ошибка: {result.get('error', 'Unknown error')}"
                )

            project_id = result.get("data", {}).get("project_id", "")
            logger.info(f"Данные отправлены в MiroFish. Project ID: {project_id}")
            return result

        except httpx.TimeoutException:
            raise MirofishSendError(
                f"Таймаут при отправке в MiroFish ({MIROFISH_TIMEOUT}s). "
                f"Сервер может быть перегружен."
            )
        except httpx.ConnectError:
            raise MirofishSendError(
                f"Не удалось подключиться к MiroFish: {mirofish_url}. "
                f"Проверьте, что сервер запущен."
            )
        except MirofishSendError:
            raise
        except Exception as e:
            raise MirofishSendError(f"Ошибка отправки: {str(e)}")

    async def _get_topic(self, topic_id: int) -> Optional[Topic]:
        """Загружает тему из БД."""
        result = await self.session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def _load_posts(self, topic_id: int) -> list[dict]:
        """Загружает посты с комментариями из БД в формате для MiroFish."""
        result = await self.session.execute(
            select(Post).where(Post.topic_id == topic_id)
        )
        posts = result.scalars().all()

        posts_data = []
        for post in posts:
            await self.session.refresh(post, ["comments"])
            posts_data.append({
                "title": post.title,
                "body": post.body or "",
                "published_at": (
                    post.published_at.isoformat() if post.published_at else ""
                ),
                "rating": post.rating or 0,
                "comments_count": post.comments_count or 0,
                "url": post.url or "",
                "comments": [
                    {
                        "body": c.body,
                        "published_at": (
                            c.published_at.isoformat() if c.published_at else ""
                        ),
                        "rating": c.rating or 0,
                    }
                    for c in post.comments
                ],
            })

        return posts_data
