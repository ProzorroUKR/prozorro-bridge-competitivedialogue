from aiohttp import ClientSession
import asyncio
import json

from prozorro_bridge_competitivedialogue.settings import (
    LOGGER,
    ERROR_INTERVAL,
    ALLOWED_STATUSES,
    REWRITE_STATUSES,
    STAGE2_STATUS,
)
from prozorro_bridge_competitivedialogue.utils import (
    journal_context,
    check_tender,
    prepare_new_tender_data,
    BASE_URL,
    HEADERS,
)
from prozorro_bridge_competitivedialogue.journal_msg_ids import (
    DATABRIDGE_GET_CREDENTIALS,
    DATABRIDGE_GOT_CREDENTIALS,
    DATABRIDGE_EXCEPTION,
    DATABRIDGE_TENDER_STAGE2_NOT_EXIST,
    DATABRIDGE_ONLY_PATCH,
    DATABRIDGE_CREATE_NEW_STAGE2,
    DATABRIDGE_CREATE_NEW_TENDER,
    DATABRIDGE_UNSUCCESSFUL_CREATE,
    DATABRIDGE_TENDER_CREATED,
    DATABRIDGE_CD_PATCH_STAGE2_ID,
    DATABRIDGE_CD_UNSUCCESSFUL_PATCH_STAGE2_ID,
    DATABRIDGE_CD_PATCHED_STAGE2_ID,
    DATABRIDGE_PATCH_NEW_TENDER_STATUS,
    DATABRIDGE_PATCH_DIALOG_STATUS,
    DATABRIDGE_SUCCESSFUL_PATCH_DIALOG_STATUS,
)


async def get_tender_credentials(tender_id: str, session: ClientSession) -> dict:
    url = f"{BASE_URL}/tenders/{tender_id}/extract_credentials"
    while True:
        LOGGER.info(
            f"Getting credentials for tender {tender_id}",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_GET_CREDENTIALS},
                {"TENDER_ID": tender_id}
            ),
        )
        try:
            response = await session.get(url, headers=HEADERS)
            data = await response.text()
            if response.status == 200:
                data = json.loads(data)
                LOGGER.info(
                    f"Got tender {tender_id} credentials",
                    extra=journal_context(
                        {"MESSAGE_ID": DATABRIDGE_GOT_CREDENTIALS},
                        {"TENDER_ID": tender_id}
                    ),
                )
                return data["data"]
            raise ConnectionError(f"Failed to get credentials {data}")
        except Exception as e:
            LOGGER.warning(
                f"Can't get tender credentials {tender_id}",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_EXCEPTION},
                    {"TENDER_ID": tender_id}
                ),
            )
            LOGGER.exception(e)
            await asyncio.sleep(ERROR_INTERVAL)


async def get_tender(tender_id: str, session: ClientSession) -> dict:
    while True:
        try:
            response = await session.get(f"{BASE_URL}/tenders/{tender_id}", headers=HEADERS)
            data = await response.text()
            if response.status == 404:
                return {}
            elif response.status != 200:
                raise ConnectionError(f"Error {data}")
            return json.loads(data)["data"]
        except Exception as e:
            LOGGER.warning(
                f"Fail to get tender {tender_id}",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_EXCEPTION},
                    params={"TENDER_ID": tender_id}
                )
            )
            LOGGER.exception(e)
            await asyncio.sleep(ERROR_INTERVAL)


async def get_competitive_dialogue_data(tender: dict, session: ClientSession) -> bool:
    if "stage2TenderID" not in tender:
        return True
    
    tender_stage2 = await get_tender(tender["stage2TenderID"], session)
    if not tender_stage2:
        LOGGER.info(
            f"Tender stage 2 id={tender['id']} didn't exist, need create new",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_TENDER_STAGE2_NOT_EXIST},
                {"TENDER_ID": tender["id"]}
            )
        )
        return True
    if tender_stage2.get("status") in ALLOWED_STATUSES:
        LOGGER.info(
            f"For dialog {tender['id']} tender stage 2 already exists, need only patch",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_ONLY_PATCH},
                {"TENDER_ID": tender["id"]}
            )
        )
        return False
    elif tender_stage2.get("status") in REWRITE_STATUSES:
        LOGGER.info(
            f"Tender stage 2 id={tender['id']} has bad status need to create new",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_CREATE_NEW_STAGE2},
                {"TENDER_ID": tender["id"]})
        )
    return True


