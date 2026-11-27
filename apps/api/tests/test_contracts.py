"""Contracts hold what people need to manage them; the paper stays the reference."""

from datetime import date, timedelta

from dishka import AsyncContainer
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contracts.service import ContractService
from app.shared.clock import business_today
from tests.contract_factory import (
    CONTRACT_FACTS,
    add_document,
    enter,
    maker,
    new_contract,
    post_contract,
)

__all__ = ["maker"]

_EXTENSION = {
    "adjustments": "term",
    "number": "02.01",
    "signed_on": "2023-03-01",
    "effective_from": "2023-03-01",
    "summary": "Extend the term",
    "extends_to": "2025-06-30",
}


async def test_facts_are_typed_saved_together_and_an_empty_value_clears_one(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    url = f"/contract-instruments/{contract['instruments'][0]['id']}/facts"

    bad_date = await maker.put(url, json={"values": {"number": "1", "signed_on": "15/03/22"}})
    unknown = await maker.put(url, json={"values": {"price": "1"}})
    saved = await maker.put(url, json={"values": {"number": "12/2024", "payment_days": "30"}})
    again = await maker.put(url, json={"values": {"number": "12/2024", "payment_days": ""}})

    # Nothing is stored when one value is wrong.
    assert bad_date.json()["details"][0]["field"] == "values.signed_on"
    assert unknown.json()["code"] == "unknown_field"
    assert saved.status_code == 200
    assert saved.json()["number"] == "12/2024"
    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    assert detail["number"] == "12/2024"
    assert detail["paymentDays"] is None
    # Re-sending an unchanged value adds no history.
    assert [v["key"] for v in detail["instruments"][0]["values"]] == ["number"]
    assert again.status_code == 200


async def test_a_contract_gets_its_code_when_recorded_and_is_in_force_once_dated(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    year = business_today().year
    assert contract["code"] == f"HĐKH-{year}-0001"
    # Signed, but no date known yet: never guessed into force.
    assert contract["status"] == "undetermined"

    await enter(maker, contract["instruments"][0]["id"], {"effective_from": "2022-03-15"})
    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    # No end date: it runs until it is terminated, and nothing is reported missing.
    assert (detail["status"], detail["endOn"], detail["missingCount"]) == ("active", None, 0)

    await enter(maker, contract["instruments"][0]["id"], CONTRACT_FACTS)
    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    assert (detail["status"], detail["endOn"]) == ("expired", "2023-03-14")
    assert detail["number"] == "2022/MSC-SPIDER/VC"


async def test_annexes_are_numbered_in_recording_order_and_the_last_extension_decides(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    await enter(maker, contract["instruments"][0]["id"], CONTRACT_FACTS)
    await add_document(maker, contract, "schedule", {"summary": "Price table"})
    await add_document(maker, contract, "addendum", {**_EXTENSION, "number": "24"})
    await add_document(
        maker, contract, "addendum", {**_EXTENSION, "number": "24", "extends_to": "2024-01-01"}
    )

    detail = (await maker.get(f"/contracts/{contract['id']}")).json()

    code = contract["code"]
    assert [i["code"] for i in detail["instruments"]] == [
        code,
        f"{code}-PL01",
        f"{code}-PL02",
        f"{code}-PL03",
    ]
    assert detail["instruments"][2]["adjustments"] == ["term"]
    # Both took effect the same day: the one recorded last decides.
    assert (detail["status"], detail["endOn"]) == ("expired", "2024-01-01")
    assert detail["addendumCount"] == 3


async def test_annexes_take_the_contract_code_and_missing_facts_are_counted(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    await enter(maker, contract["instruments"][0]["id"], CONTRACT_FACTS)
    await add_document(maker, contract, "addendum", _EXTENSION)
    await add_document(maker, contract, "addendum", {"effective_from": "2023-03-02"})

    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    code = contract["code"]
    assert [i["code"] for i in detail["instruments"]] == [code, f"{code}-PL01", f"{code}-PL02"]
    # The second addendum does not say what it changes; its number and signing date are not
    # needed to place it.
    assert detail["missingCount"] == 1
    assert detail["missingFacts"] == [
        {"code": f"{code}-PL02", "kind": "addendum", "key": "adjustments"}
    ]
    incomplete = (await maker.get("/contracts", params={"isIncomplete": "true"})).json()
    assert [c["id"] for c in incomplete["items"]] == [contract["id"]]
    await enter(maker, detail["instruments"][2]["id"], {"adjustments": "price"})
    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    assert detail["missingCount"] == 0


async def test_a_contract_is_found_by_the_code_or_number_of_one_of_its_annexes(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    await enter(maker, contract["instruments"][0]["id"], CONTRACT_FACTS)
    await add_document(maker, contract, "addendum", {**_EXTENSION, "number": "05/PLHĐ-MSC"})

    for q in (f"{contract['code']}-PL01", "05/plhđ"):
        found = (await maker.get("/contracts", params={"q": q})).json()
        assert [c["id"] for c in found["items"]] == [contract["id"]], q
    assert (await maker.get("/contracts", params={"q": "PL09"})).json()["items"] == []


async def test_a_second_contract_document_is_refused(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)

    response = await maker.post(
        f"/contracts/{contract['id']}/instruments",
        json={"kind": "contract", "fileId": contract["fileId"]},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "instrument_exists"


async def test_a_document_must_come_from_the_contract_dossier(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    other = await post_contract(maker, contract["partnerId"], "other.pdf")
    response = await maker.post(
        f"/contracts/{contract['id']}/instruments",
        json={"kind": "addendum", "fileId": other.json()["instruments"][0]["fileId"]},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "file_not_in_dossier"


async def test_the_category_decides_the_side(maker: AsyncClient, container: AsyncContainer) -> None:
    contract = await new_contract(maker, container)

    wrong = await post_contract(maker, contract["partnerId"], category="contractor")
    direct = await post_contract(maker, contract["partnerId"], "direct.pdf")

    assert wrong.status_code == 409
    assert wrong.json()["code"] == "partner_role_mismatch"
    assert direct.status_code == 201
    assert direct.json()["side"] == "customer"


async def test_the_refresh_codes_contracts_that_have_none(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    await enter(maker, contract["instruments"][0]["id"], CONTRACT_FACTS)
    async with container() as request:
        session = await request.get(AsyncSession)
        await session.execute(text("UPDATE contracts SET code = NULL, status = 'draft'"))
        await session.execute(text("UPDATE contract_instruments SET code = NULL"))
        await session.commit()

    async with container() as request:
        changed = await (await request.get(ContractService)).refresh_all(date(2026, 1, 1))

    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    assert changed == 1
    # A number once issued is never reused, even when its contract lost the code.
    year = business_today().year
    assert (detail["code"], detail["status"]) == (f"HĐKH-{year}-0002", "expired")


async def test_contracts_filter_by_notice_end_and_signing_dates(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    """Expiry and notice warnings are list filters over the stored dates, counted from today."""
    today = business_today()
    old = await new_contract(maker, container)
    await enter(maker, old["instruments"][0]["id"], CONTRACT_FACTS)
    soon = await new_contract(maker, container)
    end_on = today + timedelta(days=40)
    await enter(
        maker,
        soon["instruments"][0]["id"],
        {
            **CONTRACT_FACTS,
            "expires_on": end_on.isoformat(),
            "renewal": "automatic",
            "renewal_notice_days": "30",
        },
    )

    ending = await new_contract(maker, container)
    await enter(
        maker,
        ending["instruments"][0]["id"],
        {
            **CONTRACT_FACTS,
            "signed_on": "2024-01-01",
            "effective_from": "2024-01-01",
            "expires_on": (today + timedelta(days=20)).isoformat(),
        },
    )

    async def ids(**params: str) -> list[str]:
        response = await maker.get("/contracts", params=params)
        assert response.status_code == 200, response.text
        return [c["id"] for c in response.json()["items"]]

    # The notice date of one that renews by itself is its end less the notice days.
    notice_on = (end_on - timedelta(days=30)).isoformat()
    assert await ids(noticeFrom=today.isoformat(), noticeTo=notice_on) == [soon["id"]]
    assert await ids(endFrom=today.isoformat(), sort="end_on") == [ending["id"], soon["id"]]
    assert await ids(endTo="2023-12-31") == [old["id"]]
    assert sorted(await ids(signedFrom="2022-03-15", signedTo="2022-03-15")) == sorted(
        [old["id"], soon["id"]]
    )
    # Newest by the contract's own date, not by when it was recorded.
    assert (await ids())[0] == ending["id"]
    assert (await maker.get(f"/contracts/{soon['id']}")).json()["noticeOn"] == notice_on
    assert (await maker.get(f"/contracts/{ending['id']}")).json()["noticeOn"] is None


async def test_fuel_bases_replace_each_other_and_prices_only_when_a_document_says_so(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    today = business_today()
    await enter(
        maker,
        contract["instruments"][0]["id"],
        {**CONTRACT_FACTS, "effective_from": "2022-03-15", "expires_on": f"{today.year + 2}-01-01"},
    )
    first = await add_document(
        maker,
        contract,
        "addendum",
        {"number": "01", "signed_on": "2022-05-01", "adjustments": "price"},
    )
    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    code_01 = next(i["code"] for i in detail["instruments"] if i["id"] == first)
    route = {"number": "02", "signed_on": "2022-06-01", "adjustments": "price"}
    fuel = {"number": "03", "signed_on": "2022-07-01", "adjustments": "fuel"}
    new_price = {
        "number": "04",
        "signed_on": "2023-01-01",
        "adjustments": "price,fuel",
        "replaces": code_01,
    }
    for facts in (route, fuel, new_price):
        await add_document(maker, contract, "addendum", facts)
    # Not yet in force: it changes nothing today.
    await add_document(
        maker,
        contract,
        "addendum",
        {"number": "05", "signed_on": f"{today.year + 1}-01-01", "adjustments": "fuel"},
    )

    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    standing = {i["number"]: i["standing"] for i in detail["instruments"][1:]}
    # 04 says it replaces 01 and sets a newer fuel base than 03; 02 adds a route and stays.
    assert standing == {
        "01": "superseded",
        "02": "in_force",
        "03": "superseded",
        "04": "applying",
        "05": "pending",
    }
    replaced_by = {i["number"]: i["replacedByCode"] for i in detail["instruments"][1:]}
    code_04 = next(i["code"] for i in detail["instruments"] if i["number"] == "04")
    assert replaced_by["01"] == replaced_by["03"] == code_04
    assert {a["kind"]: a["code"] for a in detail["applying"]} == {"fuel": code_04}
    # Listed by the day each starts, whatever order they were recorded in.
    assert [i["number"] for i in detail["instruments"][1:]] == ["01", "02", "03", "04", "05"]
    listed = (
        await maker.get(
            "/contract-instruments", params={"contractId": contract["id"], "standing": "applying"}
        )
    ).json()
    assert [i["number"] for i in listed["items"]] == ["04"]
    assert listed["items"][0]["contractAnnexCount"] == 5
    everything = (
        await maker.get("/contract-instruments", params={"contractId": contract["id"]})
    ).json()
    # Newest first inside the contract.
    assert [i["number"] for i in everything["items"]] == ["05", "04", "03", "02", "01"]


async def test_missing_terms_follow_practice_not_guesses(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    """An automatic renewal without a stated cycle repeats the original term; a termination takes
    effect when signed; a notice deadline exists only for a contract that renews by itself."""
    contract = await new_contract(maker, container)
    main = contract["instruments"][0]["id"]
    await enter(
        maker,
        main,
        {
            **CONTRACT_FACTS,
            "effective_from": "2022-01-01",
            "expires_on": "2022-12-31",
            "renewal": "automatic",
        },
    )
    url = f"/contracts/{contract['id']}"
    detail = (await maker.get(url)).json()
    today = business_today()
    assert detail["status"] == "auto_renewed"
    assert detail["endOn"] == date(today.year, 12, 31).isoformat()

    await enter(maker, main, {"renewal": "none", "renewal_notice_days": "30"})
    detail = (await maker.get(url)).json()
    assert (detail["status"], detail["noticeOn"]) == ("expired", None)

    await add_document(maker, contract, "termination", {"signed_on": "2022-06-30"})
    detail = (await maker.get(url)).json()
    assert (detail["status"], detail["endOn"]) == ("terminated", "2022-06-30")


async def test_the_history_records_each_change_and_outlives_a_deleted_document(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    main = contract["instruments"][0]["id"]
    await enter(maker, main, {"number": "A-1"})
    await enter(maker, main, {"number": "A-2", "signed_on": "2022-03-15"})
    annex = await add_document(maker, contract, "addendum", {"adjustments": "price"})
    deleted = await maker.delete(f"/contract-instruments/{annex}")
    assert deleted.status_code == 200, deleted.text

    events = (await maker.get(f"/contracts/{contract['id']}")).json()["events"]
    code = contract["code"]
    assert [(e["kind"], e["instrumentCode"]) for e in events] == [
        ("created", None),
        ("edited", code),
        ("edited", code),
        ("added", f"{code}-PL01"),
        ("edited", f"{code}-PL01"),
        ("deleted", f"{code}-PL01"),
    ]
    assert events[2]["changes"] == [
        {"key": "number", "before": "A-1", "after": "A-2"},
        {"key": "signed_on", "before": None, "after": "2022-03-15"},
    ]


async def test_payment_terms_follow_the_latest_addendum_and_filter_the_list(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    terms = {"payment_days": "30", "payment_from": "invoice", "statement_cutoff": "month_end"}
    await enter(maker, contract["instruments"][0]["id"], {**CONTRACT_FACTS, **terms})
    await add_document(
        maker,
        contract,
        "addendum",
        {
            "adjustments": "payment",
            "signed_on": "2022-06-01",
            "payment_days": "45",
            "statement_cutoff": "25",
        },
    )

    read = (await maker.get(f"/contracts/{contract['id']}")).json()
    assert (read["paymentDays"], read["paymentFrom"]) == (45, "invoice")
    assert read["statementCutoff"] == "25"
    for params, found in (
        ({"payments": "up_to_45"}, True),
        ({"payments": "up_to_30"}, False),
        ({"payments": "none"}, False),
        ({"statements": "day_of_month"}, True),
        ({"statements": "month_end"}, False),
    ):
        ids = [c["id"] for c in (await maker.get("/contracts", params=params)).json()["items"]]
        assert (contract["id"] in ids) is found, params
