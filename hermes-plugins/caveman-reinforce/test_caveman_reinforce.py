import json
import os
import tempfile
from pathlib import Path

import __init__ as plugin

with tempfile.TemporaryDirectory() as tmp:
    os.environ.pop("CAVEMAN_DEFAULT_MODE", None)
    os.environ["XDG_CONFIG_HOME"] = tmp
    assert plugin.resolve_mode() == "full"

    (Path(tmp) / "caveman").mkdir()
    cfg = Path(tmp) / "caveman" / "config.json"
    cfg.write_text(json.dumps({"defaultMode": "Lite"}))
    assert plugin.resolve_mode() == "lite"
    assert "(lite)" in plugin._pre_llm_call(session_id="s")["context"]

    cfg.write_text("not json")
    assert plugin.resolve_mode() == "full"

    os.environ["CAVEMAN_DEFAULT_MODE"] = "off"
    assert plugin._pre_llm_call() is None

    os.environ["CAVEMAN_DEFAULT_MODE"] = "wenyan"
    assert plugin.resolve_mode() == "wenyan-full"

print("ok")