async def create_tender_stage2(new_tender: dict, session: ClientSession) -> dict:
    url = f"{BASE_URL}/tenders"
    while True:
        LOGGER.info(
            f"Creating tender stage2 from competitive dialogue id={new_tender['dialogueID']}",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_CREATE_NEW_TENDER},
                {"TENDER_ID": new_tender["dialogueID"]})
        )
        try:
            response = await session.post(url, json={"data": new_tender}, headers=HEADERS)
            data = await response.text()
            if response.status in (422, 404):
                LOGGER.warning(
                    f"Catch {response.status} status, stop create tender stage2",
                    extra=journal_context(
                        {"MESSAGE_ID": DATABRIDGE_UNSUCCESSFUL_CREATE},
                        {"TENDER_ID": new_tender["dialogueID"]})
                )
                LOGGER.warning(
                    f"Error response {data}",
                    extra=journal_context(
                        {"MESSAGE_ID": DATABRIDGE_UNSUCCESSFUL_CREATE},
                        {"TENDER_ID": new_tender["dialogueID"]}
                    )
                )
                return {}
            elif response.status != 201:
                raise ConnectionError(f"Error {data}")
        except Exception as e:
            LOGGER.warning(
                "Fail to post tender stage2",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_EXCEPTION},
                )
            )
            LOGGER.exception(e)
            await asyncio.sleep(ERROR_INTERVAL)
        else:
            tender = json.loads(data)["data"]
            LOGGER.info(
                f"Successfully created tender stage2 id={tender['id']} "
                f"from competitive dialogue id={tender['dialogueID']}",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_TENDER_CREATED},
                    {"DIALOGUE_ID": tender["dialogueID"], "TENDER_ID": tender["id"]}
                )
            )
            dialog = {"id": tender["dialogueID"], "stage2TenderID": tender["id"]}
            return dialog


async def patch_dialog_add_stage2_id(dialog: dict, session: ClientSession) -> None:
    url = f"{BASE_URL}/tenders/{dialog['id']}"
    while True:
        LOGGER.info(
            f"Patch competitive dialogue id={dialog['id']} with stage2 tender id",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_CD_PATCH_STAGE2_ID},
                {"TENDER_ID": dialog["id"]}
            )
        )
        try:
            response = await session.patch(url, json={"data": dialog}, headers=HEADERS)
            data = await response.text()
            if response.status == 412:
                continue
            elif response.status != 200:
                LOGGER.info(
                    f"Unsuccessful patch competitive dialogue id={dialog['id']} with stage2 tender id",
                    extra=journal_context(
                        {"MESSAGE_ID": DATABRIDGE_CD_UNSUCCESSFUL_PATCH_STAGE2_ID},
                        {"TENDER_ID": dialog['id']}
                    )
                )
                raise ConnectionError(f"Error {data}")
        except Exception as e:
            LOGGER.warning(
                "Failed to patch tender",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_EXCEPTION},
                )
            )
            LOGGER.exception(e)
            await asyncio.sleep(ERROR_INTERVAL)
        else:
            data = json.loads(data)["data"]
            LOGGER.info(
                f"Successful patch competitive dialogue id={data['id']} with stage2 tender id",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_CD_PATCHED_STAGE2_ID},
                    {"DIALOGUE_ID": data["id"], "TENDER_ID": data["stage2TenderID"]}
                )
            )
            break


