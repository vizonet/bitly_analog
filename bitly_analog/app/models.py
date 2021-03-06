"""
Definition of models.
"""

from django.db import models
from django.utils import timezone
from django.contrib.sessions.models import Session


# Create your models here.

class Owner(models.Model):
    """ Модель БД. Хранит пользователей и их настройки на основе ключа сеанса Django. """
    session = models.ForeignKey(Session, on_delete=models.CASCADE)                   # связь с таблицей сеансов Session
    url_ttl = models.PositiveSmallIntegerField('Время жизни правила (в сутках)', default=1)
    trows_on_page = models.PositiveSmallIntegerField('Число строк таблицы правил на странице', default=3)

    def __str__(self):
        """ Строковое представление модели. """
        return 'Пользователь: {}...{}'.format(self.session.session_key[:4], self.session.session_key[-3:])


class Url(models.Model):
    """ Модель БД. Хранит параметры правил сокращения ссылок. """
    link = models.URLField('Оригинальная ссылка')
    alias = models.CharField('Алиас', max_length=100)
    subpart = models.CharField('Субдомен', max_length=40)
    expire_date = models.DateField('Дата удаления правила')     
    str_limit = models.PositiveSmallIntegerField('Число первых символов отображения оригинального URL в методе __str__'
                                                 , default=40)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)                   # связь с таблицей пользователей Owner

    def to_json(self):
        """ Сведения об объекте модели в формате JSON. """
        return {
            'id': self.id,
            'link': self.link,
            'alias': self.alias,
            'owner': self.owner,
            'subpart': self.subpart,
            'str_limit': self.str_limit,
            'expire_date': self.expire_date,
        }

    def __str__(self):
        """ Строковое представление модели. """
        return str(self.owner) + ' | алиас: <' + self.alias + '> | URL: <' + self.link[:self.str_limit] \
            + (' ...' if len(self.link) > self.str_limit else '') + '>'


class Collection(models.Model):
    """ Модель БД. Хранит связи пользователей c их правилами сокращения ссылок. """
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)                   # связь с таблицей пользователей Owner
    url = models.ForeignKey(Url, on_delete=models.CASCADE, null=True)            # связь с таблицей правил Url

    def __str__(self):
        """ Строковое представление модели. """
        return 'Правило: {} | Пользователь: {}'.format(self.url, self.owner)


class Log(models.Model):
    """ Модель БД. Хранит статистику выполнения операций пользователями и приложением. """
    date_time = models.DateTimeField('Дата и время операции', default=timezone.now)
    owner = models.ForeignKey(Owner, null=True, on_delete=models.SET_NULL)       # связь с таблицей пользователей Owner
    process = models.CharField('Имя процесса', max_length=100)
    execute = models.TextField('Что выполнено')

    def __str__(self):
        """ Строковое представление модели. """
        return '{}: {} | {} | {}'.format(self.date_time, self.owner, self.process, self.execute)
