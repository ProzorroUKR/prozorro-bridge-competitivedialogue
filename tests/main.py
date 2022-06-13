import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from prozorro_bridge_competitivedialogue.bridge import (
    get_tender_credentials,
    get_tender,
    check_second_stage_tender,
    create_tender_stage2,
    patch_dialog_add_stage2_id,
    patch_new_tender_status,
    patch_dialog_status,
    process_tender,
)
from prozorro_bridge_competitivedialogue.utils import prepare_new_tender_data


@pytest.fixture
def credentials():
    return {"data": {"owner": "user1", "tender_token": "0" * 32}}


@pytest.fixture
def error_data():
    return {"error": "No permission"}


@pytest.fixture
def tender_data():
    return {
        "id": "33",
        "title": "test_tender",
        "procurementMethodType": "competitiveDialogueEU",
        "dialogueID": "35",
        "title_ru": "asd",
        "mode": 1,
        "procurementMethodDetails": 1,
        "title_en": 1,
        "description": 1,
        "description_en": 1,
        "description_ru": 1,
        "minimalStep": 1,
        "value": 1,
        "procuringEntity": 1,
        "submissionMethodDetails": 1,
        "tenderID": "test_id",
        "features": [
            {"featureOf": "tenderer"},
            {"featureOf": "item", "relatedItem": "item_1"},
            {"featureOf": "lot", "relatedItem": "lot_1"},
        ],
        "lots": [
            {"id": "lot_1", "status": "active"}
        ],
        "items": [
            {"id": "item_1", "relatedLot": "lot_1"}
        ],
        "bids": [
            {"id": "bid_1", "tenderers": [{"identifier": {"id": "id_1"}, "name": "test_name"}]},
            {"id": "bid_2", "tenderers": [{"identifier": {"id": "id_2"}, "name": "test_name"}]}
        ],
        "qualifications": [
            {"status": "active", "lotID": "lot_1", "bidID": "bid_1"},
            {"status": "active", "bidID": "bid_2"}
        ]
    }


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_get_tender_credentials(mocked_logger, credentials, error_data):
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(side_effect=[
        MagicMock(status=403, text=AsyncMock(return_value=error_data)),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps(credentials))),
    ])

    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        data = await get_tender_credentials("34", session_mock)

    assert session_mock.get.await_count == 2
    assert data == credentials["data"]
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_get_tender_exists(mocked_logger, tender_data, error_data):
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(side_effect=[
        MagicMock(status=403, text=AsyncMock(return_value=error_data)),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data}))),
    ])

    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        data = await get_tender(tender_data["id"], session_mock)

    assert session_mock.get.await_count == 2
    assert data == tender_data
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_get_tender_not_exists(mocked_logger, error_data):
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(side_effect=[
        MagicMock(status=403, text=AsyncMock(return_value=error_data)),
        MagicMock(status=404, text=AsyncMock()),
    ])

    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        data = await get_tender("34", session_mock)

    assert session_mock.get.await_count == 2
    assert data == {}
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER", MagicMock())
async def test_check_second_stage_tender_exists_second_stage(tender_data):
    tender_data["stage2TenderID"] = "34"
    tender_data["status"] = "active.tendering"
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(
        return_value=MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data})))
    )
    create_second_stage = await check_second_stage_tender(tender_data, session_mock)
    assert create_second_stage is False


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER", MagicMock())
async def test_check_second_stage_tender_not_exists_second_stage(tender_data):
    tender_data["stage2TenderID"] = "34"
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(
        return_value=MagicMock(status=404, text=AsyncMock(return_value=json.dumps({})))
    )
    create_second_stage = await check_second_stage_tender(tender_data, session_mock)
    assert create_second_stage is True


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER", MagicMock())
async def test_check_second_stage_tender_exists_second_stage_id(tender_data):
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(
        return_value=MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data})))
    )
    create_second_stage = await check_second_stage_tender(tender_data, session_mock)
    assert create_second_stage is True


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER", MagicMock())
async def test_check_second_stage_tender_exists_second_stage_draft(tender_data):
    tender_data["status"] = "draft"
    tender_data["stage2TenderID"] = "34"
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(
        return_value=MagicMock(status=404, text=AsyncMock(return_value=json.dumps({"data": tender_data})))
    )
    create_second_stage = await check_second_stage_tender(tender_data, session_mock)
    assert create_second_stage is True


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_create_tender_stage2_positive(mocked_logger, error_data):
    tender_data = {
        "id": "33",
        "status": "draft",
        "stage2TenderID": "34",
        "dialogueID": "35"
    }
    session_mock = AsyncMock()
    session_mock.post = AsyncMock(side_effect=[
        MagicMock(status=403, text=AsyncMock(return_value=error_data)),
        MagicMock(status=201, text=AsyncMock(return_value=json.dumps({"data": tender_data})))
    ])
    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        dialogue = await create_tender_stage2(tender_data, session_mock)

    assert dialogue == {"id": tender_data["dialogueID"], "stage2TenderID": tender_data["id"]}
    assert session_mock.post.await_count == 2
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_create_tender_stage2_negative(mocked_logger, error_data):
    tender_data = {
        "id": "33",
        "status": "draft",
        "stage2TenderID": "34",
        "dialogueID": "35"
    }
    session_mock = AsyncMock()
    session_mock.post = AsyncMock(side_effect=[
        MagicMock(status=404, text=AsyncMock(return_value=error_data)),
    ])
    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        dialogue = await create_tender_stage2(tender_data, session_mock)

    assert dialogue == {}
    assert session_mock.post.await_count == 1
    assert mocked_logger.exception.call_count == 0
    assert mocked_sleep.await_count == 0


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_patch_dialog_add_stage2_id(mocked_logger, error_data):
    tender_data = {
        "id": "33",
        "status": "draft",
        "stage2TenderID": "34",
        "dialogueID": "35"
    }
    session_mock = AsyncMock()
    session_mock.patch = AsyncMock(side_effect=[
        MagicMock(status=412, text=AsyncMock(return_value=error_data)),
        MagicMock(status=404, text=AsyncMock(return_value=error_data)),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data}))),
    ])
    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        await patch_dialog_add_stage2_id(tender_data, session_mock)

    assert session_mock.patch.await_count == 3
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_patch_new_tender_status(mocked_logger, error_data):
    tender_data = {
        "id": "33",
        "stage2TenderID": "34",
        "dialogueID": "35"
    }
    session_mock = AsyncMock()
    session_mock.patch = AsyncMock(side_effect=[
        MagicMock(status=412, text=AsyncMock(return_value=error_data)),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data}))),
    ])
    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        await patch_new_tender_status(tender_data, session_mock)

    assert session_mock.patch.await_count == 2
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_patch_dialog_status(mocked_logger, error_data):
    tender_data = {
        "id": "33",
        "stage2TenderID": "34",
        "dialogueID": "35"
    }
    session_mock = AsyncMock()
    session_mock.patch = AsyncMock(side_effect=[
        MagicMock(status=412, text=AsyncMock(return_value=error_data)),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data}))),
    ])
    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        await patch_dialog_status(tender_data["dialogueID"], session_mock)

    assert session_mock.patch.await_count == 2
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_patch_dialog_status_api_error(mocked_logger, error_data):
    tender_data = {
        "id": "33",
        "stage2TenderID": "34",
        "dialogueID": "35"
    }
    session_mock = AsyncMock()
    session_mock.patch = AsyncMock(side_effect=[
        MagicMock(status=412, text=AsyncMock(return_value=error_data)),
        MagicMock(
            status=422, text=AsyncMock(return_value=json.dumps({"error": "Can't patch tender in complete status"}))
        ),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data}))),
    ])
    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        await patch_dialog_status(tender_data["dialogueID"], session_mock)

    assert session_mock.patch.await_count == 2
    assert mocked_logger.exception.call_count == 1
    isinstance(mocked_logger.exception.call_args.args[0], ConnectionError)
    assert mocked_sleep.await_count == 1
    assert mocked_logger.error.call_count == 1


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.utils.LOGGER")
async def test_process_tender_skip(mocked_logger):
    tender_data = {
        "id": "33",
        "procurementMethodType": "competitiveDialogueUA",
        "status": "active.awarded"
    }
    session_mock = AsyncMock()
    await process_tender(session_mock, tender_data)
    assert session_mock.patch.await_count == 0
    assert mocked_logger.debug.call_count == 1
    assert mocked_logger.exception.call_count == 0


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
async def test_process_tender_with_stage2(mocked_logger):
    tender_data = {
        "id": "33",
        "procurementMethodType": "competitiveDialogueUA",
        "status": "active.stage2.waiting",
        "stage2TenderID": "35"
    }
    tender_data_stage2 = {
        "id": "34",
        "procurementMethodType": "competitiveDialogueUA",
        "status": "complete",
        "stage2TenderID": "35"
    }
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(side_effect=[
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data}))),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data_stage2}))),
    ])
    session_mock.patch = AsyncMock(side_effect=[
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data_stage2}))),
    ])

    await process_tender(session_mock, tender_data)

    assert session_mock.patch.await_count == 1
    assert session_mock.get.await_count == 2
    assert mocked_logger.info.call_count == 3
    assert mocked_logger.exception.call_count == 0


