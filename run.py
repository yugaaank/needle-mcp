import os
import zipfile

CACHE_DIR = os.path.expanduser("~/.cache/needle")
ENGINE_VERSION = "2.0.3"


def _ensure_engine():
    lib = os.path.join(CACHE_DIR, "libneedle.so")
    if os.path.exists(lib):
        return lib

    wheel = f"/tmp/cactus_needle-{ENGINE_VERSION}-py3-none-manylinux2014_x86_64.whl"
    if not os.path.exists(wheel):
        import urllib.request
        url = (
            f"https://huggingface.co/Cactus-Compute/needle2/"
            f"resolve/main/python/cactus_needle-{ENGINE_VERSION}-py3-none-manylinux2014_x86_64.whl"
        )
        os.makedirs(CACHE_DIR, exist_ok=True)
        ctx = __import__("ssl").create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = __import__("ssl").CERT_NONE
        urllib.request.urlretrieve(url, wheel, context=ctx)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with zipfile.ZipFile(wheel) as zf:
        with open(lib, "wb") as f:
            f.write(zf.read("needle/libneedle.so"))
    return lib


lib = _ensure_engine()
import needle.agent.fetch as _fetch
_fetch.fetch_library = lambda *a, **k: lib

import needle


@needle.tool
def get_weather(city: str):
    """Get the current weather for a city."""
    return {"city": city, "temp_c": 27, "sky": "clear"}


if __name__ == "__main__":
    agent = needle.Needle(tools=[get_weather])
    result = agent.run("what's it like in Lagos right now?")
    print(result["results"])
