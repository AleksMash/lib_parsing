import argparse
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename, sanitize_filepath
from retry import retry


def parse_book_page(html, page_url):
    """Return dict with parsed book data:
        title, author, genres (list), comments (list), image file name, title image URL
    Arguments:
        html - html (str) content of the web page.
        page_url - URL of the page"""
    soup = BeautifulSoup(html, "lxml")
    splitted_text = soup.select("h1")[0].text.split("::")
    book_title, author = map(lambda s: s.strip(), splitted_text)
    img_path = soup.select_one("div.bookimage img")["src"]
    img_url = urljoin(page_url, img_path)
    img_file_name = os.path.basename(unquote(img_path))
    comments_tags = soup.select("div.texts")
    comments = [c.span.text for c in comments_tags]
    genre_tags = soup.select("span.d_book a")
    genres = [a.text for a in genre_tags]
    return {
        "title": book_title,
        "author": author,
        "img_url": img_url,
        "comments": comments,
        "genres": genres,
        "img_file_name": img_file_name,
    }


@retry(requests.ConnectionError, jitter=0.5, tries=5)
def download_image(url, filename):
    """!!! filename must be a valid path
    to the image file. Ensure that it is properly prepared!!!"""
    response = requests.get(url)
    response.raise_for_status()
    if not os.path.exists(filename):
        with open(filename, "wb") as file:
            file.write(response.content)


@retry(requests.ConnectionError, jitter=0.5, tries=5)
def download_book(url, params, filename):
    """!!! filename must be a valid path
    to the *.txt file !!! Ensure that it is properly prepared"""
    response = get_response(url, params)
    with open(filename, "wt", encoding="UTF-8") as file:
        file.write(response.text)
    return response


@retry(requests.ConnectionError, jitter=0.5, tries=5)
def get_response(url, params=None):
    response = requests.get(url, params=params)
    response.raise_for_status()
    if response.history:
        raise requests.HTTPError
    return response


def main():
    parser = argparse.ArgumentParser(description="Load txt books from tululu.org")
    parser.add_argument("first_id", type=int, help="ID первой книги")
    parser.add_argument("last_id", type=int, help="ID последней книги")
    parser.add_argument(
        "-f",
        "--folder",
        type=str,
        default="books",
        help="папка, в которую будут скачаны книги",
    )
    args = parser.parse_args()
    first_id = args.first_id
    last_id = args.last_id
    folder = args.folder
    if last_id < first_id:
        print("ID2 должен быть больше или равен ID1")
        return
    Path("images").mkdir(parents=True, exist_ok=True)
    san_folder = sanitize_filepath(folder)
    Path(san_folder).mkdir(parents=True, exist_ok=True)
    comments_delimiter = ", \n"
    for book_id in range(first_id, last_id + 1):
        try:
            response = get_response(f"https://tululu.org/b{book_id}/")
        except requests.HTTPError as e:
            print(
                "Не удается найти главную страницу книги по адресу:"
                f"https://tululu.org/b{book_id}/",
                file=sys.stderr,
            )
        except requests.ConnectionError as e:
            print("Проблема с интернет-соединением", file=sys.stderr)
            print(e)
            sys.exit()
        else:
            book_parsed = parse_book_page(response.text, response.url)
            filepath = os.path.join(
                san_folder, sanitize_filename(f'{book_id}. {book_parsed["title"]}.txt')
            )
            try:
                params = {"id": book_id}
                response = download_book("https://tululu.org/txt.php", params, filepath)
            except requests.HTTPError as e:
                print(
                    f"Не удается скачать книгу с URL: {response.url}", file=sys.stderr
                )
            except requests.ConnectionError as e:
                print("Проблема с интернет-соединением", file=sys.stderr)
                print(e)
                sys.exit()
            try:
                download_image(
                    book_parsed["img_url"],
                    os.path.join("images", book_parsed["img_file_name"]),
                )
            except requests.HTTPError as e:
                print(
                    f'Не удается скачать изображение с URL: {book_parsed["img_url"]}',
                    file=sys.stderr,
                )
            except requests.ConnectionError as e:
                print("Проблема с интернет-соединением", file=sys.stderr)
                print(e)
                sys.exit()
            info_file_path = os.path.join(san_folder, f"{book_id}. info.txt")
            with open(info_file_path, "wt") as file:
                file.write(f'Наименование: {book_parsed["title"]}\n')
                file.write(f'Автор: {book_parsed["author"]}\n')
                file.write(f"Путь к файлу книги: {os.path.abspath(filepath)}\n")
                file.write(f'Жанры: {", ".join(book_parsed["genres"])}\n\n')
                file.write(
                    f'Комментарии:\n\n{comments_delimiter.join(book_parsed["comments"])}'
                )


if __name__ == "__main__":
    main()
