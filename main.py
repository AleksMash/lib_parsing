from pathlib import Path

import requests


def dload_picture(url, filename):
    response = requests.get(url)
    response.raise_for_status()
    with open(filename, 'wb') as file:
        file.write(response.content)


def dload_book(url, filename):
    print(url)
    response = requests.get(url)
    response.raise_for_status()
    with open(filename, 'wt') as file:
        file.write(response.text)


def dload_books():
    Path('books').mkdir(parents=True, exist_ok=True)
    for i in range(1,11):
        dload_book(f'https://tululu.org/txt.php?id={i}',
                   f'books/book-{i}.txt')


if __name__ == "__main__":
    dload_books()