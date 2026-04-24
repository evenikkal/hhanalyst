"""Scrape hh.ru website when the API is unavailable (requires OAuth)."""

import asyncio
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("hhanalyst.scraper")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}

_EXP_MAP = {
    "noExperience": ("noExperience", "Нет опыта"),
    "between1And3": ("between1And3", "От 1 года до 3 лет"),
    "between3And6": ("between3And6", "От 3 до 6 лет"),
    "moreThan6": ("moreThan6", "Более 6 лет"),
}

_CARD_QA = re.compile(r"^vacancy-serp__vacancy(\s|$)")
_CONCURRENCY = 10

_LEGAL_PREFIX = re.compile(
    r"^(ООО|ОАО|ЗАО|ПАО|АО|ИП|ТОО|АНО|НКО|ФГУП|МУП|НПП|ГК)"
    r"(?=[А-ЯЁA-Z«\"])",
)


def _clean_employer(name: str) -> str:
    name = _LEGAL_PREFIX.sub(r"\1 ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _parse_salary(text: str) -> Optional[dict]:
    text = text.replace("\xa0", "").replace(" ", "").strip()
    currency = "RUR"
    for cur_name, cur_code in [("руб", "RUR"), ("₽", "RUR"), ("USD", "USD"), ("EUR", "EUR")]:
        if cur_name in text:
            currency = cur_code
            break
    nums = [int(n) for n in re.findall(r"\d+", text)]
    if not nums:
        return None
    if "от" in text and "до" in text and len(nums) >= 2:
        return {"from": nums[0], "to": nums[1], "currency": currency}
    if "от" in text:
        return {"from": nums[0], "to": None, "currency": currency}
    if "до" in text:
        return {"from": None, "to": nums[0], "currency": currency}
    if len(nums) == 1:
        return {"from": nums[0], "to": nums[0], "currency": currency}
    return {"from": nums[0], "to": nums[1], "currency": currency}


def _parse_search_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    cards = soup.find_all(attrs={"data-qa": _CARD_QA})
    for card in cards:
        title_el = card.find(attrs={"data-qa": "serp-item__title-text"})
        if not title_el:
            continue

        link_el = card.find(attrs={"data-qa": "serp-item__title"})
        href = link_el.get("href", "") if link_el else ""

        area_el = card.find(attrs={"data-qa": "vacancy-serp__vacancy-address"})
        area_text = area_el.get_text(strip=True) if area_el else ""
        city = area_text.split(",")[0].strip() if area_text else ""

        employer_el = card.find(attrs={"data-qa": "vacancy-serp__vacancy-employer-text"})
        employer_name = _clean_employer(employer_el.get_text(strip=True)) if employer_el else ""

        exp_id, exp_name = "", ""
        for eid, (ecode, ename) in _EXP_MAP.items():
            if card.find(attrs={"data-qa": f"vacancy-serp__vacancy-work-experience-{eid}"}):
                exp_id, exp_name = ecode, ename
                break

        salary = None
        sal_el = card.find(attrs={"data-qa": re.compile(r"vacancy-serp__compensation")})
        if sal_el:
            salary = _parse_salary(sal_el.get_text())

        results.append({
            "id": "",
            "name": title_el.get_text(strip=True),
            "url": href,
            "area": {"id": "", "name": city},
            "employer": {"name": employer_name} if employer_name else None,
            "salary": salary,
            "snippet": {"requirement": "", "responsibility": ""},
            "experience": {"id": exp_id, "name": exp_name},
            "description": "",
        })

    return results


def _parse_vacancy_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    info: dict = {"description": "", "skills": []}

    desc_el = soup.find(attrs={"data-qa": "vacancy-description"})
    if desc_el:
        info["description"] = desc_el.get_text(separator=" ", strip=True)

    for tag in soup.find_all(attrs={"data-qa": "skills-element"}):
        text = tag.get_text(strip=True)
        if text:
            info["skills"].append(text)

    return info


async def _fetch_vacancy_detail(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, vacancy: dict
) -> None:
    url = vacancy.get("url", "")
    if not url:
        return
    async with sem:
        try:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                return
            vid_m = re.search(r"/vacancy/(\d+)", str(resp.url))
            if vid_m:
                vacancy["id"] = vid_m.group(1)
            info = _parse_vacancy_page(resp.text)
            vacancy["description"] = info["description"]
            if info["skills"]:
                vacancy["snippet"]["requirement"] = ", ".join(info["skills"])
        except Exception as exc:
            logger.debug("Failed to fetch %s: %s", url, exc)


async def scrape_vacancies(query: str, area: str = "", max_pages: int = 3) -> list[dict]:
    all_vacancies: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0, headers=_HEADERS) as client:
        for page in range(max_pages):
            params = {
                "text": query,
                "items_on_page": 20,
                "page": page,
            }
            if area:
                params["area"] = area

            resp = await client.get(
                "https://hh.ru/search/vacancy", params=params, follow_redirects=True
            )
            if resp.status_code != 200:
                if page == 0:
                    raise RuntimeError(
                        f"hh.ru вернул {resp.status_code} при поиске вакансий"
                    )
                break

            vacancies = _parse_search_page(resp.text)
            if not vacancies:
                break
            all_vacancies.extend(vacancies)

        sem = asyncio.Semaphore(_CONCURRENCY)
        tasks = [
            _fetch_vacancy_detail(client, sem, v)
            for v in all_vacancies
            if v.get("url")
        ]
        if tasks:
            await asyncio.gather(*tasks)

    return all_vacancies
