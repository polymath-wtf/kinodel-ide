Это один из моих траев в deep research комбинации hermes и gemini-embedding-2 , не факт что здесь всё правильно, зато концепция ясна.

# **Архитектура и Руководство по Развертыванию: Автономный Hermes Agent в Google Cloud Run с Адаптивной Памятью RAG на Базе Gemini Embedding 2**

Эволюция автономных систем искусственного интеллекта обуславливает фундаментальный сдвиг от эфемерных реактивных чат-ботов к агентам с долгосрочной памятью, способным к контекстному самообучению. В авангарде этой трансформации находится архитектура Hermes Agent, реализующая уникальный замкнутый цикл обучения. Данная система автономно генерирует навыки на основе пользовательского опыта, оптимизирует их в процессе эксплуатации и формирует многоуровневую диалектическую модель пользователя между сессиями.1 Подобный уровень автономности требует не просто локального запуска скриптов, а создания отказоустойчивой, доступной 24/7 облачной инфраструктуры, которая могла бы выступать в роли "второго мозга" (Second Brain), функционально напоминающего графовые и семантические связи баз знаний формата Obsidian.md.3

Развертывание подобной системы в корпоративной или личной облачной среде сопряжено с рядом инженерных вызовов. Традиционные виртуальные выделенные серверы (VPS) 5 часто избыточны по стоимости и требуют постоянного административного обслуживания (патчинг ОС, настройка systemd, управление Docker-демонами).6 В противовес этому, бессерверные вычисления (Serverless Computing), такие как Google Cloud Run, предоставляют возможность масштабирования до нуля, когда агент простаивает, что сводит инфраструктурные расходы к минимуму. Однако эфемерная природа бессерверных контейнеров конфликтует с необходимостью агента сохранять свои воспоминания, навыки и векторные индексы.2

Данное руководство представляет собой исчерпывающий архитектурный и практический базис для развертывания полноценного сервера с личным ассистентом Hermes. Развертывание разделено на два стратегических этапа: первичное развертывание дефолтной инфраструктуры с использованием бесплатного уровня (Free Tier) LLM-моделей через Gemini CLI, и последующая глубокая модернизация (прокачка) системы управления знаниями. Модернизация включает настройку адаптивной памяти Retrieval-Augmented Generation (RAG) на базе мультимодальной модели gemini-embedding-2 с применением технологии Matryoshka Representation Learning (MRL), где фрагменты данных выступают в роли семантических нейронов.10

## **Вычислительная Топология и Персистентное Хранение: Google Cloud Run и GCS FUSE**

Архитектура Hermes Agent жестко завязана на файловую систему. Все критические компоненты, включая файлы конфигурации (config.yaml), секреты (.env), системные промпты (SOUL.md), базу данных сессий SQLite, графы навыков и векторные индексы, по умолчанию хранятся в директории \~/.hermes (или /root/.hermes в контексте контейнера).8 Если развернуть стандартный Docker-контейнер nousresearch/hermes-agent в Cloud Run без дополнительных модификаций, все накопленные агентом знания будут безвозвратно утеряны при перезапуске или остановке инстанса.

Для обеспечения сохранности состояния (statefulness) в бессерверной среде Google Cloud Run применяется механизм монтирования томов на базе Google Cloud Storage (GCS) с использованием интеграции Cloud Storage FUSE (Filesystem in Userspace).14

### **Механика и Семантика GCS FUSE**

Интеграция GCS Fuse позволяет бессерверному контейнеру обращаться к объектному хранилищу бакета так, как если бы это была локальная файловая система, используя стандартные системные вызовы (POSIX semantics).14 Это критически важно, поскольку ядро агента, написанное на Python, использует стандартные библиотеки ввода-вывода (например, open(), os.path) для чтения и записи своих воспоминаний, и абстрагирование этого процесса через FUSE избавляет разработчика от необходимости переписывать код агента под API облачных провайдеров.16

Развертывание томов FUSE в Cloud Run поддерживается исключительно в среде выполнения второго поколения (Gen 2 execution environment), которая обеспечивает необходимую поддержку сетевых файловых систем и улучшенную производительность CPU за счет использования микро-ВМ на базе инфраструктуры gVisor.15

