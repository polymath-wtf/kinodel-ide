Здравствуйте! Мой друг Владимир поделился вашим контактом и рассказал о вакансии, и она меня заинтересовала, это как раз моя сфера деятельности, разработка ai пайплайнов, автоматизация comfyui workflow, и оркестрация агентов.

В дизайне я с 2019 года, с нейросетями работаю с лета 2022-го. 
Последние полтора года разрабатываю приложения и автоматизирую AI-пайплайны с помощью Comfyui serverless endpoints.
За это время прошёл путь от простых связок n8n → ComfyUI API → Google Cloud Storage → Pinterest API, до собственных приложений, которые комуницируют через FastAPI с Comfyui endpoints и AI-агентами.

Так-же есть опыт обучения LoRA начиная с SD 1.5 и AnimateDiff, до современных моделей Krea 2, Flux 2 klein, на очереди H3.
Поднял гибридный RAG-поиск по каталогу 200+ LoRA в Supabase для поиска lora под задачу, с передачей точных trigger_word & prompt_style для context injection LLM агенту.
А так-же опыт в поднятии продакшн билдов на google cloud VM console.

Моя сильная сторона - это упрощать сложные ai workflow с помощью гуманитарного склада ума и диплома по квантовой физике.

Сейчас разрабатываю Kinodel - локальную open-source среду с командой агентов для кинопроизводства на LangGraph, Comfyui, Python, FastAPI и React.
Идея была в том чтобы собрать весь продакшн в одном рабочем пространстве:
- специализированных агентов, которые будут учитывать правила и особенности каждой генеративной модели.
- кросс-платформенные генеративные api, Comfyui, Fal.ai, Replicate, Runpod и тд.
- иньекция контекста RAG и markdown wiki.
- сложные многоступенчатые workflows, упакованные в понятный пошаговый пайплайн.
- оставляя при этом human-in-the-loop для творческих решений.

Пайплайн начинается с vibe-input и @context (чанки персонажей, музыки, стиля и тд).
Далее по этапам state-machine, формируется сценарий, character sheet и enviroment персонажей, затем раскадровка, видео и монтаж.
На каждом этапе работает свой агент со своими skills, инструментами и зоной ответственности.
LangGraph управляет последовательностью, а пользователь проверяет результаты и принимает творческие решения через human-in-the-loop.

Примеры проектов
- Kinodel — PET проект, pre-mvp, локальный Hollywood на LangGraph: https://github.com/polymath-wtf/kinodel-ide
- Mille — авто-генеративный завод для мебельного бренда (custom LoRA + LLM + ComfyUI + n8n): https://mille-ai.vercel.app
- Alpha-Worker-v1 — serverless ComfyUI endpoint с кастомными костылями по оптимизации инференса: https://github.com/polymath-wtf/Alpha-Worker-v1
- SageAttention 3 — Предварительно скомпилированная сборка для оптимизации инференса на CUDA 13.0 Nvidia Blackwell под NVFP4 квантизацию: https://huggingface.co/Seryoger/Sageattention-3-cu130-5090-endpoint
- ComfyUI-Polymath-Vibenodes — custom node для автоматизации промптинга через вебхук в n8n: https://github.com/polymath-wtf/ComfyUI-Polymath-Vibenodes
- Checkpoint — мой первый vibecode SaaS, геймифицированный todolist в эстетике solarpunk RPG: https://github.com/polymath-wtf/Checkpoint
- так-же есть 2 приватных репозитория, которые я не могу показать, но один из них - работающий завод SMM контента на Laravel ai sdk, а второй - horny comfyui SaaS.

## Стек
- Генерация: ComfyUI это База. Minimax h3, Ltx, Flux 2 klein, Krea 2, Qwen 2.1. 
- Агенты: LangGraph, Hermes, Laravel ai sdk, n8n, mcp, tool use, OpenAI API.
- Разработка: Python, FastAPI, React, Next.js.
- Данные: Supabase, PostgreSQL, Sqlite, RAG, гибридный поиск, gemini-embedding-2.
- Инфраструктура: Docker, RunPod Serverless, Google Cloud VM и Cloud Storage.
- Визуал: After Effects композинг и постпродакшн, Photoshop, Davinci Resolve
- Vibecode: OpenCode, Codex, Windsurf, skills, soul.md

Надеюсь это не было похоже на презентация продукта, а на специалиста который уже давно работает с подобными системами и за плечами имеет релевантный багаж знаний.
Kinodel привёл как пример того, как я соединяю генеративные workflows, агентную оркестрацию и индустриальные тренды в одном продукте.
Поделитесь, пожалуйста, подробным описанием вакансии, предполагаемым форматом сотрудничества, и вилкой зп por favor