@pytest.mark.asyncio
@patch("prozorro_bridge_competitivedialogue.bridge.create_tender_stage2", AsyncMock(return_value={}))
@patch("prozorro_bridge_competitivedialogue.bridge.patch_dialog_add_stage2_id", AsyncMock())
@patch("prozorro_bridge_competitivedialogue.bridge.patch_new_tender_status", AsyncMock())
@patch("prozorro_bridge_competitivedialogue.bridge.LOGGER")
@patch("prozorro_bridge_competitivedialogue.utils.LOGGER", MagicMock())
async def test_process_tender_without_stage2(mocked_logger, tender_data, credentials, error_data):
    tender_data_stage2 = {
        "id": "34",
        "procurementMethodType": "competitiveDialogueUA",
        "status": "complete",
        "stage2TenderID": "35"
    }
    tender_data["status"] = "active.stage2.waiting"
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(side_effect=[
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data}))),
        MagicMock(status=404, text=AsyncMock(return_value=json.dumps(error_data))),
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps(credentials))),
    ])
    session_mock.patch = AsyncMock(side_effect=[
        MagicMock(status=200, text=AsyncMock(return_value=json.dumps({"data": tender_data_stage2}))),
    ])
    with patch("prozorro_bridge_competitivedialogue.bridge.asyncio.sleep", AsyncMock()) as mocked_sleep:
        await process_tender(session_mock, tender_data)

    assert session_mock.patch.await_count == 0
    assert session_mock.get.await_count == 3
    assert mocked_sleep.await_count == 1
    assert mocked_logger.info.call_count == 3
    assert mocked_logger.exception.call_count == 1


