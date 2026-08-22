You are a Senior Jedi Developer of Kinodel-ide imba software for creators.
Наша задача оживить старый проект kinodel D:\Ai\kinodel-ide\legacy и полностью его пересобрать.
Мы хотим автоматизировать креативные пайплайны в форме human-in-the-loop creative app, в котором будет много сабагентов под каждый конкретный сабж /goal, которые будут двигаться по pipeline state machine на LangGraph, с фичей иньекции контекста с помощью скилов и чанков.
---
Твоя задача, заложить новый фундамент будующего приложения, я тебе так-же оставил векторные подскази в новой документации D:\Ai\kinodel-ide\docs , твоя задача изучить старый проект, и разработать архитектуру нового приложения без прежних костылей и оверинжиниринга.
---
Старый проект у нас находится в нескольких местах:
- Здесь находятся старые агенты D:\Ai\kinodel-ide\legacy\hermes kinodel которые тебе предстоит ревёрс инжинирнуть в новое место docs\agents . Обрати внимание, что там большой оверинжиниринг, поэтому мы их будем пересоздавать с нуля. А всякие старые скрипты нужно пересобрать в новые `tool_cals` , концепт которых ты можешь записать в D:\Ai\kinodel-ide\docs\tools\tools.md . А ещё по меньше воды про контекст агентов написан тут D:\Ai\kinodel-ide\legacy\hermes wiki\entities . Типа Convert `delegate_task` handoff envelopes into typed node inputs.
- большая википедия концептов D:\Ai\kinodel-ide\legacy\hermes wiki по канонам llm-wiki скила D:\Ai\kinodel-ide\skills\llm-wiki , кстате можно взять лучшее из Andrej Karpathy's LLM Wiki pattern и пересобрать свою базу данных и rag под наш сабж в новом амплуа.
- Кстате, мы ещё не успели в старом проекте создать агентов muse-kinodel, season-kinodel, episode-kinodel, но контекст относительно этих новых агентов разбросан по wiki D:\Ai\kinodel-ide\legacy\hermes wiki с тэгами music, season, episode, music-video, alm,audio-gen и тд. И кстате у них по плану были особые `pipeline` файлы например D:\Ai\kinodel-ide\legacy\hermes wiki\concepts\music-video-pipeline.md и D:\Ai\kinodel-ide\legacy\hermes wiki\concepts\serial-pipeline.md.
---
Старый проект был собран на импровизированном state machine внутри hermes agent, в котором по дефолту небыло необходимых мне runtime state machine фичей, поэтому внутри скилов агентов находятся костыльные скрипты которые кстате можно будет сейчас переписать в `tool_cals` (делигируй задачу ресёрч старых скриптов сабагенту, чтобы он вытащил оттуда полезные tools ).
А ещё в старом проекте очень костыльные артефакты которые нам надо переихобрести без оверинжиниринга.
---
А так-же мы собираем next-gen архитектуру chunk контекста с помощью мультимодального rag gemini-embedding-2 , документация которого находится в D:\Ai\kinodel-ide\legacy\rag и wiki D:\Ai\kinodel-ide\legacy\hermes wiki\entities\gemini-embedding-2.md . 

Приложение будет работать на архитектуре LangGraph с его state machine, вот их оффициальная документация D:\Ai\kinodel-ide\skills\LangGraph , изучи её чтобы построить фундамент будующей архитектуры для нашего сабжа.
---
P.S. Сделай экстракт вайба в душу D:\Ai\kinodel-ide\SOUL.md
P.S.S. Под конец, отредактируй README.md и D:\Ai\kinodel-ide\AGENTS.md и D:\Ai\kinodel-ide\.rules\map.mdc для закрепления контекста.
P.S.S.S. Анти-оверинжиниринг скилл D:\Ai\kinodel-ide\skills\simplification-cascades .
---