import logging
import json
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.models.folders import Folders
from open_webui.models.chat_messages import ChatMessage, ChatMessages
from open_webui.utils.misc import (
    normalize_output_for_replay,
    sanitize_data_for_db,
    sanitize_text_for_db,
)

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import bindparam

####################
# Chat DB Schema
####################

log = logging.getLogger(__name__)


def normalize_collection_file_for_persistence(file_item: dict) -> dict:
    normalized_file = {"id": file_item.get("id"), "enabled": file_item.get("enabled", True)}
    if file_item.get("filename"):
        normalized_file["filename"] = file_item.get("filename")
    elif file_item.get("name"):
        normalized_file["name"] = file_item.get("name")
    return {k: v for k, v in normalized_file.items() if v is not None}


def normalize_chat_file_for_persistence(file_item: dict) -> dict:
    if not isinstance(file_item, dict):
        return file_item

    if file_item.get("type") != "collection":
        return file_item

    normalized = {
        "id": file_item.get("id"),
        "type": "collection",
        "name": file_item.get("name"),
        "boost": file_item.get("boost", 1.0),
        "allFilesEnabled": file_item.get("allFilesEnabled", True),
        "files": [
            normalize_collection_file_for_persistence(child)
            for child in file_item.get("files", [])
            if isinstance(child, dict)
        ],
    }
    return {k: v for k, v in normalized.items() if v is not None}


def normalize_status_history_for_persistence(status_history: list) -> list:
    if not isinstance(status_history, list):
        return status_history

    heavy_keys = {
        "sources",
        "source",
        "document",
        "documents",
        "chunks",
        "chunk",
        "content",
        "contents",
        "payload",
        "result",
        "results",
    }
    normalized_history = []
    for status in status_history:
        if not isinstance(status, dict):
            normalized_history.append(status)
            continue
        normalized_history.append(
            {key: value for key, value in status.items() if key not in heavy_keys}
        )
    return normalized_history


