import os
from prozorro_crawler.settings import logger, PUBLIC_API_HOST

LOGGER = logger

API_HOST = os.environ.get("API_HOST", PUBLIC_API_HOST)
API_OPT_FIELDS = os.environ.get("API_OPT_FIELDS", "status,procurementMethodType").split(",")
API_TOKEN = os.environ.get("API_TOKEN", "competitive_dialogue_data_bridge")

ERROR_INTERVAL = int(os.environ.get("ERROR_INTERVAL", 5))

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
    "buyers",
)
STAGE_2_EU_TYPE = "competitiveDialogueEU.stage2"
STAGE_2_UA_TYPE = "competitiveDialogueUA.stage2"
STAGE2_STATUS = 'draft.stage2'