async def patch_new_tender_status(dialog: dict, session: ClientSession) -> None:
    patch_data = {
        "id": dialog["stage2TenderID"],
        "status": STAGE2_STATUS,
        "dialogueID": dialog["id"]
    }
    url = f"{BASE_URL}/tenders/{patch_data['id']}"
    while True:
        LOGGER.info(
            f"Patch tender stage2 id={patch_data['id']} with status {patch_data['status']}",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_PATCH_NEW_TENDER_STATUS},
                {"TENDER_ID": patch_data["id"]})
        )
        try:
            response = await session.patch(url, json={"data": patch_data}, headers=HEADERS)
            data = await response.text()
            if response.status != 200:
                LOGGER.info(
                    f"Unsuccessful patch tender stage2 id={patch_data['id']} with status {patch_data['status']}",
                    extra=journal_context(
                        {"MESSAGE_ID": DATABRIDGE_CD_UNSUCCESSFUL_PATCH_STAGE2_ID},
                        {"TENDER_ID": patch_data['id']}
                    )
                )
                raise ConnectionError(f"Error {data}")
        except Exception as e:
            LOGGER.warning(
                f"Failed to patch tender {patch_data['id']}",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_EXCEPTION},
                )
            )
            LOGGER.exception(e)
            await asyncio.sleep(ERROR_INTERVAL)
        else:
            data = json.loads(data)["data"]
            LOGGER.info(
                f"Successful patch tender stage2 id={data['id']} with status {patch_data['status']}",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_CD_PATCHED_STAGE2_ID},
                    {"DIALOGUE_ID": patch_data["dialogueID"], "TENDER_ID": patch_data["id"]}
                )
            )
            break


async def patch_dialog_status(dialogue_id: str, session: ClientSession) -> None:
    patch_data = {"id": dialogue_id, "status": "complete"}
    url = f"{BASE_URL}/tenders/{dialogue_id}"
    while True:
        LOGGER.info(
            f"Patch competitive dialogue id={dialogue_id} with status {patch_data['status']}",
            extra=journal_context(
                {"MESSAGE_ID": DATABRIDGE_PATCH_DIALOG_STATUS},
                {"TENDER_ID": dialogue_id}
            )
        )
        try:
            response = await session.patch(url, json={"data": patch_data}, headers=HEADERS)
            data = await response.text()
            if response.status in (403, 422):
                LOGGER.error(
                    f"Stop trying patch dialogue id={patch_data['id']} with status {patch_data['status']}. "
                    f"Response: {data}",
                    extra=journal_context(
                        {"MESSAGE_ID": DATABRIDGE_CD_UNSUCCESSFUL_PATCH_STAGE2_ID},
                        params={"TENDER_ID": patch_data['id']}
                    )
                )
                return
            elif response.status != 200:
                LOGGER.info(
                    f"Unsuccessful patch competitive dialogue id={patch_data['id']} with status {patch_data['status']}",
                    extra=journal_context(
                        {"MESSAGE_ID": DATABRIDGE_CD_UNSUCCESSFUL_PATCH_STAGE2_ID},
                        {"TENDER_ID": patch_data['id']}
                    )
                )
                raise ConnectionError(f"Error {data}")
        except Exception as e:
            LOGGER.warning(
                f"Failed to patch tender {dialogue_id}",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_EXCEPTION},
                    {"TENDER_ID":dialogue_id}
                )
            )
            LOGGER.exception(e)
            await asyncio.sleep(ERROR_INTERVAL)
        else:
            data = json.loads(data)["data"]
            LOGGER.info(
                f"Successful patch competitive dialogue id={dialogue_id} with status {patch_data['status']}",
                extra=journal_context(
                    {"MESSAGE_ID": DATABRIDGE_SUCCESSFUL_PATCH_DIALOG_STATUS},
                    {"DIALOGUE_ID": dialogue_id, "TENDER_ID": data["stage2TenderID"]}
                )
            )
            break


async def process_tender(session: ClientSession, tender: dict) -> None:
    if not check_tender(tender):
        return None
    tender_to_sync = await get_tender(tender["id"], session)
    create_second_stage = await get_competitive_dialogue_data(tender_to_sync, session)

    if create_second_stage:
        credentials = await get_tender_credentials(tender["id"], session)
        try:
            new_tender = prepare_new_tender_data(tender_to_sync, credentials)
        except KeyError:
            return None
        tender_dialog = await create_tender_stage2(new_tender, session)
        if tender_dialog:
            await patch_dialog_add_stage2_id(tender_dialog, session)
            await patch_new_tender_status(tender_dialog, session)
            await patch_dialog_status(tender["id"], session)
    else:
        await patch_dialog_status(tender["id"], session)