Для обеспечения работы бакета в режиме чтения и записи с корректными правами доступа система инициализируется через интерфейс командной строки gcloud с использованием специфических флагов \--add-volume и \--add-volume-mount.14 Механизм GCS FUSE по умолчанию кэширует часто запрашиваемые файлы, что снижает латентность при повторных обращениях к метаданным памяти.16

### **Транзакционные Ограничения SQLite на Сетевых Файловых Системах**

Инженерный компромисс при использовании GCS FUSE заключается в работе с базами данных SQLite, которые Hermes интенсивно использует для управления историей сессий (SessionDB) и векторными индексами.17 Cloud Storage оптимизирован для пропускной способности при последовательном доступе к крупным объектам, а не для высокоинтенсивных транзакционных нагрузок с произвольным доступом, характерных для реляционных СУБД.18

Фундаментальное ограничение заключается в том, что сетевые файловые системы, включая FUSE, не поддерживают блокировки разделяемой памяти (shared memory locks), которые необходимы для корректной работы SQLite в режиме журнала упреждающей записи (Write-Ahead Logging, WAL). Использование режима WAL на смонтированном томе GCS неизбежно приведет к ошибкам базы данных и повреждению индексов памяти агента.9

В связи с этим, при конфигурации Hermes Agent необходимо убедиться, что все базы данных SQLite работают в классических режимах журналирования DELETE или TRUNCATE. Учитывая специфику персонального ИИ-ассистента, где соотношение операций чтения к операциям записи составляет примерно 95:5 (поиск по базе знаний происходит значительно чаще, чем сохранение новых глобальных воспоминаний), производительность базы данных на GCS FUSE остается на весьма приемлемом уровне для индивидуального использования.9

## **Этап 1\. Развертывание Базовой Инфраструктуры Hermes с Нуля**

Первая фаза реализации проекта заключается в создании фундаментальной инфраструктуры. Задача — развернуть базовый, так называемый "дефолтный" Hermes Agent, который сможет функционировать 24/7 в облаке, сохранять свое состояние и отвечать на запросы пользователя через интерфейс командной строки или мессенджеры (например, Telegram).

### **Подготовка Облачного Проекта и Ресурсов**

Начало работы требует настройки окружения Google Cloud Platform (GCP). Предполагается, что у администратора системы уже установлен инструмент gcloud CLI и выполнена авторизация.

1. **Создание и конфигурация проекта:** Выделение изолированного проекта GCP для агента обеспечивает безопасность и точный контроль затрат. В рамках проекта необходимо активировать критически важные API.  
   Убедитесь, что включены run.googleapis.com (Cloud Run) и storage.googleapis.com (Cloud Storage). Для последующего использования моделей также требуется включить generativelanguage.googleapis.com (Gemini API) или aiplatform.googleapis.com (Vertex AI).  
2. **Организация персистентного хранилища (Бакет):** Хранилище должно быть создано в том же географическом регионе, где планируется развертывание вычислительного контейнера Cloud Run. Это архитектурное требование критично: если бакет находится в США, а Cloud Run в Европе, каждая операция чтения/записи базы данных памяти будет страдать от колоссальной трансатлантической задержки, что сделает работу агента неприемлемо медленной.18  
   Bash  
   gcloud storage buckets create gs://hermes-memory-vault-alpha \--location=europe-central2 \--uniform-bucket-level-access

### **Интеграция Интеллектуального Ядра: Gemini CLI и Headless-Конфигурация**

Hermes Agent обладает модульной архитектурой провайдеров LLM, позволяя подключать локальные модели (через Ollama, llama.cpp), проприетарные API (OpenAI, Anthropic) и агрегаторы (OpenRouter).2 Для максимизации экономической эффективности и получения доступа к одному из самых больших контекстных окон в индустрии (до 2 миллионов токенов), целесообразно интегрировать модели Google Gemini.

Использование провайдера google-gemini-cli обеспечивает прямое взаимодействие с бэкендом Google.20 Однако аутентификация в бессерверной среде (Headless-режим) без доступа к браузеру для прохождения OAuth-потока требует альтернативного подхода.21 Официальная документация указывает, что для Headless-режима наиболее оптимальным является использование статического API-ключа.21

Ключ, полученный через Google AI Studio, предоставляет доступ к бесплатному уровню (Free Tier) с щедрыми квотами (в некоторых конфигурациях позволяющему обрабатывать десятки миллионов токенов в сутки без оплаты, при условии согласия на использование данных для обучения моделей Google).20 Этот ключ должен быть передан в контейнер через переменную окружения GEMINI\_API\_KEY или GOOGLE\_API\_KEY.20

