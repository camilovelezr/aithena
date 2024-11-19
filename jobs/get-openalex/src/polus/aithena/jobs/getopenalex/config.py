
import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

# automatically let python do from whatever day is today
FROM_TODAY = bool(os.getenv("FROM_TODAY", "False"))

OUTPUT_PATH = os.getenv("OUT_DIR", None)

FROM_DATE = os.getenv("FROM_DATE", None)
