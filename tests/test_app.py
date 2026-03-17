from fastapi.testclient import TestClient

from app import main
from app.storage import AuthorRecord, BookRecord


client = TestClient(main.app)


def test_list_books_returns_seed_data() -> None:
    response = client.get("/books")

    assert response.status_code == 200
    assert len(response.json()) == 3
    assert response.json()[0]["author"]["name"] == "J.R.R. Tolkien"


def test_get_single_book() -> None:
    response = client.get("/books/2")

    assert response.status_code == 200
    assert response.json()["title"] == "Dune"
    assert response.json()["author"]["name"] == "Frank Herbert"


def test_get_single_author() -> None:
    response = client.get("/authors/3")

    assert response.status_code == 200
    assert response.json()["name"] == "William Gibson"


def test_graphql_books_query() -> None:
    response = client.post(
        "/graphql",
        json={"query": "{ books { id title author { id name } } }"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["books"][0]["title"] == "The Hobbit"
    assert body["data"]["books"][0]["author"]["name"] == "J.R.R. Tolkien"


def test_graphql_book_author_uses_batch_loader() -> None:
    class SpyStorage:
        def __init__(self) -> None:
            self.batch_calls: list[list[str]] = []

        async def list_authors(self) -> list[AuthorRecord]:
            return [
                AuthorRecord(id="1", name="J.R.R. Tolkien"),
                AuthorRecord(id="2", name="Frank Herbert"),
            ]

        async def get_author(self, author_id: str) -> AuthorRecord | None:
            authors = {author.id: author for author in await self.list_authors()}
            return authors.get(author_id)

        async def get_authors_by_ids(
            self, author_ids: list[str]
        ) -> list[AuthorRecord | None]:
            self.batch_calls.append(author_ids)
            authors = {author.id: author for author in await self.list_authors()}
            return [authors.get(author_id) for author_id in author_ids]

        async def list_books(self) -> list[BookRecord]:
            return [
                BookRecord(id="1", title="The Hobbit", author_id="1"),
                BookRecord(id="2", title="Dune", author_id="2"),
            ]

        async def get_book(self, book_id: str) -> BookRecord | None:
            books = {book.id: book for book in await self.list_books()}
            return books.get(book_id)

    original_storage = main.storage
    spy_storage = SpyStorage()
    main.storage = spy_storage

    try:
        response = client.post(
            "/graphql",
            json={"query": "{ books { id author { name } } }"},
        )
    finally:
        main.storage = original_storage

    assert response.status_code == 200
    assert response.json()["data"]["books"][1]["author"]["name"] == "Frank Herbert"
    assert spy_storage.batch_calls == [["1", "2"]]
