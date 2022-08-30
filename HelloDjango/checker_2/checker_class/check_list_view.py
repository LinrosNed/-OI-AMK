from checker_2.models import CheckPoint, CheckBlock, UserSiteCheckPoint, ActualUserList


class CheckListView:

    def __init__(self, *, land, user):
        self.land_type = land.land_type
        self.discount_type = land.discount_type
        self.country = land.country
        self.language = land.language
        self.user = user
        self.url = land.url
        self.land_attrs = land.land_attrs
        self.check_list = list()

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i == len(self.check_list):
            raise StopIteration
        block = self.check_list[self.i]
        self.i += 1
        return block

    def is_need_add(self, check_point):
        if check_point.land_type in [self.land_type, None] and \
                check_point.discount_type in [self.discount_type, None] and \
                (self.country in check_point.for_geo or check_point.for_geo == '') and \
                (self.language in check_point.for_lang or check_point.for_lang == '') and \
                (check_point.filter in self.land_attrs or check_point.filter == ''):
            return True

    def process(self):
        all = CheckBlock.objects.prefetch_related('checkpoint_set').all()
        user_check_list = UserSiteCheckPoint.get_list(user_model=self.user, url=self.url)
        for b in all:
            dic = {
                'name': b.name,
                'manual_link': b.manual_link,
                'subs': []
            }
            for c in b.checkpoint_set.all():
                if self.is_need_add(c):
                    c.is_checked = user_check_list[c.id]['is_checked']
                    dic['subs'].append(c)
            # если блок чеклиста имеет пункты проверки(не пуст)
            if dic['subs']:
                self.check_list.append(dic)