Важно отметить технический нюанс: в некоторых версиях Hermes интеграция с эндпоинтом совместимости OpenAI от Google (generativelanguage.googleapis.com/v1beta/openai) может вызывать ошибки HTTP 400: API\_KEY\_INVALID из\-за несовпадения ожидаемого формата заголовков Bearer.24 Использование встроенного провайдера gemini или google-gemini-cli решает эту проблему за счет корректной нативной трансляции схем вызовов инструментов (Tool Calling) и нормализации ролей в массиве сообщений.25

Система разрешения конфигурации Hermes строго иерархична. При наличии переменных окружения в .env файле, они имеют приоритет для секретов, в то время как config.yaml управляет несекретными настройками.13

### **Деплой Контейнера в Google Cloud Run**

Официальный репозиторий nousresearch/hermes-agent предоставляет готовые Docker-образы.2 Запуск этого образа в Cloud Run требует точной передачи аргументов для активации тома GCS и запуска фонового шлюза (Gateway).

Процесс деплоя инициируется следующей командой:

Bash

gcloud beta run deploy hermes-core-assistant \\  
  \--image=nousresearch/hermes-agent:latest \\  
  \--execution-environment=gen2 \\  
  \--cpu=2 \\  
  \--memory=4Gi \\  
  \--add-volume=name=brain-volume,type\=cloud-storage,bucket=hermes-memory-vault-alpha \\  
  \--add-volume-mount=volume=brain-volume,mount-path=/root/.hermes \\  
  \--set-env-vars=GEMINI\_API\_KEY="AIzaSy....CyI...",TELEGRAM\_BOT\_TOKEN="qwe:qwe" \\  
  \--command\="hermes" \\  
  \--args="gateway,start" \\  
  \--region=europe-central2

api openrouter sk-or-v1-799...

Анализ переданных параметров:

* \--execution-environment=gen2: Обязательное условие для поддержки сетевых монтирований.15  
* \--add-volume и \--add-volume-mount: Эти флаги связывают бакет GCS с внутренней директорию /root/.hermes.14 Абсолютно все данные, генерируемые агентом (от логов до SQLite баз), теперь синхронизируются с объектным хранилищем.  
* \--command="hermes" и \--args="gateway,start": Вместо запуска интерактивного терминального интерфейса (TUI), который завершился бы ошибкой в отсутствии TTY 2, агент запускается как фоновый шлюз. Это позволяет ему прослушивать подключенные мессенджеры, такие как Telegram, Discord или Slack, используя токены, переданные в переменных окружения.2

После успешного развертывания базовый Hermes Agent функционирует. Он способен вести диалог, использовать базовые инструменты (например, поиск в интернете) и сохранять краткосрочные сессионные данные. Однако его память ограничена текстовыми файлами MEMORY.md и USER.md.13 Для трансформации агента в полноценную систему управления знаниями требуется переход ко второму этапу.

## **Этап 2\. Эволюция Памяти: Интеграция Gemini Embedding 2, MRL и Obsidian.md**

Реактивные системы ограничены своим контекстным окном. Истинная автономность достигается, когда агент способен проактивно извлекать релевантный исторический контекст из обширных массивов данных перед генерацией ответа. В архитектуре Hermes это реализуется через двухслойную инъекцию контекста: базовый слой (сводка сессии) обновляется с частотой contextCadence, в то время как диалектическое дополнение (глубокие рассуждения и факты) извлекается из памяти с частотой dialecticCadence.27

Для создания "второго мозга", функционально аналогичного графовым хранилищам Obsidian 3, ядро Hermes модернизируется с помощью RAG-конвейера (Retrieval-Augmented Generation).17 В отличие от тяжеловесных решений, требующих развертывания отдельных серверов векторных баз данных (Qdrant, Pinecone), архитектура Hermes RAG полагается на высокооптимизированное локальное хранение.17

### **Математический Базис и Архитектура Gemini Embedding 2**

