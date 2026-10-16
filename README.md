# Explainer Factory — CoinSense

Бесплатный конвейер: **сценарий → картинки → голос → монтаж → длинное видео + Shorts + обложка → Telegram**.

## Как это работает

1. В папку `episodes/<номер-название>/` кладётся `script.json` — сценарий, разбитый на биты
   (формат описан в [docs/SCRIPT_GUIDE.md](docs/SCRIPT_GUIDE.md)).
2. Как только `script.json` появляется или меняется, GitHub Actions сам запускает рендер:
   - картинки — Cloudflare Workers AI (Flux, бесплатно ~170 картинок в день);
   - голос — Kokoro (британский «документальный» `bm_george`);
   - монтаж — движение камеры, красный маркер, комикс-облачка, архивные фото, графики, субтитры, звуки.
3. Готовое появляется в **Releases** репозитория: `long.mp4`, `short_*.mp4`, `thumbnail.jpg`,
   `description.txt` (с главами и источниками), `long.srt` (субтитры), `metadata.json`.
4. В Telegram приходит обложка, ссылка на всё и сами Shorts.

## Запустить вручную

GitHub → вкладка **Actions** → **Render episode** → **Run workflow** → впиши имя папки эпизода
(например `0001-why-9-99`) → **Run workflow**.

## Настройки канала

`channel/channel.yaml` — название, стиль картинок, палитра, голос, громкость, лимиты.

## Музыка

Положи треки без авторских претензий (например, из YouTube Audio Library) в `assets/music/` —
они автоматически подмешаются тихим фоном и будут приглушаться под голос.

## Проверка локально (без интернета и API)

```bash
python -m factory check episodes/0001-why-9-99
python -m factory build episodes/0001-why-9-99 --offline
```
