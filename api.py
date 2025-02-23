import os
import sys
import uuid
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

sys.path.append(os.getcwd())  # prevents a nasty ModuleNotFoundError for imports below
from postgres_db.handler import DBhandler
from type_and_id_parser import TypeAndIdParser
from inconvenience_finder import InconvenienceFinder
from main import determine_type


handler = DBhandler()


@asynccontextmanager
async def lifespan(app: FastAPI):  # before the app starts taking requests, it will load/refresh db data
    handler.update_inconveniences_for_everyone()
    yield


app = FastAPI(lifespan=lifespan)
scheduler = BackgroundScheduler()
scheduler.start()


def refresh_db_data() -> None:
    print('INFO: started refreshing database')
    handler.update_inconveniences_for_everyone(request_uuid='SELF-UPDATE')
    print('INFO: database refreshed')


def refresh_id_data() -> None:
    print('INFO: started refreshing id data')
    TypeAndIdParser(update_json_on_init=True)
    print('INFO: id data refreshed')


scheduler.add_job(refresh_db_data, 'interval', hours=4)  # db data will be refreshed on startup and then every 4 hours
scheduler.add_job(refresh_id_data, 'interval', hours=4)  # same as db data but doesn't refresh on startup


@app.get('/current_inconveniences_for_everyone')
def get_current_inconveniences_for_everyone(request_uuid: str = None):
    if request_uuid:
        status = handler.check_request_status(request_uuid)

        if status == 'Обработка завершена':
            inconveniences = handler.get_inconveniences_for_everyone()
            return inconveniences
        else:
            return {'status': status}

    else:
        request_uuid = str(uuid.uuid4())
        is_refreshing = handler.is_currently_refreshing_data()
        handler.put_request(request_uuid)
        if not is_refreshing:
            scheduler.add_job(handler.update_inconveniences_for_everyone)
        return {'request_uuid': request_uuid}


@app.get('/inconveniences_for_everyone')
def get_inconveniences_for_everyone() -> dict[str, dict[str, list[str]]]:
    inconveniences = handler.get_inconveniences_for_everyone()
    return inconveniences


@app.get("/inconveniences")
def get_inconveniences(name: str) -> dict[str, list[str]]:
    if handler.is_currently_refreshing_data():
        inconveniences = handler.get_inconveniences(name)
    else:
        finder = InconvenienceFinder()
        id_parser = TypeAndIdParser()
        entity_type = determine_type(name)
        schedule_id = id_parser.get_id(entity_type, name)
        inconveniences = finder.get_all_inconveniences(entity_type, schedule_id)
    return inconveniences