Эффективность любой системы RAG определяется качеством ее семантического пространства. Внедрение модели gemini-embedding-2 от Google революционизирует процесс извлечения знаний благодаря своей мультимодальной природе и колоссальному объему входного контекста до 8192 токенов.10 Эта модель способна преобразовывать текст, документы (PDF), исходный код, изображения и даже аудиодорожки в единое унифицированное 3072-мерное пространство с плавающей запятой.10 Подобная мультимодальность позволяет агенту, например, находить релевантные текстовые заметки по описанию архитектурной диаграммы.10

Однако работа с векторами размерностью 3072 создает существенную вычислительную нагрузку. При индексации десятков тысяч заметок Obsidian объем базы данных многократно возрастает, а вычисление косинусного сходства (Cosine Similarity) между вектором запроса и матрицей векторов документов требует значительных ресурсов CPU, что нежелательно в среде Cloud Run с ограниченным объемом оперативной памяти.31

Решением этой проблемы является поддержка технологического прорыва — Matryoshka Representation Learning (MRL).10 Суть метода MRL заключается в обучении нейронной сети таким образом, чтобы наиболее критическая семантическая информация "сжималась" и концентрировалась в начальных сегментах (префиксах) генерируемого вектора.11 Метафора матрешки здесь идеальна: полноразмерный 3072-мерный вектор содержит внутри себя полностью функциональный 1536-мерный вектор, который, в свою очередь, содержит 768-мерный, и так далее вплоть до 256 измерений.11

Разработчик может указать параметр output\_dimensionality при вызове API, чтобы динамически усечь вектор на стороне сервера Google перед его отправкой агенту.10 Это позволяет достичь баланса между точностью и скоростью.

Сравнительный анализ метрик качества (на базе стандарта MTEB) при использовании MRL в моделях Gemini демонстрирует минимальную деградацию при уменьшении размерности 32:

| Размерность MRL | Потребление памяти (Float32) | Скорость сканирования базы | Относительное качество MTEB |
| :---- | :---- | :---- | :---- |
| **3072** (Default) | 12.0 KB / вектор | Базовая (1.0x) | 100.0% |
| **1536** | 6.0 KB / вектор | \~ 1.9x | \> 99.0% |
| **768** (Рекомендация) | 3.0 KB / вектор | \~ 3.8x | \> 97.5% |
| **256** | 1.0 KB / вектор | \~ 11.2x | \~ 92.0% |

Для инфраструктуры Hermes оптимальным выбором является размерность 768\. Это снижает потребление памяти в 4 раза, пропорционально ускоряет векторный поиск в SQLite и практически не влияет на релевантность извлекаемых знаний.11

Кроме того, модель gemini-embedding-2 поддерживает целевые инструкции (Task Types). Передача префиксов, таких как task:code retrieval (для исходного кода) или task:search result (для общих заметок), перед самим текстом оптимизирует геометрию векторов под конкретные намерения поиска, еще больше повышая точность конвейера.10 При использовании официального SDK Google Generative AI (пакет google-genai), параметр задается через конфигурационный объект EmbedContentConfig(output\_dimensionality=768).32

### **Векторная Инженерия на Базе sqlite-vec и FTS5**

Как агент Hermes хранит эти векторы без Pinecone или ChromaDB? Ответ кроется в расширении sqlite-vec.17 Hermes использует SQLite для хранения базы данных сессий, и это расширение, написанное на чистом C без внешних зависимостей, добавляет поддержку SIMD-ускоренного поиска сходства прямо внутри файлов .sqlite.17

Для интеграции RAG-конвейера необходимо установить дополнительные пакеты Python в контейнер Cloud Run. Это можно сделать, обновив Dockerfile или запустив команду внутри контейнера:

Bash

pip install hermes-agent\[rag,docs\]

Эта команда устанавливает драйверы векторного поиска, fastembed (для локальных фолбэков) и парсеры для сложных форматов (PDF, DOCX).17

Внутренняя топология базы данных knowledgebase (например, \~/.hermes/knowledgebase/indexes/{hash}.sqlite) представляет собой триумвират таблиц 17:

1. Таблица chunks: хранит исходный текст, пути к файлам и позиции строк.17  
2. Виртуальная таблица embeddings: создана с использованием using vec0(...) и хранит векторы gemini-embedding-2.17  
3. Виртуальная таблица chunks\_fts: использует встроенный модуль FTS5 для полнотекстового индексирования.17

### **Гибридный Поиск (Reciprocal Rank Fusion)**

