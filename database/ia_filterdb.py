import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo import MongoClient, TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure
from info import USE_CAPTION_FILTER, FILES_DATABASE_URL, SECOND_FILES_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

logger = logging.getLogger(__name__)

# Always provide a URI fallback - never allow empty string in MongoClient
files_db_url = FILES_DATABASE_URL if FILES_DATABASE_URL and "@" in FILES_DATABASE_URL else "mongodb://localhost:27017/filesdb"
client = MongoClient(files_db_url)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]
second_collection = None

try:
    collection.create_index([("file_name", TEXT)])
except OperationFailure as e:
    if 'quota' in str(e).lower():
        if not SECOND_FILES_DATABASE_URL:
            logger.error('your FILES_DATABASE_URL is already full, add SECOND_FILES_DATABASE_URL')
        else:
            logger.info('FILES_DATABASE_URL is full, now using SECOND_FILES_DATABASE_URL')
    else:
        logger.exception(e)

if SECOND_FILES_DATABASE_URL and "@" in SECOND_FILES_DATABASE_URL:
    second_client = MongoClient(SECOND_FILES_DATABASE_URL)
    second_db = second_client[DATABASE_NAME]
    second_collection = second_db[COLLECTION_NAME]
    second_collection.create_index([("file_name", TEXT)])

def is_second_db_configured() -> bool:
    return bool(SECOND_FILES_DATABASE_URL and 'second_collection' in globals() and second_collection is not None)

def second_db_count_documents():
    return second_collection.count_documents({}) if second_collection else 0

def db_count_documents():
    return collection.count_documents({})

def get_primary_db_storage():
    stats = db.command("dbStats")
    return stats.get('storageSize', 0)

def get_secondary_db_storage():
    if not is_second_db_configured():
        return 0
    stats = second_db.command("dbStats")
    return stats.get('storageSize', 0)

# rest of your functions unchanged...