def normalize_source_metadata_for_persistence(metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        return metadata

    allowed_keys = {
        "source",
        "name",
        "url",
        "file_id",
        "note_id",
        "page",
        "page_start",
        "page_end",
        "print_page_start",
        "print_page_end",
        "knowledge_id",
        "knowledge_name",
        "title",
        "token_count",
        "parameters",
    }
    return {
        key: value
        for key, value in metadata.items()
        if key in allowed_keys and value is not None
    }


def normalize_source_info_for_persistence(source_info: dict) -> dict:
    if not isinstance(source_info, dict):
        return source_info

    allowed_keys = {"id", "name", "type", "url", "embed_url"}
    return {
        key: value
        for key, value in source_info.items()
        if key in allowed_keys and value is not None
    }


def normalize_sources_for_persistence(sources: list) -> list:
    if not isinstance(sources, list):
        return sources

    normalized_sources = []
    for source in sources:
        if not isinstance(source, dict):
            normalized_sources.append(source)
            continue

        normalized_source = {
            "source": normalize_source_info_for_persistence(source.get("source", {})),
            "document": source.get("document", []),
            "metadata": [
                normalize_source_metadata_for_persistence(metadata)
                for metadata in source.get("metadata", [])
            ],
        }

        if isinstance(source.get("distances"), list):
            normalized_source["distances"] = source.get("distances", [])

        normalized_sources.append(normalized_source)

    return normalized_sources


def normalize_output_for_persistence(output):
    if not isinstance(output, list):
        return output
    return normalize_output_for_replay(output)


def prefer_non_none(value, fallback):
    return fallback if value is None else value


def prefer_list(value, fallback):
    if isinstance(value, list):
        return value
    if isinstance(fallback, list):
        return fallback
    return []


def project_message_to_detail_snapshot(message: dict) -> dict:
    if not isinstance(message, dict):
        return message

    normalized = dict(message)

    if isinstance(normalized.get("files"), list):
        normalized["files"] = [
            normalize_chat_file_for_persistence(file_item)
            for file_item in normalized["files"]
        ]

    if "output" in normalized:
        normalized["output"] = normalize_output_for_persistence(normalized.get("output"))

    if "statusHistory" in normalized:
        normalized["statusHistory"] = normalize_status_history_for_persistence(
            normalized.get("statusHistory")
        )

    if "sources" in normalized:
        normalized["sources"] = normalize_sources_for_persistence(
            normalized.get("sources")
        )

    return normalized


def project_message_to_history_skeleton(
    message: dict, compatibility_mode: bool = True
) -> dict:
    if not isinstance(message, dict):
        return message

    projected = project_message_to_detail_snapshot(message)
    if compatibility_mode:
        return projected

    allowed_keys = {
        "id",
        "parentId",
        "childrenIds",
        "role",
        "content",
        "model",
        "modelName",
        "timestamp",
        "done",
        "error",
        "models",
        "selectedModelId",
        "arena",
        "modelIdx",
        "annotation",
        "favorite",
        "followUps",
        "feedbackId",
        "originalContent",
        "merged",
        "code_executions",
        "ragSnapshot",
    }
    skeleton = {
        key: value for key, value in projected.items() if key in allowed_keys
    }
    if projected.get("role") != "assistant" and "files" in projected:
        skeleton["files"] = projected.get("files")
    return skeleton


def normalize_message_for_persistence(message: dict) -> dict:
    return project_message_to_history_skeleton(message, compatibility_mode=False)


def normalize_chat_for_persistence(chat: dict) -> dict:
    if not isinstance(chat, dict):
        return chat

    normalized_chat = dict(chat)

    if isinstance(normalized_chat.get("files"), list):
        normalized_chat["files"] = [
            normalize_chat_file_for_persistence(file_item)
            for file_item in normalized_chat.get("files", [])
        ]

    history = normalized_chat.get("history")
    if isinstance(history, dict) and isinstance(history.get("messages"), dict):
        normalized_messages = {}
        for message_id, message in history["messages"].items():
            normalized_messages[message_id] = project_message_to_history_skeleton(
                message, compatibility_mode=False
            )
        normalized_chat["history"] = {**history, "messages": normalized_messages}

    return normalized_chat


def sync_chat_history_to_chat_messages(
    chat_id: str, user_id: str, chat: dict, db: Optional[Session] = None
) -> None:
    history = chat.get("history", {}) if isinstance(chat, dict) else {}
    messages = history.get("messages", {}) if isinstance(history, dict) else {}

    for message_id, message in messages.items():
        if isinstance(message, dict) and message.get("role"):
            existing_chat_message = ChatMessages.get_message_by_id(
                f"{chat_id}-{message_id}", db=db
            )
            merged_detail_message = {
                **build_message_detail_snapshot(
                    chat_id,
                    message_id,
                    message,
                    existing_chat_message,
                ),
                **project_message_to_detail_snapshot(message),
                "id": message_id,
                "chat_id": chat_id,
            }
            ChatMessages.upsert_message(
                message_id=message_id,
                chat_id=chat_id,
                user_id=user_id,
                data=merged_detail_message,
                db=db,
            )


def build_message_detail_snapshot(
    chat_id: str, message_id: str, history_message: dict, chat_message=None
) -> dict:
    detail_snapshot = project_message_to_detail_snapshot(history_message or {})
    detail_snapshot["id"] = message_id
    detail_snapshot["chat_id"] = chat_id

    if chat_message is None:
        return detail_snapshot

    detail = chat_message.model_dump()
    detail_snapshot.update(
        {
            "role": prefer_non_none(detail.get("role"), detail_snapshot.get("role")),
            "parentId": prefer_non_none(
                detail.get("parent_id"), detail_snapshot.get("parentId")
            ),
            "content": prefer_non_none(
                detail.get("content"), detail_snapshot.get("content")
            ),
            "output": prefer_non_none(
                detail.get("output"), detail_snapshot.get("output")
            ),
            "model": prefer_non_none(
                detail.get("model_id"), detail_snapshot.get("model")
            ),
            "files": prefer_non_none(
                detail.get("files"), detail_snapshot.get("files")
            ),
            "sources": prefer_non_none(
                detail.get("sources"), detail_snapshot.get("sources")
            ),
            "embeds": prefer_non_none(
                detail.get("embeds"), detail_snapshot.get("embeds")
            ),
            "statusHistory": prefer_non_none(
                normalize_status_history_for_persistence(
                    prefer_list(
                        detail.get("status_history"),
                        detail_snapshot.get("statusHistory"),
                    )
                ),
                detail_snapshot.get("statusHistory"),
            ),
            "error": prefer_non_none(
                detail.get("error"), detail_snapshot.get("error")
            ),
            "usage": prefer_non_none(
                detail.get("usage"), detail_snapshot.get("usage")
            ),
            "timestamp": prefer_non_none(
                detail.get("created_at"), detail_snapshot.get("timestamp")
            ),
            "done": prefer_non_none(
                detail.get("done"), detail_snapshot.get("done", True)
            ),
        }
    )
    return detail_snapshot


class Chat(Base):
    __tablename__ = "chat"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)
    title = Column(Text)
    chat = Column(JSON)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    share_id = Column(Text, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False, nullable=True)

    meta = Column(JSON, server_default="{}")
    folder_id = Column(Text, nullable=True)

    __table_args__ = (
        # Performance indexes for common queries
        # WHERE folder_id = ...
        Index("folder_id_idx", "folder_id"),
        # WHERE user_id = ... AND pinned = ...
        Index("user_id_pinned_idx", "user_id", "pinned"),
        # WHERE user_id = ... AND archived = ...
        Index("user_id_archived_idx", "user_id", "archived"),
        # WHERE user_id = ... ORDER BY updated_at DESC
        Index("updated_at_user_id_idx", "updated_at", "user_id"),
        # WHERE folder_id = ... AND user_id = ...
        Index("folder_id_user_id_idx", "folder_id", "user_id"),
    )


class ChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    chat: dict

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    share_id: Optional[str] = None
    archived: bool = False
    pinned: Optional[bool] = False

    meta: dict = {}
    folder_id: Optional[str] = None


