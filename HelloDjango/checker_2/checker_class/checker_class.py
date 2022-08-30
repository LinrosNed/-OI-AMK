import requests as req
from bs4 import BeautifulSoup
from datetime import datetime
from .kma_land import KMALand, Land, PrelandNoAdminError
from .text_fixxer import DomFixxer
from .text_finder import TextAnaliz
from .check_list_view import CheckListView
from kma.models import PhoneNumber, OfferPosition, Language



class Check:
    DESCRIPTION = 'No'
    KEY_NAME = 'No'

    WARNING = 'warning'
    ERROR = 'error'
    INFO = 'info'

    STATUS_SET = {}

    def __init__(self, land, text_finder_result):
        self.land = land
        self.text_finder_result = text_finder_result
        self.errors = set()
        self.info = set()
        self.messages = list()

    def process(self):
        pass

    def add_mess(self, message_text, *args):
        message = {
            'text': message_text,
            'status': self.STATUS_SET[message_text],
            'items': args,
        }
        self.messages.append(message)


class PhoneCountryMask(Check):
    DESCRIPTION = 'Поиск моб кодов стран'
    KEY_NAME = 'phone_country_code'

    MASK_ON_LAND = 'Найден моб код'
    INCORECT_MASK_ON_LAND = 'Найден моб код другого гео'

    STATUS_SET = {
        MASK_ON_LAND: Check.WARNING,
        INCORECT_MASK_ON_LAND: Check.ERROR,
    }

    def process(self):
        phone_codes_on_land = self.text_finder_result['phone_codes']
        country_phone_code = '+' + self.land.phone_code
        for code in phone_codes_on_land:
            if code == country_phone_code:
                self.add_mess(self.MASK_ON_LAND, code)
            else:
                self.add_mess(self.INCORECT_MASK_ON_LAND, code)


class Currency(Check):
    DESCRIPTION = 'Поиск валют по тексту'
    KEY_NAME = 'currencies_on_land'

    NO_CURRENCIES = 'Валюты не найдены'
    MORE_ONE_CURRENCIES = 'Найдена валюта другой страны'
    ONE_CURR_FOUND = 'Найденая валюта'

    STATUS_SET = {
        NO_CURRENCIES: Check.WARNING,
        MORE_ONE_CURRENCIES: Check.ERROR,
        ONE_CURR_FOUND: Check.INFO,
    }

    def process(self):
        currency = self.land.curr.lower()
        currencies_on_land = self.text_finder_result['currencys']
        if not currencies_on_land:
            self.add_mess(self.NO_CURRENCIES)
        for curr in currencies_on_land:
            if curr == currency:
                self.add_mess(self.ONE_CURR_FOUND, curr.upper())
            if curr != currency and curr not in ['all','try', 'gel', 'peso']:
                self.add_mess(self.MORE_ONE_CURRENCIES, curr)


class OffersInLand(Check):
    DESCRIPTION = 'Поиск офферов по тексту'
    KEY_NAME = 'offers_on_land'

    NO_OFFER_FIND = 'Не найден не один оффер'
    MORE_ONE_OFFER_FOUND = 'Найдено больше одного оффера'
    ONE_OFFER_FOUND = 'Оффер'

    STATUS_SET = {
        NO_OFFER_FIND: Check.WARNING,
        MORE_ONE_OFFER_FOUND: Check.ERROR,
        ONE_OFFER_FOUND: Check.INFO
    }

    def process(self):
        offers_in_land = self.text_finder_result['offers']
        if not offers_in_land:
            self.add_mess(self.NO_OFFER_FIND)
        if len(offers_in_land) > 1:
            self.add_mess(self.MORE_ONE_OFFER_FOUND, *offers_in_land)
        if len(offers_in_land) == 1:
            self.add_mess(self.ONE_OFFER_FOUND, *offers_in_land)


class Dates(Check):
    DESCRIPTION = 'Поиск дат по тексту'
    KEY_NAME = 'dates_on_land'

    ALL_YEARS = 'Года'
    ALL_DATES = 'Даты'
    INCORRECT_DATE_FORMAT = 'Некоректный формат'
    INCORRECT_DATE = 'Некоректный день или месяц'
    FUTURE_DATE = 'Дата из будущего'
    EARLIEST_DATE = 'Самая ранняя дата'

    STATUS_SET = {
        ALL_YEARS: Check.INFO,
        ALL_DATES: Check.INFO,
        EARLIEST_DATE: Check.INFO,
        INCORRECT_DATE_FORMAT: Check.WARNING,
        INCORRECT_DATE: Check.ERROR,
        FUTURE_DATE: Check.ERROR,
    }

    def process(self):
        dates = self.text_finder_result['dates_on_land']
        # dates += ['00.12.20', '01.13.20', '20-12-20',]
        years = self.text_finder_result['years_on_land']
        if years:
            years.sort(key=lambda x: int(x))
            self.add_mess(self.ALL_YEARS, *years)
        if dates:
            self.add_mess(self.ALL_DATES, *dates)

        incorrect_format_dates = list(filter(self.is_incorrect_date_format, dates))
        if incorrect_format_dates:
            self.add_mess(self.INCORRECT_DATE_FORMAT, *incorrect_format_dates)

        incorrect_dates = list(filter(self.is_date_incorrect,dates))
        if incorrect_dates:
            self.add_mess(self.INCORRECT_DATE, *incorrect_dates)

        future_dates = list(filter(self.is_date_from_future, dates))
        if future_dates:
            self.add_mess(self.FUTURE_DATE, *future_dates)
        earliest_date = self.get_earliest_date(dates)
        if earliest_date:
            self.add_mess(self.EARLIEST_DATE, earliest_date)


    @staticmethod
    def is_incorrect_date_format(date):
        chars = '-\\/'
        for char in chars:
            if char in date:
                return True
    @staticmethod
    def make_date_point_delimeter(date: str) -> str:
        """Привести дату к формату хх.хх.хх"""
        new_date = ''
        for char in date:
            if char.isdigit():
                new_date += char
            else:
                new_date += '.'
        return new_date
    @staticmethod
    def make_date(date: str):
        """Создать обьект даты или вернуть None"""
        date = Dates.make_date_point_delimeter(date)
        correct_date = None
        for year_format in 'yY':
            try:
                correct_date = datetime.strptime(date, '%d.%m.%' + year_format).date()
            except ValueError:
                pass
        return correct_date
    @staticmethod
    def is_date_incorrect(date):
        """Правильный ли день и месяц у даты"""
        return not bool(Dates.make_date(date))
    @staticmethod
    def is_date_from_future(date: str):
        """Явзяеться ли дата датой из будущего"""
        date = Dates.make_date(date)
        if date:
            today = datetime.today().date()
            if date > today:
                return True
        return False

    @staticmethod
    def get_earliest_date(dates: list):
        dates_obj = []
        for date in dates:
            date = Dates.make_date(date)
            if date:
                dates_obj.append(date)
        dates_obj.sort()
        if dates_obj:
            earliest_date = dates_obj[0]
            return earliest_date.strftime('%d.%m.%Y')