Плотный векторный поиск (Dense Search), основанный на эмбеддингах, превосходно улавливает семантический смысл (например, связывает "увеличение скорости базы данных" с "рефакторингом запросов"). Однако он печально известен тем, что упускает точные ключевые совпадения (Sparse Search) — например, специфические имена переменных, уникальные идентификаторы или редкие аббревиатуры.38

В Hermes внедрен механизм гибридного поиска, который решает эту проблему.17 При поступлении запроса от агента (или автоматически перед его ответом), система выполняет два параллельных запроса:

1. Семантический поиск через sqlite-vec (вычисляет cosine\_similarity).  
2. Поиск по ключевым словам через FTS5 (вычисляет bm25\_score).17

Результаты этих двух независимых систем объединяются. Чаще всего применяется математический аппарат Reciprocal Rank Fusion (RRF), который рассчитывает итоговый балл по формуле ![][image1], где ![][image2] — позиция документа в каждом из списков, а ![][image3] — константа сглаживания.17 Альтернативным подходом является взвешенная линейная комбинация баллов, где семантический результат получает альфа-вес 0.6, слегка доминируя над ключевыми словами.17 Этот гибридный подход, не требующий внешних серверов, увеличивает показатель полноты (Recall) на 15-30%.17

### **Интеграция "Второго Мозга" Obsidian**

Практическая реализация концепции "второго мозга" начинается с указания директории с файлами Markdown (базы Obsidian) в файле конфигурации агента. Hermes Agent реализует концепцию "Рабочего пространства" (Workspace), постоянно отслеживая изменения в указанных файловых путях.17

Для тонкой настройки процесса векторизации и интеграции Gemini Embedding 2 необходимо отредактировать файл \~/.hermes/config.yaml. Поскольку этот файл находится на примонтированном томе GCS FUSE, любые изменения, внесенные через терминал или удаленно, сохранятся перманентно.

Пример конфигурации блока knowledgebase для интеграции с Obsidian:

YAML

knowledgebase:  
  enabled: true  
  directories:  
    \- /root/.hermes/workspace/obsidian\_vault  
  auto\_retrieve: true  
  max\_context\_chunks: 8  
  reindex\_on\_change: true  
  embedding\_model: custom  
  custom\_embedding:  
    provider: google-genai  
    model: gemini-embedding-2  
    output\_dimensionality: 768  
    task\_type: "retrieval\_document"

Анализ параметров конфигурации 17:

* directories: Массив путей, который агент сканирует. При использовании Obsidian переменная окружения OBSIDIAN\_VAULT\_PATH также может быть задана в .env для обратной совместимости с плагинами.4  
* auto\_retrieve: Включает фоновый векторный поиск. Перед тем как агент увидит сообщение пользователя, система невидимо выполняет поиск по базе Obsidian и внедряет релевантные фрагменты в системный контекст.17  
* max\_context\_chunks: Ограничивает количество инжектируемых "мыслей". При лимите в 8 фрагментов (размером 400-500 токенов каждый), бюджет токенов на контекст составляет около 4000, что предотвращает переполнение контекстного окна и снижает затраты на генерацию.17  
* reindex\_on\_change: Инструктирует агента отслеживать системные события модификации файлов (например, когда пользователь редактирует заметку в Obsidian) и автоматически реиндексировать изменившийся файл в фоне, обновляя его векторы в sqlite-vec.17

#### **Стратегии Фрагментации (Chunking)**

Эффективность модели gemini-embedding-2 напрямую зависит от качества подаваемых на вход данных. Отправка всего файла целиком размывает семантический смысл, а отправка по одному предложению лишает данные контекста. Hermes применяет интеллектуальные стратегии фрагментации 17:

1. **Документы Markdown (заметки Obsidian):** Применяется рекурсивное разбиение текста (Recursive character splitting). Текст разделяется по естественным границам, спускаясь по иерархии разделителей \["\\n\\n", "\\n", ". ", " ", ""\]. Целевой размер фрагмента составляет 400-512 токенов. Для сохранения связности мыслей применяется перекрытие (overlap) в 10-20% между соседними чанками.17  
2. **Файлы исходного кода:** Если в базе Obsidian или рабочем пространстве присутствуют скрипты, применение текстового разбиения фатально для логики кода. Hermes использует парсинг на основе абстрактного синтаксического дерева (AST) через библиотеку Tree-sitter.17 Код разделяется по границам логических блоков (определения функций, классы) с целевым размером 400-600 токенов. Согласно внутренним исследованиям, AST-фрагментация повышает полноту извлечения кода с 42.4% до 70.1%.17

