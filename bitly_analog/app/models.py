"""
Definition of models.
"""

from django.db import models

# Глобальные переменные

STOP_STR = 10   # число первых символов отображении оригинального URL в методе __str__


# Create your models here.

class Url(models.Model):
    ''' Модель данных для хранения параметров правила сокращения ссылки. '''
    global STOP_STR

    full = models.URLField('Оригинальный URL')
    date_end = models.DateField('Дата удаления правила')     
    short = models.CharField('Короткая cсылка', max_length=101)
    subpart = models.CharField('Субдомен', max_length=50)
    # time_start = models.DateTimeField('Дата и время начала действия правила')     
    # ttl = models.DurationField('Период действия правила')

    def __str__(self):
        ''' Строковое представление модели. ''' 
        return 'URL: ' + self.full[:STOP_STR] + ('...' if len(self.full) > STOP_STR else '') + self.short

    def to_json(self):
        ''' Сведения об объекте модели. '''
        return {
            'id': self.id,
            'full': self.full,
            'short': self.short,
            'ttl': self.ttl,
        }
