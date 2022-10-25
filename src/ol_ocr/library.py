from dataclasses import dataclass

import httpx
import isbnlib

from .database import create_db_if_needed, db_conn, transaction


class BookNotInDatabaseError(Exception):
    pass


DB_FILE = create_db_if_needed()
print(DB_FILE)


@dataclass
class Author:
    """Represents an author."""

    url: str
    """Main url for the author"""
    name: str
    """Full name of the author"""


@dataclass
class Book:
    """Represents an openlibrary book."""

    url: str
    """Main url for the book"""
    isbn: str
    """Either ISBN13 or ISBN10"""
    title: str
    """Book title"""
    subtitle: str | None
    """Book subtitle; may be empty."""
    authors: list[Author]
    """Set of author strings."""
    subjects: set[str]
    """Set of subject strings."""
    cover_url: str | None
    """Url of largest cover image."""

    @classmethod
    def from_openlibrary(cls, isbn: isbnlib.Isbn):
        """Create a new Book instance by getting the data from openlibrary."""
        book = fetch_openlibrary_book(isbn)
        covers = book["cover"]
        return cls(
            url=book["url"],
            isbn=isbn.canonical,
            title=book["title"],
            subtitle=book.get("subtitle", None),
            authors=[Author(a["url"], a["name"]) for a in book["authors"]],
            subjects=set([s["name"] for s in book["subjects"]]),
            cover_url=covers.get("large", None),
        )

    @classmethod
    def from_db(cls, isbn: isbnlib.Isbn | str):
        """Create `Book` from database."""
        try:
            isbn = isbn.canonical  # type: ignore
        except AttributeError:
            pass

        with db_conn(DB_FILE) as conn:
            cur = conn.execute(
                """SELECT id, url, isbn, title, subtitle, cover_url
                   FROM book WHERE isbn = ?""",
                (isbn,),
            )
            result = cur.fetchone()
            if not result:
                raise BookNotInDatabaseError(isbn)
            b_id, url, isbn, title, subtitle, cover_url = result
            cur.execute(
                """SELECT url, name FROM author a
                   JOIN book_author ba ON a.id = ba.a_id
                   WHERE ba.b_id = ?""",
                (b_id,),
            )
            authors = []
            for author_row in cur.fetchall():
                a_url, a_name = author_row
                authors.append(Author(a_url, a_name))

            cur.execute(
                """SELECT sub_name FROM subject s
                   JOIN book_subject bs ON s.id = bs.s_id
                   WHERE bs.b_id = ?""",
                (b_id,),
            )
            subjects = set()
            for subject_row in cur.fetchall():
                subjects.add(subject_row[0])

            return cls(url, isbn, title, subtitle, authors, subjects, cover_url)

    def save(self):
        """Write `Book` to database."""
        with db_conn(DB_FILE) as conn:
            cur = conn.execute("SELECT id FROM book WHERE isbn = ?", (self.isbn,))
            result = cur.fetchone()
            if not result:
                with transaction(conn):
                    cur = conn.execute(
                        """INSERT INTO book (url, isbn, title, subtitle, cover_url)
                           VALUES (?,?,?,?,?) ON CONFLICT (url) DO NOTHING""",
                        (
                            self.url,
                            self.isbn,
                            self.title,
                            self.subtitle,
                            self.cover_url,
                        ),
                    )
                b_id = cur.lastrowid
            else:
                b_id = result[0]

            for author in self.authors:
                cur.execute("SELECT id from author where url = ?", (author.url,))
                result = cur.fetchone()
                if not result:
                    cur.execute(
                        """INSERT INTO author (url, name) VALUES (?,?)
                           ON CONFLICT (url) DO NOTHING""",
                        (author.url, author.name),
                    )
                    a_id = cur.lastrowid
                else:
                    a_id = result[0]

                cur.execute(
                    """INSERT INTO book_author (b_id, a_id) VALUES (?,?)
                       ON CONFLICT DO NOTHING""",
                    (b_id, a_id),
                )

            for subject in self.subjects:
                cur.execute("SELECT id from subject where sub_name = ?", (subject,))
                result = cur.fetchone()
                if not result:
                    cur.execute(
                        """INSERT INTO subject (sub_name) VALUES (?)
                           ON CONFLICT (sub_name) DO NOTHING""",
                        (subject,),
                    )
                    s_id = cur.lastrowid
                else:
                    s_id = result[0]
                cur.execute(
                    """INSERT INTO book_subject (b_id, s_id) VALUES (?,?)
                       ON CONFLICT DO NOTHING""",
                    (b_id, s_id),
                )
            conn.commit()


def fetch_openlibrary_book(isbn: isbnlib.Isbn):
    """Request book from openlibrary."""
    key = f"ISBN:{isbn.canonical}"
    url = f"https://openlibrary.org/api/books?bibkeys={key}&format=json&jscmd=data"
    try:
        resp = httpx.get(url)
        resp_data = resp.json()
        book = resp_data[key]
    except Exception as e:
        print(key)
        print(url)
        print(resp.status_code)
        print(resp.headers)
        raise e
    return book


def find_isbn(text: str) -> isbnlib.Isbn | None:
    """Return ISBN or None."""
    try:
        return isbnlib.Isbn(isbnlib.get_isbnlike(text)[0])
    except IndexError:
        pass
    except isbnlib.NotValidISBNError:
        pass
    return None


if __name__ == "__main__":
    isbn = isbnlib.Isbn("9780226550275")
    # book = Book.from_db(isbn)
    book = Book.from_openlibrary(isbn)
    book.save()
    print(book)
