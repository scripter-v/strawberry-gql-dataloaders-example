import logging
from fastapi import FastAPI, HTTPException
import strawberry
from strawberry.dataloader import DataLoader
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from typing import TypedDict

from app.storage import AuthorRecord, BookRecord, InMemoryStorage, Storage

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@strawberry.type
class Author:
    id: str
    name: str


def _author_from_record(record: AuthorRecord | None) -> Author | None:
    return Author(id=record.id, name=record.name) if record is not None else None


def _author_payload(record: AuthorRecord) -> dict[str, str]:
    return {"id": record.id, "name": record.name}


async def _book_payload(record: BookRecord) -> dict[str, str | dict[str, str]]:
    author = await storage.get_author(record.author_id)
    if author is None:
        raise ValueError(f"Missing author {record.author_id} for book {record.id}")
    return {
        "id": record.id,
        "title": record.title,
        "author": _author_payload(author),
    }


def _book_from_record(record: BookRecord) -> "Book":
    return Book(id=record.id, title=record.title, author_id=record.author_id)


@strawberry.type
class Book:
    id: str
    title: str
    author_id: strawberry.Private[str]

    @strawberry.field
    async def author(self, info: Info["GraphQLContext", None]) -> Author | None:
        logger.info("WTF1")
        author = await info.context["author_loader"].load(self.author_id)
        logger.info(f"WTF2: {author}")
        return author


storage: Storage = InMemoryStorage()


class GraphQLContext(TypedDict):
    author_loader: DataLoader[str, Author | None]


async def _load_authors(author_ids: list[str]) -> list[Author | None]:
    return [
        _author_from_record(ar) for ar in await storage.get_authors_by_ids(author_ids)
    ]


async def get_context() -> GraphQLContext:
    return {
        "author_loader": DataLoader(load_fn=_load_authors),
    }


@strawberry.type
class Query:
    @strawberry.field
    async def authors(self) -> list[Author | None]:  # FIXME narrow
        return [_author_from_record(record) for record in await storage.list_authors()]

    @strawberry.field
    async def author(self, id: str) -> Author | None:
        return _author_from_record(await storage.get_author(id))

    @strawberry.field
    async def books(self) -> list[Book]:
        return [_book_from_record(record) for record in await storage.list_books()]

    @strawberry.field
    async def book(self, id: str) -> Book | None:
        record = await storage.get_book(id)
        if record is None:
            return None
        return _book_from_record(record)


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema, context_getter=get_context)

app = FastAPI(title="Simple Books Server")
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/authors")
async def list_authors() -> list[dict[str, str]]:
    return [_author_payload(record) for record in await storage.list_authors()]


@app.get("/authors/{author_id}")
async def get_author(author_id: str) -> dict[str, str]:
    record = await storage.get_author(author_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return _author_payload(record)


@app.get("/books")
async def list_books() -> list[dict[str, str | dict[str, str]]]:
    return [await _book_payload(record) for record in await storage.list_books()]


@app.get("/books/{book_id}")
async def get_book(book_id: str) -> dict[str, str | dict[str, str]]:
    record = await storage.get_book(book_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return await _book_payload(record)
