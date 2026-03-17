# from collections.abc import Awaitable
# from contextvars import ContextVar
import logging
from fastapi import FastAPI
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


def _book_from_record(record: BookRecord) -> "Book":
    return Book(id=record.id, title=record.title, author_id=record.author_id)


async def _load_authors(author_ids: list[str]) -> list[Author | None]:
    return [
        _author_from_record(ar) for ar in await storage.get_authors_by_ids(author_ids)
    ]


# req_ctx_author_cache = ContextVar[DataLoader[str, "Author"] | None](
#     "req_ctx_author_cache", default=None
# )

# def get_author_loader() -> DataLoader[str, Author]:
#     authors_loader = req_ctx_author_cache.get()
#     if not authors_loader:
#         authors_loader = DataLoader[str, Author](load_fn=_load_authors)
#         req_ctx_author_cache.set(authors_loader)
#     return authors_loader
#
#
# def author_resolver(root: "Book") -> Awaitable[Author]:
#     return get_author_loader().load(root.author_id)


@strawberry.type
class Book:
    id: str
    title: str
    author_id: strawberry.Private[str]

    @strawberry.field
    async def author(self, info: Info["GraphQLContext", None]) -> Author | None:
        logger.debug(f"before loader for author id {self.author_id}")
        author = await info.context["author_loader"].load(self.author_id)
        logger.debug(f"after loader for author id {self.author_id}")
        return author

    # author_ctxvars: Author = strawberry.field(resolver=author_resolver)


storage: Storage = InMemoryStorage()


class GraphQLContext(TypedDict):
    author_loader: DataLoader[str, Author | None]


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
