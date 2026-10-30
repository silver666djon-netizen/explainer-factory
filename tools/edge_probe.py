"""Which edge-tts settings answer from this runner? python tools/edge_probe.py"""
import asyncio
import time

import edge_tts

TEXTS = ["У Ларри в корзине билет.", "А покупатели среди них выбирали места примерно на... пять процентов дороже.",
         "А покупатели среди них выбирали места примерно на пять процентов дороже."]
VARIANTS = [dict(rate="-4%", pitch="-6Hz", boundary="WordBoundary"), dict(rate="-4%", pitch="-6Hz", boundary="SentenceBoundary"),
            dict(rate="+0%", pitch="+0Hz", boundary="WordBoundary"), dict(rate="+0%", pitch="+0Hz", boundary="SentenceBoundary")]


async def one(text, v):
    c = edge_tts.Communicate(text, "ru-RU-DmitryNeural", **v)
    n = 0
    async for ch in c.stream():
        if ch["type"] == "audio":
            n += len(ch["data"])
    return n


print("edge-tts", edge_tts.__version__ if hasattr(edge_tts, "__version__") else "?")
for v in VARIANTS:
    for t in TEXTS:
        ok = 0
        errs = set()
        for k in range(5):
            try:
                ok += asyncio.run(one(t, v)) > 0
            except Exception as e:  # noqa: BLE001
                errs.add(type(e).__name__ + ": " + str(e)[:60])
            time.sleep(1)
        print(f"::notice::{v} {t[:30]!r}: {ok}/5 {sorted(errs)}")
