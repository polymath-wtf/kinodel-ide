Примерный Roadmap нашего приложения, мб какие-то шаги пропустил, а какие-то перепутал.

## Фаза 1: Препродакшн (MVP)
- [ ] Экстракт старого проекта в новую документацию без воды.
- [ ] Architecture 
    - [ ] Langgraph
    - [ ] основные модули (agents, tools, memory, chunks)
- [ ] Agents 
    - [ ] создание основных агентов
    - [ ] интеграция агентов в langgraph
    - [ ] проектирование `tool_calls` в агентах
        - [ ] search
        - [ ] read
        - [ ] write
        - [ ] generate
        - [ ] edit
    - [ ] проектирование chunks в агентов
        - [ ] картинки
        - [ ] видео
        - [ ] музыка

- [ ] Базовые UI компоненты
- [ ] Initial mvp documentation

## Фаза 2: Первый деплой (MVP)

- [ ] Core architecture и основные модули
- [ ] Deploy langgraph
- [ ] Deploy agents
    - [ ] импорт agents
    - [ ] рабочие `tool_calls` для агентов
    - [ ] chunks агентов
    - [ ] контекст агентов
- [ ] Database
    - [ ] gemini-embedding-2 chunks
    - [ ] supabase for storage
- [ ] Workflows
    - [ ] image workflow (i2i, t2i)
    - [ ] video workflow (t2v, i2v, v2v)
    - [ ] music workflow (t2a)
    - [ ] Api calls для workflow
- [ ] Docker compose для локального запуска
- [ ] Основные функции приложения

## Фаза 3: Open-betta

- [ ] Deploy на сервер
- [ ] Friends testing
- [ ] Users feedback
- [ ] Performance optimization

## Фаза 4: Advanced Features

- [ ] Расширенные возможности
- [ ] Tutorials для пользователей
- [ ] Release preparation
    - [ ] Security audit
    - [ ] Endpoints testing
    - [ ] Subscriptions testing

## Фаза 5: Production

- [ ] Production deployment
- [ ] Monitoring and logging
- [ ] Performance optimization
- [ ] Аминь