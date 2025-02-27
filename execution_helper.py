import json
from concurrent.futures import ThreadPoolExecutor
try:
    from .type_and_id_parser import TypeAndIdParser
    from .inconvenience_finder import InconvenienceFinder
except ImportError:
    from type_and_id_parser import TypeAndIdParser
    from inconvenience_finder import InconvenienceFinder


def determine_type(name: str) -> int:
    return 1 if any(char.isdigit() for char in name) else 2


def get_inconveniences_for_everyone(finder: InconvenienceFinder) -> dict[str, dict[str, list[str]]]:  # {date: {name: [inconveniences]}}
    """1. Pulls the credentials of every entity from the pre-created json.
       2. Creates a lot of threads and then bombards MIREA website with requests (about 8000 in total), gathering
       all data about everyone's schedules. (the longest step, usually takes 2-5 minutes)
       3. Determines the inconveniences in every single entity's schedule, saving the data in a dict.
       4. Returns the resulting dict."""
    with open('ids_by_type_and_name.json', 'r', encoding='utf-8') as f:
        ids_by_type_and_name = json.loads(f.read())
    all_inconveniences_in_mirea = {}

    for entity_type in range(2, 0, -1):  # first professors, then students
        with ThreadPoolExecutor(max_workers=800) as executor:
            futures = {}
            for name in ids_by_type_and_name[str(entity_type)].keys():
                schedule_id = ids_by_type_and_name[str(entity_type)][name]
                futures[name] = (executor.submit(finder.get_all_inconveniences, entity_type, schedule_id))

        for name in futures.keys():
            inconveniences = futures[name].result()
            if inconveniences:
                for date in inconveniences.keys():
                    if not all_inconveniences_in_mirea.get(date): all_inconveniences_in_mirea[date] = {}
                    all_inconveniences_in_mirea[date][name] = inconveniences[date]
    return all_inconveniences_in_mirea
