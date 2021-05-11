""" Definition of views. """

import json, time, threading, inspect

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, Http404
from django.db import IntegrityError 
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from app.models import Session, Owner, Url, Collection, Log
from app.forms import Mainform

# rest api
from rest_framework import generics
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from .serializers import UrlSerializer
# cache
from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.conf import settings


# ----- Глобальные переменные 
DB_ERROR = 'Ошибка доступа к БД.'                                                       # ошибка при обращении к БД для записи лога
UNKNOWN_NAME = 'UNKNOWN FUNCTION NAME'                                                  # ошибка установления процесса при записи лога 
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)                             # таймаут объектов кэша по умолчанию


# ----- Общий функционал
            
def logger(owner, process, exec_msg):
    ''' Создание записи в таблице логирования Log. 
        Аргументы:
        owner    (Owner) -- объект пользователя 
        process  (str)   -- имя вызывающего фрейма/функции/процесса
        exec_msg (str)   -- сообщение о выполненных действиях
    '''
    try: # запись лога в БД 
        Log.objects.create(
            owner = owner,                                                          
            process = process,                            
            execute = exec_msg,
        )
    except:
        Log.objects.create(
            owner = owner or None,                                                          
            process = process or None,                            
            execute = 'Не удалось создать лог пользователя <{}> для процесса {}'.format(owner, process),
        )
        

 
def is_subpart_exists(request, sub_domain):
    ''' Проверка на уникальность субдомена. Возвращает Boolean: True, если есть совпадения, иначе False. 
        Аргументы:
        request    (HttpRequest) -- объект HTTP-запроса
        sub_domain (str)         -- имя субдомена
    '''
    return Url.objects.filter(subpart=sub_domain).exists()


def get_owner(request):
    ''' Возвращает объект анонимного пользователя, установленного по ключу сессии из запроса. 
        Аргументы:
        request (HttpRequest) -- объект HTTP-запроса
    '''
    msg = ''                                                                            # сообщение в лог
    if not request.session.exists(request.session.session_key):                         # наличие ключа сессии
        request.session.create()                                                        # создание сессии для нового пользователя
    try:
        # извлеченние пользователя или создание нового
        result  = Owner.objects.get_or_create(session = Session.objects.get(session_key = request.session.session_key))
    except IntegrityError:
        owner = None
        msg = DB_ERROR
    else: 
        if result[1]:                                                                   # создан новый пользователь
            owner = result[0]
            msg = 'Создан новый пользователь с ключом сессии: ' + result[0].session.session_key,
    finally:
        if result[1] or msg:                                                            # создан новый пользователь
            logger(owner, get_fname(inspect.currentframe()), msg)                       # запись лога в БД  
    return result[0]    # объект Owner из кортежа (object, create)



def get_fname(frame):
    ''' Возвращает имя вызывающего фрейма/функции. 
        Аргументы:
        frame (frame) -- объект вызывающего фрейма  
    '''
    try:
        fname = inspect.getframeinfo(frame).function                                     # имя фрейма/функции
    except:
        fname = UNKNOWN_NAME 
        logger(None, 'get_fname', 'Не удалось определить имя процесса.')
    return fname                                                                        



def paginate(object_list=[], page_number=1, onpage=10):
    ''' Пагинация объектов заданной модели. Возвращает сраницу списка - объект класса Paginator. 
        Аргументы:
        request     (HttpRequest) -- объект HTTP-запроса
        object_list (iterable)    -- список объектов для разбиения на страницы
        page_number (int)         -- начальная страница пагинации списка правил пользователя
        onpage      (int)         -- количество строк списка правил в таблице  
    '''
    paginator = Paginator(object_list, onpage) 
    return paginator.get_page(page_number) 


  