class GeoWords(Check):
    DESCRIPTION = 'Поиск стран по тексту'
    KEY_NAME = 'countrys_in_land'

    ALL_COUNTRYS = 'Страны'
    INCORECT_COUNTRY = 'Другие страны'

    STATUS_SET = {
        ALL_COUNTRYS: Check.INFO,
        INCORECT_COUNTRY: Check.WARNING,
    }

    def process(self):
        countrys = self.text_finder_result['geo_words_templates']
        for iso, countrys in countrys.items():
            countrys.insert(0, iso.upper())
            if self.land.country == iso:
                self.add_mess(self.ALL_COUNTRYS, *countrys)
            else:
                self.add_mess(self.INCORECT_COUNTRY, *countrys)


class CountyLang(Check):
    DESCRIPTION = 'Правильный язык сайта'
    KEY_NAME = 'country_lang'

    INCORRECT_LANG = 'Указан не вырный язык сайта'

    STATUS_SET = {
        INCORRECT_LANG: Check.WARNING,
    }

    def process(self):
        site_lang = self.land.language
        list_of_langs = self.land.available_langs.split(',')
        if site_lang not in self.land.available_langs:
            self.add_mess(self.INCORRECT_LANG,'должен быть', *list_of_langs)



class UrlChecker:

    def __init__(self, source_text, url, user):
        self.land = KMALand(source_text, url, escape_chars=True)
        self.check_list = CheckListView(land=self.land, user=user)
        self.user = user

    def process(self):
        self.land.add_site_attrs()
        self.land.process()
        self.check_list.process()
        self.land.phone_code = PhoneNumber.get_phone_code_by_country(self.land.country)
        try:
            self.land.full_lang = Language.objects.get(pk=self.land.language)
        except Language.DoesNotExist:
            self.land.full_lang = 'no lang in BD'

    @staticmethod
    def text_analiz(land_text):
        data_for_text_analiz = UrlChecker.get_data_for_text_analiz()
        land = KMALand(source_text=land_text, url='0', parser='lxml')
        land.drop_tags_from_dom(KMALand.POLICY_IDS)
        # land.phone_code = PhoneNumber.get_phone_code_by_country(land.country)
        country_db_data = PhoneNumber.objects.get(short=land.country)
        land.phone_code = country_db_data.phone_code
        land.available_langs = country_db_data.langs
        human_text = land.get_human_land_text()
        analizer = TextAnaliz(source_text=str(land.soup.text), human_text=human_text.lower(), data=data_for_text_analiz)
        analizer.process()
        old_analizer_result = analizer.result
        messages = []
        for check in PhoneCountryMask, OffersInLand, Currency, Dates, GeoWords, CountyLang:
            check = check(land=land, text_finder_result=analizer.result)
            check.process()
            messages += check.messages
        statuses = set()
        for m in messages:
            statuses.add(m['status'])
        jeneral_status = ''
        if Check.INFO in statuses:
            jeneral_status = Check.INFO
        if Check.WARNING in statuses:
            jeneral_status = Check.WARNING
        if Check.ERROR in statuses:
            jeneral_status = Check.ERROR
        result = {
            'old': old_analizer_result,
            'new': messages,
            'jeneral_status': jeneral_status
        }
        return result


    @staticmethod
    def get_data_for_text_analiz():
        offers = OfferPosition.objects.values('name')
        offers_names = [offer['name'] for offer in offers]
        phones = PhoneNumber.objects.values('short', 'currency', 'phone_code', 'words')
        phone_codes = [phone['phone_code'] for phone in phones]
        currencys = [phone['currency'] for phone in phones]
        geo_words = {}
        geo_words_templates = {}
        for phone in phones:
            if phone['words']['words']:
                dic = {phone['short']: phone['words']['words']}
                geo_words.update(dic)
        for phone in phones:
            if phone['words']['templates']:
                dic = {phone['short']: phone['words']['templates']}
                geo_words_templates.update(dic)
        data_for_text_analiz = {
            'offers': offers_names,
            'currencys': currencys,
            'phone_codes': phone_codes,
            'geo_words': geo_words,
            'geo_words_templates': geo_words_templates,
        }
        return data_for_text_analiz
