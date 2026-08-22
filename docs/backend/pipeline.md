## Pipeline architecture

документация архитектуры пайплайнов kinodel-ide.
как работает state machine и /goal
сделай экстракт контекста из нашего предыдущего проекта и покажи архитектуру пайплайнов.
Основной message об архитектуре пайплайнов уже описан в нашем предыдущем проекте, сделай ревёрс инжиниринг под свежую архитектуру LangGraph.

## Pipeline types
обрати внимание, что у нас есть заготовленные пайплайны: cinematic, season, music-video, а ещё у нас есть фича create-pipeline которая позволяет создавать свои пайплайны.

## Create pipeline 
Create-pipeline это пайплайн по созданию пайплайна, окак.
Пример legacy\hermes wiki\concepts\create-pipeline.md
В двух словах, на input мы получаем natural language idea, reference video или VLM/ALM analysis, production constraints, required chunks и known agents/capabilities registry. 
Затем агент ризонит, как можно упаковать этот пайплайн в нашу архитектуру, какие задачи нужно раздать *существующим агентам*.
На output мы получаем пайплайн с списком /goal (каждому агенту) для нашего state machine по достижению желаемого результата.