## **Продвинутая Эксплуатация и Будущее Расширение**

Завершение второго этапа формирует полностью автономную инфраструктуру: Hermes Agent, размещенный в Google Cloud Run с нулевыми затратами на простой, использующий персистентное хранилище GCS FUSE для файлов конфигурации и SQLite баз данных. Его "мозг" запитан бесплатными токенами Gemini 2.5 через Headless CLI конфигурацию, а долговременная память интегрирована с базой Obsidian.md, где каждая заметка превращена в семантический чанк (нейрон) с помощью MRL-усеченной модели gemini-embedding-2.

Дальнейшее расширение архитектуры может включать интеграцию протокола Model Context Protocol (MCP).41 MCP позволяет агенту подключаться к внешним серверам и инструментам стандартизированным способом. Например, добавление секции mcp\_servers в config.yaml позволит агенту обращаться к API Github или файловым системам сторонних серверов.41 В сочетании с кросс-сессионной памятью и гибридным поиском, это превращает личного ассистента в мощную децентрализованную интеллектуальную систему, способную не только к семантическому извлечению знаний, но и к проактивному выполнению сложных, многошаговых задач в облачной среде.

Анализ архитектуры плагинов памяти (MemoryProvider) показывает, что Hermes обладает глубокой интеграцией с жизненным циклом диалога. Методы prefetch(query), sync\_turn(), и on\_pre\_compress() позволяют модулю RAG не только извлекать информацию, но и автоматически суммировать, компрессировать и сохранять новые факты обратно в базу Obsidian, формируя истинно замкнутый цикл непрерывного самообучения.28 Таким образом, интеграция Gemini Embedding 2 с MRL выступает не просто механизмом поиска, а фундаментальным когнитивным драйвером эволюции персонального ИИ.

#### **Works cited**