@patch("prozorro_bridge_competitivedialogue.utils.LOGGER", MagicMock())
def test_prepare_new_tender_data_with_lots_and_bids_positive(tender_data, credentials):
    data = prepare_new_tender_data(tender_data, credentials["data"])

    assert data["tenderID"].endswith(".2")
    assert data["procurementMethod"] == "selective"
    assert data["procurementMethodType"].endswith(".stage2")
    assert data["shortlistedFirms"] != []
    assert data["lots"] != []
    assert all(i in data for i in ("shortlistedFirms", "owner", "dialogue_token"))
    assert all(i not in data for i in ("id", "bids", "qualifications"))


@patch("prozorro_bridge_competitivedialogue.utils.LOGGER", MagicMock())
def test_prepare_new_tender_data_with_lots_and_bids_without_features(tender_data, credentials):
    tender_data["procurementMethodType"] = "competitiveDialogueUA"
    tender_data["qualifications"][0]["status"] = "pending"
    tender_data["qualifications"][1]["status"] = "pending"
    del tender_data["features"]

    data = prepare_new_tender_data(tender_data, credentials["data"])

    assert data["tenderID"].endswith(".2")
    assert data["procurementMethod"] == "selective"
    assert data["procurementMethodType"].endswith(".stage2")
    assert data["shortlistedFirms"] == []
    assert data["lots"] == []
    assert all(i in data for i in ("shortlistedFirms", "owner", "dialogue_token"))
    assert all(i not in data for i in ("id", "bids", "qualifications"))


@patch("prozorro_bridge_competitivedialogue.utils.LOGGER", MagicMock())
def test_prepare_new_tender_data_with_lots_and_bids_no_active_lots(tender_data, credentials):
    tender_data["lots"][0]["status"] = "pending"
    data = prepare_new_tender_data(tender_data, credentials["data"])

    assert data["tenderID"].endswith(".2")
    assert data["procurementMethod"] == "selective"
    assert data["procurementMethodType"].endswith(".stage2")
    assert data["shortlistedFirms"] != []
    assert data["lots"] == []
    assert all(i in data for i in ("shortlistedFirms", "owner", "dialogue_token"))
    assert all(i not in data for i in ("id", "bids", "qualifications"))
