"""Unit tests for providers.py (dynamic LLM registry). Self-contained."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import providers  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

results = []


def check(name, cond):
    results.append((name, bool(cond)))


def main():
    path = providers.PROVIDERS_PATH
    backup = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    os.environ.pop("TMP_KEY", None)
    try:
        names = {p["name"] for p in providers.provider_defs()}
        check("defaults present", {"openai", "deepseek", "hermes"} <= names)

        r = providers.upsert_provider("tmp-prov", "Tmp", "https://x/v1/chat", "TMP_KEY", "m1")
        check("upsert returns saved", r.get("saved") is True)
        check("appears in defs", any(p["name"] == "tmp-prov" for p in providers.provider_defs()))
        check("model stored", providers.get_provider("tmp-prov")["model"] == "m1")

        os.environ["TMP_KEY"] = "secret"
        check("available with key", providers.is_available("tmp-prov"))
        check("in active order", "tmp-prov" in providers.available_order())
        del os.environ["TMP_KEY"]
        check("unavailable without key", not providers.is_available("tmp-prov"))

        try:
            providers.chat("tmp-prov", [{"role": "user", "content": "hi"}])
            check("chat needs key", False)
        except RuntimeError:
            check("chat needs key", True)

        try:
            providers.chat("does-not-exist", [])
            check("chat unknown raises", False)
        except RuntimeError:
            check("chat unknown raises", True)

        try:
            providers.upsert_provider("bad-name-ok", base_url="")
            check("upsert needs base_url", False)
        except ValueError:
            check("upsert needs base_url", True)

        try:
            providers.upsert_provider("bad name!", base_url="https://x")
            check("upsert slug validated", False)
        except ValueError:
            check("upsert slug validated", True)

        providers.delete_provider("tmp-prov")
        check("deleted", not any(p["name"] == "tmp-prov" for p in providers.provider_defs()))
        try:
            providers.delete_provider("tmp-prov")
            check("delete missing raises", False)
        except ValueError:
            check("delete missing raises", True)
    finally:
        if backup is not None:
            with open(path, "w", encoding="utf-8") as f:
                f.write(backup)

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(("PASS " if ok else "FAIL ") + name)
    print(f"=== providers: {passed}/{len(results)} passed ===")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