1. Hermes Agent Documentation | Hermes Agent, accessed April 28, 2026, [https://hermes-agent.nousresearch.com/docs/](https://hermes-agent.nousresearch.com/docs/)  
2. NousResearch/hermes-agent: The agent that grows with you \- GitHub, accessed April 28, 2026, [https://github.com/nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent)  
3. Is there an AI agent integration for Obsidian that can use my notes as the source for prompts? : r/ObsidianMD \- Reddit, accessed April 28, 2026, [https://www.reddit.com/r/ObsidianMD/comments/1rp5woo/is\_there\_an\_ai\_agent\_integration\_for\_obsidian/](https://www.reddit.com/r/ObsidianMD/comments/1rp5woo/is_there_an_ai_agent_integration_for_obsidian/)  
4. Read, search, and create notes in the Obsidian vault \- Hermes Agent, accessed April 28, 2026, [https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian)  
5. I took the NousResearch Hermes Agent and built a simple managed hosting app \- Reddit, accessed April 28, 2026, [https://www.reddit.com/r/vibecoding/comments/1slhhj1/i\_took\_the\_nousresearch\_hermes\_agent\_and\_built\_a/](https://www.reddit.com/r/vibecoding/comments/1slhhj1/i_took_the_nousresearch_hermes_agent_and_built_a/)  
6. 3 Ways to Deploy Hermes Agent on the Cloud (From Fastest to Most Flexible), accessed April 28, 2026, [https://www.tencentcloud.com/techpedia/144041](https://www.tencentcloud.com/techpedia/144041)  
7. Full Hermes Agent Setup Tutorial: Step-by-Step Walkthrough \- YouTube, accessed April 28, 2026, [https://www.youtube.com/watch?v=uycgV-eulGE](https://www.youtube.com/watch?v=uycgV-eulGE)  
8. How to set up Hermes Agent with Docker \- Hostinger, accessed April 28, 2026, [https://www.hostinger.com/tutorials/how-to-set-up-hermes-agent](https://www.hostinger.com/tutorials/how-to-set-up-hermes-agent)  
9. How to deploy flask app with sqlite on google cloud ? : r/googlecloud \- Reddit, accessed April 28, 2026, [https://www.reddit.com/r/googlecloud/comments/12hk510/how\_to\_deploy\_flask\_app\_with\_sqlite\_on\_google/](https://www.reddit.com/r/googlecloud/comments/12hk510/how_to_deploy_flask_app_with_sqlite_on_google/)  
10. Gemini Embedding 2 | Generative AI on Vertex AI \- Google Cloud Documentation, accessed April 28, 2026, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2)  
11. Getting Started with Gemini Embedding 2 \- DataCamp, accessed April 28, 2026, [https://www.datacamp.com/tutorial/gemini-embedding-2](https://www.datacamp.com/tutorial/gemini-embedding-2)  
12. Gemini Embedding 2: Our first natively multimodal embedding model \- Google Blog, accessed April 28, 2026, [https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/)  
13. Configuration | Hermes Agent \- nous research, accessed April 28, 2026, [https://hermes-agent.nousresearch.com/docs/user-guide/configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)  
14. Configure Cloud Storage volume mounts for Cloud Run services, accessed April 28, 2026, [https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts](https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts)  
15. Introducing Cloud Run volume mounts | Google Cloud Blog, accessed April 28, 2026, [https://cloud.google.com/blog/products/serverless/introducing-cloud-run-volume-mounts](https://cloud.google.com/blog/products/serverless/introducing-cloud-run-volume-mounts)  
16. Working with Files in Cloud Run Jobs: Introducing GCS Fuse \- DEV Community, accessed April 28, 2026, [https://dev.to/mesmacosta/working-with-files-in-cloud-run-jobs-introducing-gcs-fuse-iob](https://dev.to/mesmacosta/working-with-files-in-cloud-run-jobs-introducing-gcs-fuse-iob)  
17. Feature: Knowledgebase RAG System — User-Configured Document Directory with Local Embedding, Hybrid Search & Auto-Retrieval · Issue \#844 · NousResearch/hermes-agent \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/issues/844](https://github.com/NousResearch/hermes-agent/issues/844)  
18. How to Deploy a Serverless Database with Cloud Run \- Wallace's Blog, accessed April 28, 2026, [https://www.wallacesharpedavidson.nz/post/sqlite-cloudrun/](https://www.wallacesharpedavidson.nz/post/sqlite-cloudrun/)  
19. Quickstart | Hermes Agent \- nous research, accessed April 28, 2026, [https://hermes-agent.nousresearch.com/docs/getting-started/quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)  
20. AI Providers | Hermes Agent \- nous research, accessed April 28, 2026, [https://hermes-agent.nousresearch.com/docs/integrations/providers](https://hermes-agent.nousresearch.com/docs/integrations/providers)  
21. Gemini CLI authentication setup | Gemini CLI, accessed April 28, 2026, [https://geminicli.com/docs/get-started/authentication/](https://geminicli.com/docs/get-started/authentication/)  
22. Headless Mode | gemini-cli \- GitHub Pages, accessed April 28, 2026, [https://google-gemini.github.io/gemini-cli/docs/cli/headless.html](https://google-gemini.github.io/gemini-cli/docs/cli/headless.html)  
23. A simple guide to setting up Gemini 2.5 Pro, free, without running into 3rd party rate limits, accessed April 28, 2026, [https://www.reddit.com/r/ChatGPTCoding/comments/1jrp1tj/a\_simple\_guide\_to\_setting\_up\_gemini\_25\_pro\_free/](https://www.reddit.com/r/ChatGPTCoding/comments/1jrp1tj/a_simple_guide_to_setting_up_gemini_25_pro_free/)  
24. \[Setup\]: \[Bug\] HTTP 400 API\_KEY\_INVALID with Google Provider on the latest version (Worked fine in previous version) · Issue \#12127 · NousResearch/hermes-agent \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/issues/12127](https://github.com/NousResearch/hermes-agent/issues/12127)  
25. \[Feature\]: Native Google GenAI Provider for Gemini Models · Issue \#4983 · NousResearch/hermes-agent \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/issues/4983](https://github.com/NousResearch/hermes-agent/issues/4983)  
26. Nous Research Hermes Agent: Setup and Tutorial Guide \- DataCamp, accessed April 28, 2026, [https://www.datacamp.com/tutorial/hermes-agent](https://www.datacamp.com/tutorial/hermes-agent)  
27. hermes-agent/website/docs/user-guide/features/memory-providers.md at main \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory-providers.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory-providers.md)  
28. hermes-agent/agent/memory\_provider.py at main \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/blob/main/agent/memory\_provider.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/memory_provider.py)  
29. Your OpenClaw Agent Just Got a Photographic Memory: Add Gemini's Free On-Demand RAG in Under 15… \- Dr. Ernesto Lee, accessed April 28, 2026, [https://drlee.io/your-openclaw-agent-just-got-a-photographic-memory-add-geminis-free-on-demand-rag-in-under-15-410b6110a55f](https://drlee.io/your-openclaw-agent-just-got-a-photographic-memory-add-geminis-free-on-demand-rag-in-under-15-410b6110a55f)  
30. GoogleGenerativeAIEmbeddings | langchain\_google\_genai \- LangChain Reference Docs, accessed April 28, 2026, [https://reference.langchain.com/python/langchain-google-genai/embeddings/GoogleGenerativeAIEmbeddings](https://reference.langchain.com/python/langchain-google-genai/embeddings/GoogleGenerativeAIEmbeddings)  
31. What Is Matryoshka Representation Learning in Gemini Embedding 2? \- MindStudio, accessed April 28, 2026, [https://www.mindstudio.ai/blog/matryoshka-representation-learning-gemini-embedding-2](https://www.mindstudio.ai/blog/matryoshka-representation-learning-gemini-embedding-2)  
32. Embeddings | Gemini API \- Google AI for Developers, accessed April 28, 2026, [https://ai.google.dev/gemini-api/docs/embeddings](https://ai.google.dev/gemini-api/docs/embeddings)  
33. Gemini Embedding now generally available in the Gemini API \- Google Developers Blog, accessed April 28, 2026, [https://developers.googleblog.com/gemini-embedding-available-gemini-api/](https://developers.googleblog.com/gemini-embedding-available-gemini-api/)  
34. GoogleGenerativeAIEmbeddings integration \- Docs by LangChain, accessed April 28, 2026, [https://docs.langchain.com/oss/python/integrations/embeddings/google\_generative\_ai](https://docs.langchain.com/oss/python/integrations/embeddings/google_generative_ai)  
35. cookbook/quickstarts/Embeddings.ipynb at main \- Gemini API \- GitHub, accessed April 28, 2026, [https://github.com/google-gemini/cookbook/blob/main/quickstarts/Embeddings.ipynb](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Embeddings.ipynb)  
36. sqlite-graphrag \- crates.io: Rust Package Registry, accessed April 28, 2026, [https://crates.io/svelte/crates/sqlite-graphrag/1.0.1](https://crates.io/svelte/crates/sqlite-graphrag/1.0.1)  
37. asg017/sqlite-vec: A vector search SQLite extension that runs anywhere\! \- GitHub, accessed April 28, 2026, [https://github.com/asg017/sqlite-vec](https://github.com/asg017/sqlite-vec)  
38. Integration: agentmemory as a memory provider plugin for Hermes · Issue \#6715 \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/issues/6715](https://github.com/NousResearch/hermes-agent/issues/6715)  
39. Feature: User Workspace & Knowledge Base — Persistent Document Storage, Search, and RAG Integration · Issue \#531 · NousResearch/hermes-agent \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/issues/531](https://github.com/NousResearch/hermes-agent/issues/531)  
40. Tree-sitter \+ Embeddings as search\_files target='semantic' Mode (inspired by Roo Code) · Issue \#489 · NousResearch/hermes-agent \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/issues/489](https://github.com/NousResearch/hermes-agent/issues/489)  
41. Hermes Agent Tutorial: Install & Set Up Your First Self-Improving AI (2026) | NxCode, accessed April 28, 2026, [https://www.nxcode.io/resources/news/hermes-agent-tutorial-install-setup-first-agent-2026](https://www.nxcode.io/resources/news/hermes-agent-tutorial-install-setup-first-agent-2026)  
42. Native Mcp | Hermes Agent, accessed April 28, 2026, [https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mcp/mcp-native-mcp](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mcp/mcp-native-mcp)  
43. Memory Provider Plugins | Hermes Agent, accessed April 28, 2026, [https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin)  
44. \[Feature\] Introduce \`MemoryProvider\` interface for long-term memory integrations · Issue \#3943 · NousResearch/hermes-agent \- GitHub, accessed April 28, 2026, [https://github.com/NousResearch/hermes-agent/issues/3943](https://github.com/NousResearch/hermes-agent/issues/3943)