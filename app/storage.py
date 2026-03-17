import asyncio
import random
from dataclasses import dataclass
from logging import Logger, getLogger
from typing import Protocol


@dataclass(frozen=True)
class AuthorRecord:
    id: str
    name: str


@dataclass(frozen=True)
class BookRecord:
    id: str
    title: str
    author_id: str


class Storage(Protocol):
    async def list_authors(self) -> list[AuthorRecord]: ...

    async def get_author(self, author_id: str) -> AuthorRecord | None: ...

    async def get_authors_by_ids(
        self, author_ids: list[str]
    ) -> list[AuthorRecord | None]: ...

    async def list_books(self) -> list[BookRecord]: ...

    async def get_book(self, book_id: str) -> BookRecord | None: ...


class InMemoryStorage:
    _DELAY_SECONDS_MIN = 0.100
    _DELAY_SECONDS_MAX = 0.300

    def __init__(self, logger: Logger | None = None) -> None:
        self._logger = logger or getLogger(__name__)
        self._authors: dict[str, dict[str, str]] = {
            "1": {"id": "1", "name": "J.R.R. Tolkien"},
            "2": {"id": "2", "name": "Frank Herbert"},
            "3": {"id": "3", "name": "William Gibson"},
        }
        self._books: dict[str, dict[str, str]] = {
            "1": {"id": "1", "title": "The Hobbit", "author_id": "1"},
            "2": {"id": "2", "title": "Dune", "author_id": "2"},
            "3": {"id": "3", "title": "Neuromancer", "author_id": "3"},
        }
        self._logger.debug(
            "Initialized in-memory storage with %s authors and %s books",
            len(self._authors),
            len(self._books),
        )

    async def list_authors(self) -> list[AuthorRecord]:
        await self._sleep()
        self._logger.debug("Listing all authors")
        return [self._author_from_row(row) for row in self._authors.values()]

    async def get_author(self, author_id: str) -> AuthorRecord | None:
        await self._sleep()
        self._logger.debug("Fetching author by id=%s", author_id)
        row = self._authors.get(author_id)
        if row is None:
            self._logger.debug("Author id=%s not found", author_id)
            return None
        return self._author_from_row(row)

    async def get_authors_by_ids(
        self, author_ids: list[str]
    ) -> list[AuthorRecord | None]:
        await self._sleep()
        self._logger.debug("Batch fetching authors for ids=%s", author_ids)
        return [
            self._author_from_row(row)
            if (row := self._authors.get(author_id))
            else None
            for author_id in author_ids
        ]

    async def list_books(self) -> list[BookRecord]:
        await self._sleep()
        self._logger.debug("Listing all books")
        return [self._book_from_row(row) for row in self._books.values()]

    async def get_book(self, book_id: str) -> BookRecord | None:
        await self._sleep()
        self._logger.debug("Fetching book by id=%s", book_id)
        row = self._books.get(book_id)
        if row is None:
            self._logger.debug("Book id=%s not found", book_id)
            return None
        return self._book_from_row(row)

    async def _sleep(self) -> None:
        await asyncio.sleep(
            random.uniform(self._DELAY_SECONDS_MIN, self._DELAY_SECONDS_MAX)
        )

    def _author_from_row(self, row: dict[str, str]) -> AuthorRecord:
        return AuthorRecord(id=row["id"], name=row["name"])

    def _book_from_row(self, row: dict[str, str]) -> BookRecord:
        if row["author_id"] not in self._authors:
            self._logger.error(
                "Book id=%s references missing author id=%s",
                row["id"],
                row["author_id"],
            )
            raise ValueError(f"Missing author {row['author_id']} for book {row['id']}")
        return BookRecord(id=row["id"], title=row["title"], author_id=row["author_id"])
