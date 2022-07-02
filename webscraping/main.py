from scrapper import Scrapper
from dateutil import parser


def main():
    looker = Scrapper(
        property_type='mieszkanie',  # dom
        deal_type='sprzedaz',  # wynajem
        max_search=250,  # -1
    )
    looker.scrap_pages()


if __name__ == "__main__":
    main()
