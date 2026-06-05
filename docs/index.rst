Lazlabs School Documentation
============================
**Веб-система управления образовательным центром**

Lazlabs School — это комплексное решение для автоматизации управления образовательным центром. Система поддерживает три роли пользователей: директора, учителей и учеников, предоставляя каждому необходимый функционал для эффективной работы.

.. toctree::
    :maxdepth: 2
    :caption: Содержание:

    spec

Быстрый старт
-------------

Для разработчиков
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Клонировать репозиторий
    git clone https://github.com/pidumbadum/lazlabs.git
    cd lazlabs-school

    # Установить зависимости
    make setup

    # Запустить тесты
    make test

    # Запустить приложение
    make run

Для пользователей Docker
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # собрать образ Docker
    make docker-build

    # Запустить в Docker
    make docker-up

    # Открыть в браузере
    open http://localhost:5000

    # Остановить docker 
    make docker-down

Тестирование
~~~~~~~~~~~~~~~~~~~~~~~~

Проект покрыт интеграционными тестами:

.. code-block:: bash

    # Все тесты
    make test

    # С отчётом о покрытии
    make coverage

Индексы и таблицы
-----------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`