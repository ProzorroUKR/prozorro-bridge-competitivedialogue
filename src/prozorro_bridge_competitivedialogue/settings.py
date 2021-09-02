import os
from prozorro_crawler.settings import logger

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://root:example@localhost:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "prozorro-bridge-competitivedialogue")
ERROR_INTERVAL = int(os.environ.get("ERROR_INTERVAL", 5))

PUBLIC_API_HOST = os.environ.get("PUBLIC_API_HOST", "https://lb-api-sandbox-2.prozorro.gov.ua")
API_TOKEN = os.environ.get("API_TOKEN", "competitive_dialogue_data_bridge")
USER_AGENT = os.environ.get("USER_AGENT", "Databridge competitivedialogue 2.0")
API_VERSION = os.environ.get("API_VERSION", "2.5")

BASE_URL = f"{PUBLIC_API_HOST}/api/{API_VERSION}"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}",
    "User-Agent": USER_AGENT,
}
ALLOWED_STATUSES = (
    "active.tendering",
    "active.pre-qualification",
    "active.pre-qualification.stand-still",
    "active.auction",
    "active.qualification",
    "active.awarded",
    "complete",
    "cancelled",
    "unsuccessful",
    "draft.stage2",
)
REWRITE_STATUSES = ('draft',)
COPY_NAME_FIELDS = (
    "title_ru",
    "mode",
    "procurementMethodDetails",
    "title_en",
    "description",
    "description_en",
    "description_ru",
    "title",
    "minimalStep",
    "value",
    "procuringEntity",
    "submissionMethodDetails",
)
CD_UA_TYPE = "competitiveDialogueUA"
CD_EU_TYPE = "competitiveDialogueEU"
STAGE_2_EU_TYPE = "competitiveDialogueEU.stage2"
STAGE_2_UA_TYPE = "competitiveDialogueUA.stage2"
STAGE2_STATUS = 'draft.stage2'

LOGGER = logger
