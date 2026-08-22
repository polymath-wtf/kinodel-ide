# Agent Muse

В нашем RAG будет google-gemini-embedding-2 , а это значит что мы можем грузить аудиофайлы на вход, и получать векторное представление аудио. Можно загрузить любимые песни и попробовать их миксануть по новому.Значит нам нужно будет сделать по чанку для каждого аудиофайла и попробовать его описать ещё если поместится.

## Prompts
- Alternative interdimentional Rock,vibrant gravitation,4D echo,powefull hetero assinchrone vocal,soulfy eclipse,etherial guitar rifs,energies drumm,adventure time,vhs screengrab,vinyl scratches,legendary recipe,full power
- The great escape freelancer into paradise,celestial echo vibe girl gracefully sing a worldwide echo song ,full power masala,ultimate prana power ,alternative gravitation,authentic pleasure,future dreampop,Inspired by inner soul
- digital magic beyond,Soul eclipse,Uplifting drum and bass elements,Hopeful increasing vocal,ethereal synth pads,Vivacious bass,breakbeat rhythms, Inspiration euphoric,experimental electronic,alternative house,Vibrant rock
- Alternative gravitation, escape from reality,Reverse the gravity, reality interpolation, 2’5 D composition, charity empathy , worldwide echo, alternative dimension, soulfy eclipse
- Ambient etherium paradise vibe,good vibes only,japanese forest leaf rustling, peace bird music, 808 drum machine, 808 kick, claps, shaker, synthesizer, synth bass, Synth Drones, beautiful, peaceful, Ethereal, Natural, 122 BPM, Instrumental
- the great escape to Ambient etherium house paradise,good vibes only,japanese forest leaf rustling, peace bird music, cat mew, new age, meditation, advertisement, 808 drum machine, 808 kick, claps, shaker, synthesizer, synth bass, soaring lead heavily reverbed, modern, sleek, beautiful, inspiring, futuristic

## Agent
нужно собрать скил который даст агенту возможность генерировать музыку с помощью api suno.
например сделаем скил для агента, который сперва сделает промпт и lyrics, затем закидывает api запрос по вебхуку и получает в output песню.

## Features
- French Moldavian vibe
- decomposition `alm`
	- тайминг битов
	- звуковые дорожки (vocal,drums,и тд)
	- это поможет на монтаже, а так-же нужно знать где какой кусок какой длительности
- Агент может выкупать музыку с помощью докомпозированных дорожек и таймингов слов и контекста звука
- После создания песни и декомпозиции, агент должен выкупить трек и сделать по нему заметки вайба
- todolist-pipeline
	- процессы которые можно автоматизировать можно делать постепенно с помощью фичи todolist-pipeline
	- например создание песни это: vibe prompt -> lyrics generation + prompt generation -> api request suno -> recieve music -> decomposition -> analyzation -> vibe notes -> checkpoint = на данном этапе агент может остановиться и подумать что делать дальше и что у него получилось. Потом например можно начать делать раскадровку и клип (тоже постепенно)