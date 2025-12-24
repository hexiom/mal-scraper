# MyAnimeList Scraper

A scraper for MyAnimeList (MAL) created using [Selenium](https://www.selenium.dev/) in Python.

## Getting Started

Clone the repository using ```git clone```
```bash
git clone https://github.com/hexiom/mal-scraper.git
```

or click **Code** and "Download Zip" to download the repository.

### Prerequisites

[Selenium](https://www.selenium.dev/) is required for this project.

Install it using the [pip](https://pip.pypa.io/en/stable/) package manager.
```bash
python -m pip install selenium
```

### Usage
There are 3 different scripts for scraping anime reviews (mal_comment_scraper.py), anime details (mal_anime_scraper.py) and user details (mal_user_scraper.py)

```bash
python mal_anime_scraper.py [input-file] -u [urls] -v/--verbose -o [output-file]
```

```bash
python mal_comment_scraper.py -s [source-urls] -t [target-urls] -l [scrape-limit] -p [max-anime-pagination] -r [max-review-pagination] --headless -v/--verbose -o [output-file]
```

The user scraper (mal_user_scraper.py) is currently a WIP. It doesn't work and is a copy of the comment scraper.

## Built With

  - [Contributor Covenant](https://www.contributor-covenant.org/) - Used
    for the Code of Conduct
  - [MIT License](https://mit-license.org/) - Used to choose
    the license

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code
of conduct, and the process for submitting pull requests to us.

## Authors
  - **Hexiom** - Me

## License

This project is licensed under the [MIT License](LICENSE.md) - see the [LICENSE.md](LICENSE.md) file for details