from django.db import models
from ordered_model.models import OrderedModel
from django.contrib.auth.models import User


# Create your models here.
class CheckBlock(OrderedModel):
    name = models.CharField(max_length=100, verbose_name='Название')
    manual_link = models.CharField(max_length=50, verbose_name='ссылка на доку', blank=True)

    class Meta:
        verbose_name = 'Блок проверки'
        verbose_name_plural = 'Блоки проверки'
        ordering = ['order']

    def __str__(self):
        return self.name


class CheckPoint(OrderedModel):
    LAND_TYPES = ('land', 'Лэндинг'), ('preland', 'Прэлендинг')
    DISCOUNT_TYPE = ('free', 'Бесплатно'), ('low_price', 'Лоу-прайс')

    text = models.CharField(max_length=255, verbose_name='Описание пункта проверки')
    parent = models.ForeignKey(CheckBlock, on_delete=models.CASCADE)
    land_type = models.CharField(
        max_length=20,
        verbose_name='Тип сайта',
        choices=LAND_TYPES,
        null=True,
        blank=True,
    )

    discount_type = models.CharField(
        max_length=20,
        verbose_name='Тип скидки',
        choices=DISCOUNT_TYPE,
        null=True,
        blank=True,
    )
    for_geo = models.CharField(
        max_length=255,
        verbose_name='Только для гео',
        blank=True,
    )
    for_lang = models.CharField(
        max_length=255,
        verbose_name='Только для языка',
        blank=True,
    )
    is_notice = models.BooleanField(default=False, null=False, blank=True, verbose_name='Требует внимания')
    filter = models.CharField(max_length=30, verbose_name='Прочий фильтр', default='', null=False, blank=True)
    manual_link = models.CharField(max_length=50, verbose_name='ссылка на доку', blank=True)

    class Meta:
        verbose_name = 'Пункт проверки'
        verbose_name_plural = 'Пункты проверки'
        ordering = ['order']

    def save(self):
        super().save()
        actual_lists = ActualUserList.objects.all()
        for user_list in actual_lists:
            user_check_point = UserSiteCheckPoint(user_list=user_list, check_point=self)
            user_check_point.save()

    def __str__(self):
        return self.text

class ActualUserList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    url = models.CharField(max_length=70)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'url']


class UserSiteCheckPoint(models.Model):
    check_point = models.ForeignKey(CheckPoint, on_delete=models.CASCADE)
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    # url = models.CharField(max_length=70)
    user_list = models.ForeignKey(ActualUserList, on_delete=models.CASCADE)
    is_checked = models.BooleanField(default=False)

    class Meta:
        # verbose_name = 'Пункт проверки'
        # verbose_name_plural = 'Пункты проверки'
        ordering = ['check_point__order']
        unique_together = ['check_point', 'user_list']

    @staticmethod
    def make_user_url_list(user_list):
        """Создать чеклист проверки под конкрентый сайт и пользователя"""
        all = CheckPoint.objects.all()
        new_check_list = list()
        for check_point in all:
            u = UserSiteCheckPoint(check_point=check_point, user_list=user_list)
            new_check_list.append(u)
        new_list = UserSiteCheckPoint.objects.bulk_create(new_check_list)
        new_dic = {check_point.__dict__['check_point_id']: check_point.__dict__ for check_point in new_list}
        return new_dic

    @staticmethod
    def get_user_ckecklist_dict(user_list):
        """Получить чеклист пользователя для сайта"""
        all = UserSiteCheckPoint.objects.filter(user_list=user_list).values()
        user_dict_checklist = {check_point['check_point_id']: check_point for check_point in all}
        return user_dict_checklist

    @staticmethod
    def get_list(user_model, url):
        try:
            user_list = ActualUserList.objects.get(user=user_model, url=url)
            user_check_list = UserSiteCheckPoint.get_user_ckecklist_dict(user_list=user_list)
        except ActualUserList.DoesNotExist as error:
            new_ckeck_list_record = ActualUserList(user=user_model, url=url)
            new_ckeck_list_record.save()
            user_check_list = UserSiteCheckPoint.make_user_url_list(user_list=new_ckeck_list_record)
        return user_check_list

    # def __str__(self):
    #     return self.text


class CheckerUserSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    left_bar = models.BooleanField(default=True, verbose_name='Показывать боковую панель')
    click_elem = models.BooleanField(default=False, verbose_name='Показывать клик элементы')
    other = models.BooleanField(default=True, verbose_name='Показывать даты, формы')

    def __str__(self):
        return f'{self.user}-{self.left_bar}-{self.click_elem}-{self.other}'

