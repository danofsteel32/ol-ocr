PRAGMA foreign_keys = ON;

CREATE TABLE book (
    id INTEGER PRIMARY KEY,
    isbn TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    subtitle TEXT,
    cover_url TEXT UNIQUE
);

CREATE TABLE author (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE subject (
    id INTEGER PRIMARY KEY,
    sub_name TEXT NOT NULL UNIQUE
);


CREATE TABLE book_author (
    b_id INTEGER,
    a_id INTEGER,
    FOREIGN KEY (b_id) REFERENCES book (id),
    FOREIGN KEY (a_id) REFERENCES author (id),
    PRIMARY KEY (b_id, a_id)
);

CREATE TABLE book_subject (
    b_id INTEGER,
    s_id INTEGER,
    FOREIGN KEY (b_id) REFERENCES book (id),
    FOREIGN KEY (s_id) REFERENCES subject (id),
    PRIMARY KEY (b_id, s_id)
);
