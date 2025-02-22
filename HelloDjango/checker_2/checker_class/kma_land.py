from bs4 import BeautifulSoup
import re
import json
from json import JSONDecodeError
import requests as req
from .text_fixxer import DomFixxer
from django.conf import settings

class PrelandNoAdminError(BaseException):
    """Прелэндинг не подключен к админке (нет ?ufl=)"""



class Land:
    TYPES_REL = ['shortcut icon', 'icon', 'apple-touch-icon', 'apple-touch-icon-precomposed', 'image/x-icon']

    def __init__(self, source_text, url, *, parser='html5lib', escape_chars=False):
        self.source_text = Land.re_escape_html_chars(source_text) if escape_chars else source_text
        self.url = url
        self.soup = BeautifulSoup(self.source_text, parser)
        self.human_text = None
        self.img_doubles = None

    def get_no_protocol_url(self):
        return self.url.replace('http://', '')

    def _get_title(self):
        """найти title сайта"""
        title = self.soup.find('title')
        return title.text

    def _is_video_tag_on_site(self):
        """Есть ли на сайте тэг video"""
        if self.soup.find_all('video'):
            return True

    def get_favicon_links(self, add_base_url=True):
        links = self.soup.find_all('link')
        links = list(filter(self.is_favicon_links,links))
        if add_base_url:
            for l in links:
                if not l['href'].startswith('http'):
                    l['href'] = Land.get_url_for_base_tag(self.url) + l['href']
                yield str(l)
        

    @staticmethod
    def is_favicon_links(link):
        res = []
        for attr in ['rel', 'type']:
            try:
                a = link[attr]
                if isinstance(a, str):
                    res.append(a)
                if isinstance(a, list):
                    res.extend(a)
            except KeyError:
                pass
        for attr in res:
            if attr in Land.TYPES_REL:
                return True

    @property
    def scripts(self):
        for script in self.soup.find_all('script'):
            yield str(script)

    @staticmethod
    def re_escape_html_chars(html_text):
        chars = [('&copy;', '©'),('&#8211;', '-'), ('&#8220;', '“'), ('&#8221;', '”'), ('&#39;', "'"), ('&nbsp;', ' '), ('&quot;', '"'),
                 ('&apos;', "'"),
                 ('&&', '@@'), ('&', '&amp;&amp;'), ('@@', '&&')]
        for char, chat_to in chars:
            html_text = html_text.replace(char, chat_to)
        return html_text

    @staticmethod
    def escape_html_for_iframe(html_text):
        chars = [
            # ('&', '&amp;&amp;'),
            ('"', '&quot;'), ("'", '&apos;')]
        for char, chat_to in chars:
            html_text = html_text.replace(char, chat_to)
        return html_text

    @staticmethod
    def get_url_for_base_tag(url):
        if '?' in url:
            url = url.split('?')[0]
        if not url.endswith('/'):
            url += '/'
        return url

    def add_style_tag(self, style_text):
        DomFixxer.add_css(self.soup, style_text)

    def add_script_tag(self, scritp_text):
        DomFixxer.add_js(self.soup, scritp_text)

    def add_base_tag(self):
        url_base_tag = self.get_url_for_base_tag(self.url)
        DomFixxer.add_base_tag(self.soup, url_base_tag)

    def find_n_mark_img_doubles(self):
        base_url = self.get_url_for_base_tag(self.url)
        self.img_doubles = DomFixxer.find_double_img(self.soup, base_url=base_url)

    def drop_tags_from_dom(self, elems_ids):
        for id in elems_ids:
            elem = self.soup.find(id=id)
            if elem:
                elem.decompose()

    def get_human_land_text(self):
        clean_land_text = self.soup.text
        clean_land_text += ' ' + self.title
        inputs = self.soup.find_all('input')
        placeholders_text = ['']
        for inpt in inputs:
            try:
                placeholder = inpt['placeholder']
                placeholders_text.append(placeholder)
            except KeyError:
                pass
        placeholders_text = ' '.join(placeholders_text)
        clean_land_text += placeholders_text
        return clean_land_text

    @property
    def title(self):
        return self._get_title()

    def is_yam_script(self):
        yam_link = 'https://mc.yandex.ru/metrika'
        for script in self.scripts:
            if yam_link in script:
                return True


