from copy import deepcopy

from prozorro_bridge_competitivedialogue.settings import LOGGER, STAGE_2_EU_TYPE, STAGE_2_UA_TYPE, COPY_NAME_FIELDS
from prozorro_bridge_competitivedialogue.journal_msg_ids import DATABRIDGE_FOUND_NOLOT, DATABRIDGE_COPY_TENDER_ITEMS


def journal_context(record: dict = None, params: dict = None) -> dict:
    if record is None:
        record = {}
    if params is None:
        params = {}
    for k, v in params.items():
        record["JOURNAL_" + k] = v
    return record


def get_bid_by_id(bids: list, bid_id: str) -> dict:
    for bid in bids:
        if bid["id"] == bid_id:
            return bid


def prepare_lot(orig_tender: dict, lot_id: str, items: list) -> dict:
    lot = None
    for tender_lot in orig_tender["lots"]:
        if tender_lot["id"] == lot_id:
            lot = tender_lot
            break
    if lot["status"] != "active":
        return {}

    for item in orig_tender["items"]:
        try:
            if item["relatedLot"] == lot_id:
                items.append(item)
        except KeyError:
            raise KeyError("Item should contain 'relatedLot' field.")
    return lot


def check_tender(tender: dict) -> bool:
    if (
            tender.get("procurementMethodType", "") in ("competitiveDialogueUA", "competitiveDialogueEU")
            and tender["status"] == "active.stage2.waiting"
    ):
        return True
    else:
        LOGGER.info(
            f"Skipping tender {tender['id']} in status {tender['status']} "
            f"with procurementMethodType {tender.get('procurementMethodType', '')}",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_FOUND_NOLOT},
                params={"TENDER_ID": tender["id"]}
            ),
        )
    return False


def prepare_new_tender_data(tender: dict, credentials: dict) -> dict:
    LOGGER.info(
        f"Copy competitive dialogue data, id={tender['id']}",
        extra=journal_context(
            {"MESSAGE_ID": DATABRIDGE_COPY_TENDER_ITEMS},
            {"TENDER_ID": tender["id"]})
    )
    new_tender = {
        "procurementMethod": "selective",
        "status": "draft",
        "dialogueID": tender["id"]
    }

    for field_name in COPY_NAME_FIELDS:
        if field_name in tender:
            new_tender[field_name] = tender[field_name]
    if tender["procurementMethodType"].endswith("EU"):
        new_tender["procurementMethodType"] = STAGE_2_EU_TYPE
    else:
        new_tender["procurementMethodType"] = STAGE_2_UA_TYPE
    new_tender["tenderID"] = f"{tender['tenderID']}.2"

    old_lots = process_qualifications(tender, new_tender)
    if "features" in tender:
        process_features(new_tender, tender["features"], old_lots)

    new_tender["owner"] = credentials["owner"]
    new_tender["dialogue_token"] = credentials["tender_token"]
    return new_tender


def process_qualifications(tender: dict, new_tender: dict) -> dict:
    old_lots, items, short_listed_firms = {}, [], {}
    for qualification in tender["qualifications"]:
        if qualification["status"] == "active":
            bid = get_bid_by_id(tender["bids"], qualification["bidID"])
            if qualification.get("lotID"):
                if qualification["lotID"] not in old_lots:
                    lot = prepare_lot(tender, qualification["lotID"], items)
                    if not lot:
                        continue
                    old_lots[qualification["lotID"]] = lot
                for bid_tender in bid["tenderers"]:
                    if bid_tender["identifier"]["id"] not in short_listed_firms:
                        identifier = {
                            "name": bid_tender["name"],
                            "identifier": bid_tender["identifier"],
                            "lots": [{"id": old_lots[qualification["lotID"]]["id"]}]
                        }
                        short_listed_firms[bid_tender["identifier"]["id"]] = identifier
                    else:
                        short_listed_firms[bid_tender["identifier"]["id"]]["lots"].append(
                            {"id": old_lots[qualification["lotID"]]["id"]}
                        )
            else:
                new_tender["items"] = deepcopy(tender["items"])
                for bid_tender in bid["tenderers"]:
                    if bid_tender["identifier"]["id"] not in short_listed_firms:
                        identifier = {
                            "name": bid_tender["name"],
                            "identifier": bid_tender["identifier"],
                            "lots": []
                        }
                        short_listed_firms[bid_tender["identifier"]["id"]] = identifier
    new_tender["shortlistedFirms"] = list(short_listed_firms.values())
    new_tender["lots"] = list(old_lots.values())
    if items:
        new_tender["items"] = items
    return old_lots


def process_features(new_tender: dict, features: list, old_lots: dict) -> None:
    new_tender["features"] = []
    for feature in features:
        if feature["featureOf"] == "tenderer":
            new_tender["features"].append(feature)
        elif feature["featureOf"] == "item":
            if feature["relatedItem"] in (item["id"] for item in new_tender["items"]):
                new_tender["features"].append(feature)
        elif feature["featureOf"] == "lot":
            if feature["relatedItem"] in old_lots.keys():
                new_tender["features"].append(feature)
