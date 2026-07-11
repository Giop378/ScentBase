from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "scentbase")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI non configurata. Verificare il file .env o le variabili di ambiente.")