class KMALand(Land):
    """Сайт KMA"""
    PRE_LAND_DOMAINS = ['blog-feed.org']
    LAND_ADMIN_UTM = 'ufl='
    POLICY_IDS = ['polit', 'agreement']
    STYLES_FILE = str(settings.BASE_DIR) + '/checker_2/checker_class/front_data/styles.css'
    JS_FILE = str(settings.BASE_DIR) + '/checker_2/checker_class/front_data/script.js'

    def __init__(self, source_text, url, **kwargs):
        super().__init__(source_text=source_text, url=url, **kwargs)
        self.__kma_script = self._find_kma_back_data()
        self.country = self._country()
        self.language = self._language()
        self.country_list = self._country_list()
        self.list_of_parameters = self._list_of_parameters()
        self.list_of_form_parameters = self._list_of_form_parameters()
        self.land_attrs = list()

    def get_clean_url(self):
        url = super().get_no_protocol_url()
        for domain in KMALand.PRE_LAND_DOMAINS:
            url = url.replace(domain, '')
        if url.startswith('/'):
            url = url[1:]
        if url.endswith('/'):
            url = url[:-1]
        return url

    @staticmethod
    def format_url(url):
        url = url.strip()
        url = url.replace('https://', 'http://')
        return url

    def _find_kma_back_data(self) -> str:
        """Ищет и возвражает тело скрипта с переменными для лэндинга"""
        # soup = BeautifulSoup(self.source_text, 'html5')
        # scripts = soup.find_all('script')
        for script in self.scripts:
            # print(script)
            # print('country_list' in script)
            if 'country_list' in script:
                return script

    def _country(self) -> str:
        """Поиск в js коде переменной country - возвращает ее значение"""
        block = re.search(r"country='\w\w'", self.__kma_script)
        country_w_brackets = re.search(r"'\w\w'", block.group(0))
        country = country_w_brackets.group(0).replace("'", '')
        return country.lower()

    def _language(self) -> str:
        """Поиск в js коде переменной language - возвращает ее значение"""
        block = re.search(r'"language":"\w\w"', self.__kma_script)
        language_w_brackets = re.search(r'"\w\w"', block.group(0))
        language = language_w_brackets.group(0).replace('"', '')
        return language.lower()

    def _country_list(self) -> dict:
        """Поиск в js коде переменной country_list - возвращает ее значение"""
        start = self.__kma_script.find('country_list=') + len('country_list=')
        end = self.__kma_script.find('}};') + 2
        var = self.__kma_script[start:end]
        country_list = json.loads(var)
        dic = dict()
        for k, v in country_list.items():
            dic[k.lower()] = v
        return dic

    def _list_of_parameters(self) -> dict:
        """Поиск в js коде переменной list_of_parameters - возвращает ее значение"""
        start = self.__kma_script.find('list_of_parameters=') + len('list_of_parameters=')
        if start == -1:
            return dict()
        end = self.__kma_script.find('};',start) + 1
        var = self.__kma_script[start:end]
        try:
            list_of_parameters = json.loads(var)
        except JSONDecodeError:
            return dict()
        dic = dict()
        for k, v in list_of_parameters.items():
            dic[k.lower()] = v
        return dic

    def _list_of_form_parameters(self) -> dict:
        # for preland
        """Поиск в js коде переменной list_of_form_parameters - возвращает ее значение"""
        start = self.__kma_script.find("list_of_form_parameters='") + len("list_of_form_parameters='")
        end = self.__kma_script.find("';", start) + 0
        var = self.__kma_script[start:end]
        try:
            list_of_form_parameters = json.loads(var)
        except JSONDecodeError:
            return dict()
        dic = dict()
        for k, v in list_of_form_parameters.items():
            dic[k.lower()] = v
        return dic


    def add_site_attrs(self):
        if self._is_video_tag_on_site():
            self.land_attrs.append('video')

        if len(self.country_list) > 1:
            self.land_attrs.append('more_one_select')

    def process(self):
        self.find_n_mark_img_doubles()


    @property
    def iframe_srcdoc(self):
        with open(self.STYLES_FILE, encoding='utf-8') as file:
            style_text = file.read()
            self.add_style_tag(style_text)
        with open(self.JS_FILE, encoding='utf-8') as file:
            js_text = file.read()
            self.add_script_tag(js_text)
        self.add_base_tag()
        html_code = str(self.soup)
        html_code = self.escape_html_for_iframe(html_code)
        return html_code

    def is_social_script(self):
        socialFish = 'duhost'
        for script in self.scripts:
            if socialFish in script:
                return True

    @property
    def discount_type(self):
        """Получить тип скидки"""
        discount = self.country_list[self.country]['discount']
        if int(discount) > 50:
            return 'low_price'
        else:
            return 'full_price'

    @property
    def land_type(self):
        """Получить тип сайта"""
        for domain in self.PRE_LAND_DOMAINS:
            if domain in self.url:
                if KMALand.LAND_ADMIN_UTM not in self.url:
                    raise PrelandNoAdminError
                return 'preland'
        return 'land'

    @property
    def s1(self):
        return self.country_list[self.country]['s1']

    @property
    def s2(self):
        return self.country_list[self.country]['s2']

    @property
    def s3(self):
        return self.country_list[self.country]['s3']

    @property
    def s4(self):
        return self.country_list[self.country]['s4']

    @property
    def discount(self):
        return self.country_list[self.country]['discount']

    @property
    def curr(self):
        return self.country_list[self.country]['curr']

    @property
    def offer_id(self):
        if self.list_of_form_parameters:
            return self.list_of_form_parameters['offer_id']
        else:
            return self.list_of_parameters['offer_id']

    @property
    def landing_id(self):
        return self.list_of_parameters['landing']
    @property
    def preland_id(self):
        return self.list_of_form_parameters['transit']

    @property
    def get_land_admin_url(self):
        if self.land_type == 'land':
            kma_land_url = f'https://cpanel.kma.biz/offer/module/landing/update?offer_id={self.offer_id}&id={self.landing_id}'
            return kma_land_url
        else:
            kma_preland_url = f'https://cpanel.kma.biz/offer/module/transit/update?offer_id={self.offer_id}&id={self.preland_id}'
            return kma_preland_url


if __name__ == '__main__':
    url = 'https://blog-feed.org/elle-breasty/?ufl=14926'
    res = req.get(url)
    kma = Land(res.text, url)