class ChatFile(Base):
    __tablename__ = "chat_file"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text, nullable=False)

    chat_id = Column(Text, ForeignKey("chat.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Text, nullable=True)
    file_id = Column(Text, ForeignKey("file.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("chat_id", "file_id", name="uq_chat_file_chat_file"),
    )


class ChatFileModel(BaseModel):
    id: str
    user_id: str

    chat_id: str
    message_id: Optional[str] = None
    file_id: str

    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ChatForm(BaseModel):
    chat: dict
    folder_id: Optional[str] = None


class ChatImportForm(ChatForm):
    meta: Optional[dict] = {}
    pinned: Optional[bool] = False
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class ChatsImportForm(BaseModel):
    chats: list[ChatImportForm]


class ChatTitleMessagesForm(BaseModel):
    title: str
    messages: list[dict]


class ChatTitleForm(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    chat: dict
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch
    share_id: Optional[str] = None  # id of the chat to be shared
    archived: bool
    pinned: Optional[bool] = False
    meta: dict = {}
    folder_id: Optional[str] = None


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int


class SharedChatResponse(BaseModel):
    id: str
    title: str
    share_id: Optional[str] = None
    updated_at: int
    created_at: int


class ChatListResponse(BaseModel):
    items: list[ChatModel]
    total: int


class ChatUsageStatsResponse(BaseModel):
    id: str  # chat id

    models: dict = {}  # models used in the chat with their usage counts
    message_count: int  # number of messages in the chat

    history_models: dict = {}  # models used in the chat history with their usage counts
    history_message_count: int  # number of messages in the chat history
    history_user_message_count: int  # number of user messages in the chat history
    history_assistant_message_count: (
        int  # number of assistant messages in the chat history
    )

    average_response_time: (
        float  # average response time of assistant messages in seconds
    )
    average_user_message_content_length: (
        float  # average length of user message contents
    )
    average_assistant_message_content_length: (
        float  # average length of assistant message contents
    )

    tags: list[str] = []  # tags associated with the chat

    last_message_at: int  # timestamp of the last message
    updated_at: int
    created_at: int

    model_config = ConfigDict(extra="allow")


class ChatUsageStatsListResponse(BaseModel):
    items: list[ChatUsageStatsResponse]
    total: int
    model_config = ConfigDict(extra="allow")


class MessageStats(BaseModel):
    id: str
    role: str
    model: Optional[str] = None
    content_length: int
    token_count: Optional[int] = None
    timestamp: Optional[int] = None
    rating: Optional[int] = None  # Derived from message.annotation.rating
    tags: Optional[list[str]] = None  # Derived from message.annotation.tags


class ChatHistoryStats(BaseModel):
    messages: dict[str, MessageStats]
    currentId: Optional[str] = None


class ChatBody(BaseModel):
    history: ChatHistoryStats


class AggregateChatStats(BaseModel):
    average_response_time: float
    average_user_message_content_length: float
    average_assistant_message_content_length: float
    models: dict[str, int]
    message_count: int
    history_models: dict[str, int]
    history_message_count: int
    history_user_message_count: int
    history_assistant_message_count: int


class ChatStatsExport(BaseModel):
    id: str
    user_id: str
    created_at: int
    updated_at: int
    tags: list[str] = []
    stats: AggregateChatStats
    chat: ChatBody


class ChatTable:
    def _clean_null_bytes(self, obj):
        """Recursively remove null bytes from strings in dict/list structures."""
        return sanitize_data_for_db(obj)

    def _sanitize_chat_row(self, chat_item):
        """
        Clean a Chat SQLAlchemy model's title + chat JSON,
        and return True if anything changed.
        """
        changed = False

        # Clean title
        if chat_item.title:
            cleaned = self._clean_null_bytes(chat_item.title)
            if cleaned != chat_item.title:
                chat_item.title = cleaned
                changed = True

        # Clean JSON
        if chat_item.chat:
            cleaned = self._clean_null_bytes(chat_item.chat)
            if cleaned != chat_item.chat:
                chat_item.chat = cleaned
                changed = True

        return changed

    def insert_new_chat(
        self, user_id: str, form_data: ChatForm, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        with get_db_context(db) as db:
            normalized_chat = normalize_chat_for_persistence(form_data.chat)
            id = str(uuid.uuid4())
            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": self._clean_null_bytes(
                        normalized_chat["title"]
                        if "title" in normalized_chat
                        else "New Chat"
                    ),
                    "chat": self._clean_null_bytes(normalized_chat),
                    "folder_id": form_data.folder_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            chat_item = Chat(**chat.model_dump())
            db.add(chat_item)
            db.commit()
            db.refresh(chat_item)

            # Dual-write initial messages to chat_message table
            try:
                history = form_data.chat.get("history", {})
                messages = history.get("messages", {})
                for message_id, message in messages.items():
                    if isinstance(message, dict) and message.get("role"):
                        ChatMessages.upsert_message(
                            message_id=message_id,
                            chat_id=id,
                            user_id=user_id,
                            data=project_message_to_detail_snapshot(message),
                        )
            except Exception as e:
                log.warning(
                    f"Failed to write initial messages to chat_message table: {e}"
                )

            return ChatModel.model_validate(chat_item) if chat_item else None

    def _chat_import_form_to_chat_model(
        self, user_id: str, form_data: ChatImportForm
    ) -> ChatModel:
        id = str(uuid.uuid4())
        normalized_chat = normalize_chat_for_persistence(form_data.chat)
        chat = ChatModel(
            **{
                "id": id,
                "user_id": user_id,
                "title": self._clean_null_bytes(
                    normalized_chat["title"] if "title" in normalized_chat else "New Chat"
                ),
                "chat": self._clean_null_bytes(normalized_chat),
                "meta": form_data.meta,
                "pinned": form_data.pinned,
                "folder_id": form_data.folder_id,
                "created_at": (
                    form_data.created_at if form_data.created_at else int(time.time())
                ),
                "updated_at": (
                    form_data.updated_at if form_data.updated_at else int(time.time())
                ),
            }
        )
        return chat

    def import_chats(
        self,
        user_id: str,
        chat_import_forms: list[ChatImportForm],
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            chats = []

            for form_data in chat_import_forms:
                chat = self._chat_import_form_to_chat_model(user_id, form_data)
                chats.append(Chat(**chat.model_dump()))

            db.add_all(chats)
            db.commit()

            # Dual-write messages to chat_message table
            try:
                for form_data, chat_obj in zip(chat_import_forms, chats):
                    history = form_data.chat.get("history", {})
                    messages = history.get("messages", {})
                    for message_id, message in messages.items():
                        if isinstance(message, dict) and message.get("role"):
                            ChatMessages.upsert_message(
                                message_id=message_id,
                                chat_id=chat_obj.id,
                                user_id=user_id,
                                data=project_message_to_detail_snapshot(message),
                            )
            except Exception as e:
                log.warning(
                    f"Failed to write imported messages to chat_message table: {e}"
                )

            return [ChatModel.model_validate(chat) for chat in chats]

    def update_chat_by_id(
        self, id: str, chat: dict, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat_item = db.get(Chat, id)
                normalized_chat = normalize_chat_for_persistence(chat)
                chat_item.chat = self._clean_null_bytes(normalized_chat)
                chat_item.title = (
                    self._clean_null_bytes(normalized_chat["title"])
                    if "title" in normalized_chat
                    else "New Chat"
                )

                chat_item.updated_at = int(time.time())

                db.commit()
                db.refresh(chat_item)

                try:
                    sync_chat_history_to_chat_messages(
                        chat_id=id,
                        user_id=chat_item.user_id,
                        chat=chat,
                        db=db,
                    )
                except Exception as e:
                    log.warning(
                        f"Failed to resync chat history to chat_message table: {e}"
                    )

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    def update_chat_title_by_id(self, id: str, title: str) -> Optional[ChatModel]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        chat = chat.chat
        chat["title"] = title

        return self.update_chat_by_id(id, chat)

    def update_chat_tags_by_id(
        self, id: str, tags: list[str], user
    ) -> Optional[ChatModel]:
        with get_db_context() as db:
            chat = db.get(Chat, id)
            if chat is None:
                return None

            old_tags = chat.meta.get("tags", [])
            new_tags = [t for t in tags if t.replace(" ", "_").lower() != "none"]
            new_tag_ids = [t.replace(" ", "_").lower() for t in new_tags]

            # Single meta update
            chat.meta = {**chat.meta, "tags": new_tag_ids}
            db.commit()
            db.refresh(chat)

            # Batch-create any missing tag rows
            Tags.ensure_tags_exist(new_tags, user.id, db=db)

            # Clean up orphaned old tags in one query
            removed = set(old_tags) - set(new_tag_ids)
            if removed:
                self.delete_orphan_tags_for_user(list(removed), user.id, db=db)

            return ChatModel.model_validate(chat)

    def get_chat_title_by_id(self, id: str) -> Optional[str]:
        with get_db_context() as db:
            result = db.query(Chat.title).filter_by(id=id).first()
            if result is None:
                return None
            return result[0] or "New Chat"

    def get_messages_map_by_chat_id(self, id: str) -> Optional[dict]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}) or {}

    def get_message_by_id_and_message_id(
        self, id: str, message_id: str
    ) -> Optional[dict]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}).get(message_id, {})

    def get_message_detail_by_id_and_message_id(
        self, id: str, message_id: str, db: Optional[Session] = None
    ) -> Optional[dict]:
        chat = self.get_chat_by_id(id, db=db)
        if chat is None:
            return None

        history_message = (
            chat.chat.get("history", {}).get("messages", {}).get(message_id, {}) or {}
        )
        chat_message = ChatMessages.get_message_by_id(f"{id}-{message_id}", db=db)

        if chat_message is None:
            return build_message_detail_snapshot(id, message_id, history_message)

        return build_message_detail_snapshot(id, message_id, history_message, chat_message)

    def upsert_message_to_chat_by_id_and_message_id(
        self,
        id: str,
        message_id: str,
        message: dict,
        db: Optional[Session] = None,
    ) -> Optional[ChatModel]:
        chat = self.get_chat_by_id(id, db=db)
        if chat is None:
            return None

        # Sanitize message content for null characters before upserting
        if isinstance(message.get("content"), str):
            message["content"] = sanitize_text_for_db(message["content"])

        user_id = chat.user_id
        chat = chat.chat
        history = chat.get("history", {})
        history_messages = history.setdefault("messages", {})
        detail_message = project_message_to_detail_snapshot(message)
        existing_detail_message = self.get_message_detail_by_id_and_message_id(
            id, message_id, db=db
        ) or build_message_detail_snapshot(
            id, message_id, history_messages.get(message_id, {})
        )
        merged_detail_message = {
            **existing_detail_message,
            **detail_message,
            "id": message_id,
            "chat_id": id,
        }

        history_messages[message_id] = project_message_to_history_skeleton(
            merged_detail_message, compatibility_mode=False
        )

        history["currentId"] = message_id

        chat["history"] = history

        # Dual-write to chat_message table
        try:
            ChatMessages.upsert_message(
                message_id=message_id,
                chat_id=id,
                user_id=user_id,
                data=merged_detail_message,
            )
        except Exception as e:
            log.warning(f"Failed to write to chat_message table: {e}")

        return self.update_chat_by_id(id, chat, db=db)

    def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> Optional[ChatModel]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        user_id = chat.user_id
        chat_data = chat.chat
        history = chat_data.get("history", {})
        history_messages = history.get("messages", {})

        if message_id in history_messages:
            detail_message = self.get_message_detail_by_id_and_message_id(
                id, message_id
            ) or build_message_detail_snapshot(
                id, message_id, history_messages.get(message_id, {})
            )
            status_history = detail_message.get("statusHistory")
            if not isinstance(status_history, list):
                status_history = []
            status_history.append(status)
            detail_message["statusHistory"] = normalize_status_history_for_persistence(
                status_history
            )
            history_messages[message_id] = project_message_to_history_skeleton(
                detail_message, compatibility_mode=False
            )

            try:
                ChatMessages.upsert_message(
                    message_id=message_id,
                    chat_id=id,
                    user_id=user_id,
                    data=detail_message,
                )
            except Exception as e:
                log.warning(f"Failed to write status update to chat_message table: {e}")

        history["messages"] = history_messages
        chat_data["history"] = history
        return self.update_chat_by_id(id, chat_data)

    def add_message_files_by_id_and_message_id(
        self, id: str, message_id: str, files: list[dict]
    ) -> list[dict]:
        with get_db_context() as db:
            chat = self.get_chat_by_id(id, db=db)
            if chat is None:
                return None

            user_id = chat.user_id
            chat_data = chat.chat
            history = chat_data.get("history", {})
            history_messages = history.get("messages", {})

            message_files = []

            if message_id in history_messages:
                detail_message = self.get_message_detail_by_id_and_message_id(
                    id, message_id, db=db
                ) or build_message_detail_snapshot(
                    id, message_id, history_messages.get(message_id, {})
                )
                message_files = detail_message.get("files", [])
                message_files = message_files + files
                detail_message["files"] = [
                    normalize_chat_file_for_persistence(file_item)
                    for file_item in message_files
                ]
                history_messages[message_id] = project_message_to_history_skeleton(
                    detail_message, compatibility_mode=False
                )

                try:
                    ChatMessages.upsert_message(
                        message_id=message_id,
                        chat_id=id,
                        user_id=user_id,
                        data=detail_message,
                    )
                except Exception as e:
                    log.warning(f"Failed to write file update to chat_message table: {e}")

            history["messages"] = history_messages
            chat_data["history"] = history
            self.update_chat_by_id(id, chat_data, db=db)
            return message_files

    def insert_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        with get_db_context(db) as db:
            # Get the existing chat to share
            chat = db.get(Chat, chat_id)
            # Check if chat exists
            if not chat:
                return None
            # Check if the chat is already shared
            if chat.share_id:
                return self.get_chat_by_id_and_user_id(chat.share_id, "shared", db=db)
            # Create a new chat with the same data, but with a new ID
            shared_chat = ChatModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": f"shared-{chat_id}",
                    "title": chat.title,
                    "chat": chat.chat,
                    "meta": chat.meta,
                    "pinned": chat.pinned,
                    "folder_id": chat.folder_id,
                    "created_at": chat.created_at,
                    "updated_at": int(time.time()),
                }
            )
            shared_result = Chat(**shared_chat.model_dump())
            db.add(shared_result)
            db.commit()
            db.refresh(shared_result)

            # Update the original chat with the share_id
            result = (
                db.query(Chat)
                .filter_by(id=chat_id)
                .update({"share_id": shared_chat.id})
            )
            db.commit()
            return shared_chat if (shared_result and result) else None

    def update_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, chat_id)
                shared_chat = (
                    db.query(Chat).filter_by(user_id=f"shared-{chat_id}").first()
                )

                if shared_chat is None:
                    return self.insert_shared_chat_by_chat_id(chat_id, db=db)

                shared_chat.title = chat.title
                shared_chat.chat = chat.chat
                shared_chat.meta = chat.meta
                shared_chat.pinned = chat.pinned
                shared_chat.folder_id = chat.folder_id
                shared_chat.updated_at = int(time.time())
                db.commit()
                db.refresh(shared_chat)

                return ChatModel.model_validate(shared_chat)
        except Exception:
            return None

    def delete_shared_chat_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                # Use subquery to delete chat_messages for shared chats
                shared_chat_id_subquery = (
                    db.query(Chat.id)
                    .filter_by(user_id=f"shared-{chat_id}")
                    .scalar_subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(shared_chat_id_subquery)
                ).delete(synchronize_session=False)
                db.query(Chat).filter_by(user_id=f"shared-{chat_id}").delete()
                db.commit()

                return True
        except Exception:
            return False

    def unarchive_all_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Chat).filter_by(user_id=user_id).update({"archived": False})
                db.commit()
                return True
        except Exception:
            return False

    def update_chat_share_id_by_id(
        self, id: str, share_id: Optional[str], db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.share_id = share_id
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_pinned_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.pinned = not chat.pinned
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_archive_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.archived = not chat.archived
                chat.folder_id = None
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def archive_all_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Chat).filter_by(user_id=user_id).update({"archived": True})
                db.commit()
                return True
        except Exception:
            return False

    def get_archived_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ChatTitleIdResponse]:

        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=True)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction:
                    if not getattr(Chat, order_by, None):
                        raise ValueError("Invalid order_by field")

                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

            query = query.with_entities(
                Chat.id, Chat.title, Chat.updated_at, Chat.created_at
            )

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        "id": chat[0],
                        "title": chat[1],
                        "updated_at": chat[2],
                        "created_at": chat[3],
                    }
                )
                for chat in all_chats
            ]

    def get_shared_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[SharedChatResponse]:

        with get_db_context(db) as db:
            query = (
                db.query(Chat)
                .filter_by(user_id=user_id)
                .filter(Chat.share_id.isnot(None))
            )

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction:
                    if not getattr(Chat, order_by, None):
                        raise ValueError("Invalid order_by field")

                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

            # Select only the columns needed for SharedChatResponse
            # to avoid loading the heavy chat JSON blob
            query = query.with_entities(
                Chat.id,
                Chat.title,
                Chat.share_id,
                Chat.updated_at,
                Chat.created_at,
            )

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [
                SharedChatResponse.model_validate(
                    {
                        "id": chat[0],
                        "title": chat[1],
                        "share_id": chat[2],
                        "updated_at": chat[3],
                        "created_at": chat[4],
                    }
                )
                for chat in all_chats
            ]

    def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            if not include_archived:
                query = query.filter_by(archived=False)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction and getattr(Chat, order_by):
                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc(), Chat.id)
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc(), Chat.id)
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_title_id_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        include_folders: bool = False,
        include_pinned: bool = False,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> list[ChatTitleIdResponse]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            if not include_folders:
                query = query.filter_by(folder_id=None)

            if not include_pinned:
                query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))

            if not include_archived:
                query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc(), Chat.id).with_entities(
                Chat.id, Chat.title, Chat.updated_at, Chat.created_at
            )

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()

            # result has to be destructured from sqlalchemy `row` and mapped to a dict since the `ChatModel`is not the returned dataclass.
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        "id": chat[0],
                        "title": chat[1],
                        "updated_at": chat[2],
                        "created_at": chat[3],
                    }
                )
                for chat in all_chats
            ]

    def get_chat_list_by_chat_ids(
        self,
        chat_ids: list[str],
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            all_chats = (
                db.query(Chat)
                .filter(Chat.id.in_(chat_ids))
                .filter_by(archived=False)
                .order_by(Chat.updated_at.desc())
                .all()
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat_item = db.get(Chat, id)
                if chat_item is None:
                    return None

                if self._sanitize_chat_row(chat_item):
                    db.commit()
                    db.refresh(chat_item)

                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    def get_chat_by_share_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                # it is possible that the shared link was deleted. hence,
                # we check if the chat is still shared by checking if a chat with the share_id exists
                chat = db.query(Chat).filter_by(share_id=id).first()

                if chat:
                    return self.get_chat_by_id(id, db=db)
                else:
                    return None
        except Exception:
            return None

    def get_chat_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.query(Chat).filter_by(id=id, user_id=user_id).first()
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def is_chat_owner(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        """
        Lightweight ownership check — uses EXISTS subquery instead of loading
        the full Chat row (which includes the potentially large JSON blob).
        """
        try:
            with get_db_context(db) as db:
                return db.query(
                    exists().where(and_(Chat.id == id, Chat.user_id == user_id))
                ).scalar()
        except Exception:
            return False

    def get_chat_folder_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[str]:
        """
        Fetch only the folder_id column for a chat, without loading the full
        JSON blob. Returns None if chat doesn't exist or doesn't belong to user.
        """
        try:
            with get_db_context(db) as db:
                result = (
                    db.query(Chat.folder_id).filter_by(id=id, user_id=user_id).first()
                )
                return result[0] if result else None
        except Exception:
            return None

    def get_chats(
        self, skip: int = 0, limit: int = 50, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            all_chats = (
                db.query(Chat)
                # .limit(limit).offset(skip)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> ChatListResponse:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            if filter:
                if filter.get("updated_at"):
                    query = query.filter(Chat.updated_at > filter.get("updated_at"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction:
                    if hasattr(Chat, order_by):
                        if direction.lower() == "asc":
                            query = query.order_by(
                                getattr(Chat, order_by).asc(), Chat.id
                            )
                        elif direction.lower() == "desc":
                            query = query.order_by(
                                getattr(Chat, order_by).desc(), Chat.id
                            )
                else:
                    query = query.order_by(Chat.updated_at.desc(), Chat.id)

            else:
                query = query.order_by(Chat.updated_at.desc(), Chat.id)

            total = query.count()

            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            all_chats = query.all()

            return ChatListResponse(
                **{
                    "items": [ChatModel.model_validate(chat) for chat in all_chats],
                    "total": total,
                }
            )

    def get_pinned_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> list[ChatTitleIdResponse]:
        with get_db_context(db) as db:
            all_chats = (
                db.query(Chat)
                .filter_by(user_id=user_id, pinned=True, archived=False)
                .order_by(Chat.updated_at.desc())
                .with_entities(Chat.id, Chat.title, Chat.updated_at, Chat.created_at)
            )
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        "id": chat[0],
                        "title": chat[1],
                        "updated_at": chat[2],
                        "created_at": chat[3],
                    }
                )
                for chat in all_chats
            ]

    def get_archived_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            all_chats = (
                db.query(Chat)
                .filter_by(user_id=user_id, archived=True)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        """
        Filters chats based on a search query using Python, allowing pagination using skip and limit.
        """
        search_text = sanitize_text_for_db(search_text).lower().strip()

        if not search_text:
            return self.get_chat_list_by_user_id(
                user_id, include_archived, filter={}, skip=skip, limit=limit, db=db
            )

        search_text_words = search_text.split(" ")

        # search_text might contain 'tag:tag_name' format so we need to extract the tag_name, split the search_text and remove the tags
        tag_ids = [
            word.replace("tag:", "").replace(" ", "_").lower()
            for word in search_text_words
            if word.startswith("tag:")
        ]

        # Extract folder names - handle spaces and case insensitivity
        folders = Folders.search_folders_by_names(
            user_id,
            [
                word.replace("folder:", "")
                for word in search_text_words
                if word.startswith("folder:")
            ],
        )
        folder_ids = [folder.id for folder in folders]

        is_pinned = None
        if "pinned:true" in search_text_words:
            is_pinned = True
        elif "pinned:false" in search_text_words:
            is_pinned = False

        is_archived = None
        if "archived:true" in search_text_words:
            is_archived = True
        elif "archived:false" in search_text_words:
            is_archived = False

        is_shared = None
        if "shared:true" in search_text_words:
            is_shared = True
        elif "shared:false" in search_text_words:
            is_shared = False

        search_text_words = [
            word
            for word in search_text_words
            if (
                not word.startswith("tag:")
                and not word.startswith("folder:")
                and not word.startswith("pinned:")
                and not word.startswith("archived:")
                and not word.startswith("shared:")
            )
        ]

        search_text = " ".join(search_text_words)

        with get_db_context(db) as db:
            query = db.query(Chat).filter(Chat.user_id == user_id)

            if is_archived is not None:
                query = query.filter(Chat.archived == is_archived)
            elif not include_archived:
                query = query.filter(Chat.archived == False)

            if is_pinned is not None:
                query = query.filter(Chat.pinned == is_pinned)

            if is_shared is not None:
                if is_shared:
                    query = query.filter(Chat.share_id.isnot(None))
                else:
                    query = query.filter(Chat.share_id.is_(None))

            if folder_ids:
                query = query.filter(Chat.folder_id.in_(folder_ids))

            query = query.order_by(Chat.updated_at.desc(), Chat.id)

            # Check if the database dialect is either 'sqlite' or 'postgresql'
            dialect_name = db.bind.dialect.name
            if dialect_name == "sqlite":
                # SQLite case: using JSON1 extension for JSON searching
                sqlite_content_sql = (
                    "EXISTS ("
                    "    SELECT 1 "
                    "    FROM json_each(Chat.chat, '$.messages') AS message "
                    "    WHERE LOWER(message.value->>'content') LIKE '%' || :content_key || '%'"
                    ")"
                )
                sqlite_content_clause = text(sqlite_content_sql)
                query = query.filter(
                    or_(
                        Chat.title.ilike(bindparam("title_key")), sqlite_content_clause
                    ).params(title_key=f"%{search_text}%", content_key=search_text)
                )

                # Check if there are any tags to filter, it should have all the tags
                if "none" in tag_ids:
                    query = query.filter(text("""
                            NOT EXISTS (
                                SELECT 1
                                FROM json_each(Chat.meta, '$.tags') AS tag
                            )
                            """))
                elif tag_ids:
                    query = query.filter(
                        and_(
                            *[
                                text(f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_each(Chat.meta, '$.tags') AS tag
                                        WHERE tag.value = :tag_id_{tag_idx}
                                    )
                                    """).params(**{f"tag_id_{tag_idx}": tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )

            elif dialect_name == "postgresql":
                # PostgreSQL doesn't allow null bytes in text. We filter those out by checking
                # the JSON representation for \u0000 before attempting text extraction

                # Safety filter: JSON field must not contain \u0000
                query = query.filter(text("Chat.chat::text NOT LIKE '%\\\\u0000%'"))

                # Safety filter: title must not contain actual null bytes
                query = query.filter(text("Chat.title::text NOT LIKE '%\\x00%'"))

                postgres_content_sql = """
                EXISTS (
                    SELECT 1
                    FROM json_array_elements(Chat.chat->'messages') AS message
                    WHERE json_typeof(message->'content') = 'string'
                    AND LOWER(message->>'content') LIKE '%' || :content_key || '%'
                )
                """

                postgres_content_clause = text(postgres_content_sql)

                query = query.filter(
                    or_(
                        Chat.title.ilike(bindparam("title_key")),
                        postgres_content_clause,
                    )
                ).params(title_key=f"%{search_text}%", content_key=search_text.lower())

                # Check if there are any tags to filter, it should have all the tags
                if "none" in tag_ids:
                    query = query.filter(text("""
                            NOT EXISTS (
                                SELECT 1
                                FROM json_array_elements_text(Chat.meta->'tags') AS tag
                            )
                            """))
                elif tag_ids:
                    query = query.filter(
                        and_(
                            *[
                                text(f"""
                                    EXISTS (
                                        SELECT 1
                                        FROM json_array_elements_text(Chat.meta->'tags') AS tag
                                        WHERE tag = :tag_id_{tag_idx}
                                    )
                                    """).params(**{f"tag_id_{tag_idx}": tag_id})
                                for tag_idx, tag_id in enumerate(tag_ids)
                            ]
                        )
                    )
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Perform pagination at the SQL level
            all_chats = query.offset(skip).limit(limit).all()

            log.info(f"The number of chats: {len(all_chats)}")

            # Validate and return chats
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_folder_id_and_user_id(
        self,
        folder_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 60,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(folder_id=folder_id, user_id=user_id)
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc(), Chat.id)

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter(
                Chat.folder_id.in_(folder_ids), Chat.user_id == user_id
            )
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.folder_id = folder_id
                chat.updated_at = int(time.time())
                chat.pinned = False
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chat_tags_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> list[TagModel]:
        with get_db_context(db) as db:
            chat = db.get(Chat, id)
            tag_ids = chat.meta.get("tags", [])
            return Tags.get_tags_by_ids_and_user_id(tag_ids, user_id, db=db)

    def get_chat_list_by_user_id_and_tag_name(
        self,
        user_id: str,
        tag_name: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            tag_id = tag_name.replace(" ", "_").lower()

            log.info(f"DB dialect name: {db.bind.dialect.name}")
            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 querying for tags within the meta JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif db.bind.dialect.name == "postgresql":
                # PostgreSQL JSON query for tags within the meta JSON field (for `json` type)
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            all_chats = query.all()
            log.debug(f"all_chats: {all_chats}")
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def add_chat_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str, db: Optional[Session] = None
    ) -> Optional[ChatModel]:
        tag_id = tag_name.replace(" ", "_").lower()
        Tags.ensure_tags_exist([tag_name], user_id, db=db)
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                if tag_id not in chat.meta.get("tags", []):
                    chat.meta = {
                        **chat.meta,
                        "tags": list(set(chat.meta.get("tags", []) + [tag_id])),
                    }
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def count_chats_by_tag_name_and_user_id(
        self, tag_name: str, user_id: str, db: Optional[Session] = None
    ) -> int:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)
            tag_id = tag_name.replace(" ", "_").lower()

            if db.bind.dialect.name == "sqlite":
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif db.bind.dialect.name == "postgresql":
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            return query.count()

    def delete_orphan_tags_for_user(
        self,
        tag_ids: list[str],
        user_id: str,
        threshold: int = 0,
        db: Optional[Session] = None,
    ) -> None:
        """Delete tag rows from *tag_ids* that appear in at most *threshold*
        non-archived chats for *user_id*.  One query to find orphans, one to
        delete them.

        Use threshold=0 after a tag is already removed from a chat's meta.
        Use threshold=1 when the chat itself is about to be deleted (the
        referencing chat still exists at query time).
        """
        if not tag_ids:
            return
        with get_db_context(db) as db:
            orphans = []
            for tag_id in tag_ids:
                count = self.count_chats_by_tag_name_and_user_id(tag_id, user_id, db=db)
                if count <= threshold:
                    orphans.append(tag_id)
            Tags.delete_tags_by_ids_and_user_id(orphans, user_id, db=db)

    def count_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str, db: Optional[Session] = None
    ) -> int:
        with get_db_context(db) as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            query = query.filter_by(folder_id=folder_id)
            count = query.count()

            log.info(f"Count of chats for folder '{folder_id}': {count}")
            return count

    def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                tags = chat.meta.get("tags", [])
                tag_id = tag_name.replace(" ", "_").lower()

                tags = [tag for tag in tags if tag != tag_id]
                chat.meta = {
                    **chat.meta,
                    "tags": list(set(tags)),
                }
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_tags_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                chat = db.get(Chat, id)
                chat.meta = {
                    **chat.meta,
                    "tags": [],
                }
                db.commit()

                return True
        except Exception:
            return False

    def delete_chat_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(ChatMessage).filter_by(chat_id=id).delete()
                db.query(Chat).filter_by(id=id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id, db=db)
        except Exception:
            return False

    def delete_chat_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(ChatMessage).filter_by(chat_id=id).delete()
                db.query(Chat).filter_by(id=id, user_id=user_id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id, db=db)
        except Exception:
            return False

    def delete_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                self.delete_shared_chats_by_user_id(user_id, db=db)

                chat_id_subquery = (
                    db.query(Chat.id).filter_by(user_id=user_id).subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(chat_id_subquery)
                ).delete(synchronize_session=False)
                db.query(Chat).filter_by(user_id=user_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                chat_id_subquery = (
                    db.query(Chat.id)
                    .filter_by(user_id=user_id, folder_id=folder_id)
                    .subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(chat_id_subquery)
                ).delete(synchronize_session=False)
                db.query(Chat).filter_by(user_id=user_id, folder_id=folder_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def move_chats_by_user_id_and_folder_id(
        self,
        user_id: str,
        folder_id: str,
        new_folder_id: Optional[str],
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Chat).filter_by(user_id=user_id, folder_id=folder_id).update(
                    {"folder_id": new_folder_id}
                )
                db.commit()

                return True
        except Exception:
            return False

    def delete_shared_chats_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                chats_by_user = db.query(Chat).filter_by(user_id=user_id).all()
                shared_chat_ids = [f"shared-{chat.id}" for chat in chats_by_user]

                # Use subquery to delete chat_messages for shared chats
                shared_id_subq = (
                    db.query(Chat.id)
                    .filter(Chat.user_id.in_(shared_chat_ids))
                    .subquery()
                )
                db.query(ChatMessage).filter(
                    ChatMessage.chat_id.in_(shared_id_subq)
                ).delete(synchronize_session=False)
                db.query(Chat).filter(Chat.user_id.in_(shared_chat_ids)).delete()
                db.commit()

                return True
        except Exception:
            return False

    def insert_chat_files(
        self,
        chat_id: str,
        message_id: str,
        file_ids: list[str],
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[list[ChatFileModel]]:
        if not file_ids:
            return None

        chat_message_file_ids = [
            item.id
            for item in self.get_chat_files_by_chat_id_and_message_id(
                chat_id, message_id, db=db
            )
        ]
        # Remove duplicates and existing file_ids
        file_ids = list(
            set(
                [
                    file_id
                    for file_id in file_ids
                    if file_id and file_id not in chat_message_file_ids
                ]
            )
        )
        if not file_ids:
            return None

        try:
            with get_db_context(db) as db:
                now = int(time.time())

                chat_files = [
                    ChatFileModel(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        file_id=file_id,
                        created_at=now,
                        updated_at=now,
                    )
                    for file_id in file_ids
                ]

                results = [
                    ChatFile(**chat_file.model_dump()) for chat_file in chat_files
                ]

                db.add_all(results)
                db.commit()

                return chat_files
        except Exception:
            return None

    def get_chat_files_by_chat_id_and_message_id(
        self, chat_id: str, message_id: str, db: Optional[Session] = None
    ) -> list[ChatFileModel]:
        with get_db_context(db) as db:
            all_chat_files = (
                db.query(ChatFile)
                .filter_by(chat_id=chat_id, message_id=message_id)
                .order_by(ChatFile.created_at.asc())
                .all()
            )
            return [
                ChatFileModel.model_validate(chat_file) for chat_file in all_chat_files
            ]

    def delete_chat_file(
        self, chat_id: str, file_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(ChatFile).filter_by(chat_id=chat_id, file_id=file_id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def get_shared_chats_by_file_id(
        self, file_id: str, db: Optional[Session] = None
    ) -> list[ChatModel]:
        with get_db_context(db) as db:
            # Join Chat and ChatFile tables to get shared chats associated with the file_id
            all_chats = (
                db.query(Chat)
                .join(ChatFile, Chat.id == ChatFile.chat_id)
                .filter(ChatFile.file_id == file_id, Chat.share_id.isnot(None))
                .all()
            )

            return [ChatModel.model_validate(chat) for chat in all_chats]


Chats = ChatTable()