def redirect_to(request, rule_id):
    ''' Перенаправление на ресурс по оригинальной ссылке.
        Аргументы:
        request (HttpRequest) -- объект HTTP-запроса
        rule_id (int)         -- id правила в БД        
    '''
    try:
        url = Url.objects.get(id = rule_id)                                             # объект правила, соответствующий короткой ссылке
    except Url.DoesNotExist:
        raise Http404('В модели Url нет объекта с номером ' + str(rule_id))
    else:
        return redirect(url.link)                                                       # пренаправление по ссылке правила



def ajax_check_subpart(request, sub_domain=None):
    ''' Оповещение пользователя об уникальности субдомена при вводе оригинальной ссылки или изменении значения субдомена sub_domain. 
        Возвращает JSON-объект {'subpart_unique': <Boolean: true/false>}, как результат проверки по БД,
        либо {'error': 'error'} при пустом параметре в запросе. 
        Аргументы:
        request    (HttpRequest) -- объект HTTP-запроса
        sub_domain (str)         -- значение поля субдомена
    '''
    assert isinstance(request, HttpRequest)
    result = {} # словарь callback-ответа 

    # параметр запроса не пустой -> установка результата проверки значения по БД 
    if sub_domain: 
        result = { 
            'is_subpart_exists': is_subpart_exists(request, sub_domain),                # существует ли заданный субдомен
        }
    # сообщение об ошибке
    else:
        result = {
            'error': 'Ошибка: ' + 'не указано значение субдомена!' if sub_domain == '' else 'отсутствует значение субдомена в запроосе!'
        } 
    return HttpResponse(json.dumps(result))


def caching(request, owner, process, obj, cache_key, related_field, page_number=1):
    ''' Кэширование выборки модели. Возвращает словарь контекста. '''
    page_number = request.GET.get('page') or page_number                                # установка номера страницы для текущего отображения

    # КЭШИРОВАНИЕ 
    # выборка всех правил пользователя с сортирвкой по дате удаления 
    if 'cache_key' in cache and not obj:                                                # если не производилась запись объекта url в БД
        url_query = cache.get('cache_key')                                              # ВЫБОРКА ИЗ КЭША
        is_db_query = False                                                             # флаг сообщения в контексте 
        logger(owner, process, 'Создан кеш объектов правил Url.')
    else:
        is_db_query = True
        url_query = Url.objects.filter(
            collection__in = Collection.objects.select_related(related_field).filter(
                owner=owner)).order_by('expire_date')

        results = [url.to_json() for url in url_query]
        cache.set('cache_key', results, timeout=CACHE_TTL)                              # ЗАПИСЬ В КЭШ 

        #print('TTL: ' + str(cache.ttl('url')))                                         # TTL=300 по умолчанию # вывод в консоль для отладки  
    
    return {
        'url_query': url_query,                                                         # список всех правил пользователя
        'is_db_query': is_db_query,                                                     # Boolean (из БД/кеш)
        'page_obj': paginate(url_query, page_number, owner.trows_on_page),              # разбивка на страницы      
    }
    # ----- end of caching


# ----- Периодические задачи

def clean_urls(*args):                                                                      
    ''' Очистка в БД записей правил модели 'Url' с наступившей датой удаления 'expire_date'. 
        Вызывается асинхронно в отдельном потоке.
    '''
    msg = 'Периодическая задача: очистка в БД Url-объектов правил по текущую дату включительно. '
    while True:
        delay = 24*60*60  # одни сутки                                                  # время в секундах между вызовами функции
        # очистка правил в БД и логирование
        try: 
            query = Url.objects.filter(expire_date__lte=datetime.now().date())          # выборка всех правил до текущей даты включительно
        except NameError:
            msg += DB_ERROR + 'Таблица Url не найдена.' 
        else: 
            ids = [url.id for url in query]
            # сообщение в лог
            msg = ('Удалены правила ({}) с id : ' + str(len(ids)) + str(ids)) if query \
                else 'Нет правил для удаления.' + msg
            query.delete()                                                              # удаление правил с соответствующей датой
        finally:
            logger(None, get_fname(inspect.currentframe()), msg)                        # запись лога в БД  
        # очистка правил в кеше
        time.sleep(delay)                                                               # останов задачи на период
     

