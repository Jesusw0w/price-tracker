import os

# Settings require a URL at import; tests never connect, so any parseable one works
os.environ.setdefault("PT_DATABASE_URL", "sqlite://")
