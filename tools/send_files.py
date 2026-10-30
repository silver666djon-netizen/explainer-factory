"""Send chosen files of a (draft) release to Telegram under one header (pilots, review extras).
python tools/send_files.py <dir> "<header>" [--text <file to send as a message>] <file> ...
Videos go as videos (album when several), other files as documents."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.notify import LIMIT, _api, send_document, send_text  # noqa: E402


def main(argv):
    d, head = Path(argv[0]), argv[1]
    rest = argv[2:]
    text = None
    if "--text" in rest:
        i = rest.index("--text")
        text = (d / rest[i + 1]).read_text(encoding="utf-8")
        rest = rest[:i] + rest[i + 2:]
    if text:
        body = f"{head}\n\n{text}"
        for k in range(0, len(body), 3900):
            send_text(body[k:k + 3900])
    else:
        send_text(head)
    for name in rest:
        f = d / name
        if not f.exists():
            print(f"::warning::missing {name}")
            continue
        if f.suffix == ".mp4" and f.stat().st_size < LIMIT:
            with open(f, "rb") as fh:
                _api("sendVideo", data={"caption": f"{head} · {f.name}"[:1000], "supports_streaming": "true"}, files={"video": (f.name, fh)})
        elif f.stat().st_size < LIMIT:
            send_document(f, f"{head} · {f.name}")
        else:
            print(f"::warning::{name} is over the bot limit")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