def scheduller(task, *args):
    ''' Выполняет запуск асинхронной задачи в потоке.
        Аргументы:
        task (str)      -- имя задачи/функции
        args (tuple)    -- аргументы задачи task
    '''
    thread = threading.Thread(target=task, args=args)                                  # инициализация потока
    try:
        thread.start()
    except:
        msg = 'Не удалось запустить асинхроную задачу.' + task.__name__ 
    else: 
        msg = '--> В асинхронном потоке запущена задача ' + task.__name__ \
                + ((': ' + args[0]) if args else '') + '\n'                            # сообщение в лог из аргументов 
    logger(None, get_fname(inspect.currentframe()), msg)                               # запись лога в БД  
    print(msg)                                                                         # сообщение в консоль сервера


# запуск задачи clean_rules
scheduller(clean_urls, 'периодическая очистка URL-правил в БД')                                        



# ----- Представления HTML-страниц 

def home(request):
    ''' Главная страница серсвиса. 
        Аргументы:
        request     (HttpRequest) -- объект HTTP-запроса
        page_number (int)         -- начальная страница пагинации списка правил пользователя
        onpage      (int)         -- количество строк списка правил в таблице  
    '''
    assert isinstance(request, HttpRequest)                                             # проверка принадлежности объекта запроса к своему классу
    url = None
    owner = get_owner(request)                                                          # инициализация пользователя
    process = get_fname(inspect.currentframe())                                         # имя текущей функции

    # данные для начальной формы - срок жизни правила (в сутках)
    default_data = {'expire_date': datetime.now().date() + timedelta(days=owner.url_ttl)} 
    savemsg = ''                                                                        # сообщение о записи правила в БД
    mainform = Mainform(request.POST or default_data)                                   # HTML-форма правила модели Url
    errors = {} # ошибки валидации формы и логики значений.                             # Формат: 'errors': { key: [ error ] }
    msg = ''                                                                            # сообщение в лог            
    # обработка и запись формы
    if request.method == 'POST':
        if mainform.is_valid():                                                         # учтена проверка субдомена          
            url = mainform.save(commit=False)                                           # инициализация объекта Url
            url.alias = '{}/{}'.format(mainform.cleaned_data['domain'], url.subpart)    # формирование короткой ссылки 
            url.owner = owner                                                           # добавление пользователя
            url.save()                                                                  # сохранение формы - запись объекта правила в БД
            logger(owner, process, 'Создан объект правила с id: ' + str(url.id))        # запись лога в БД 
            
            url_col = Collection.objects.create(owner=get_owner(request), url=url)      # создание нового правила в БД-коллекцию пользователя
            logger(owner, process, 
                   'Создан объект коллекци правил с id: ' + str(url_col.id))            # запись лога в БД  
            
            savemsg = '{}'.format(url)                                                  # из метода __str__ модели  
            mainform = Mainform(default_data)                                           # чистая форма после записи предыдущих данных
        else:
            errors = mainform.errors                                                    # ошибки валидации формы
    # --- end of POST

    # caching was here

    # контекст HTML-страницы                                                             
    context = {
        'title': 'Сервис коротких ссылок', 'year': datetime.now().year,                 # заголовок страницы
        'mainform': mainform,
        'savemsg': savemsg,
        'errors': errors,
    }

    context.update(caching(request, owner, process, url, 'cache_key', 'url'))           # контекст кеширования
    return render(request, 'app/index.html', context)


# ----------- API

class UrlList(generics.ListAPIView):
    ''' Возвращает все правила из БД. ''' 
    queryset = Url.objects.all().order_by('expire_date')
    serializer_class = UrlSerializer



class UrlViewSet(viewsets.ModelViewSet):
    ''' Возвращает все правила из БД. ''' 
    queryset = Url.objects.all().order_by('expire_date')
    serializer_class = UrlSerializer