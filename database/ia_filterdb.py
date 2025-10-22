import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo import MongoClient, TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure
from info import USE_CAPTION_FILTER, FILES_DATABASE_URL, SECOND_FILES_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

logger = logging.getLogger(__name__)

def valid_mongo_uri(uri):
    if uri and uri.startswith("mongodb"):
        if "@:" in uri or "@" == uri or "@" not in uri:
            return False
        return True
    return False

uri_from_env = FILES_DATABASE_URL or ""
print("DEBUG FILES_DATABASE_URL:", uri_from_env[:10] + "..." if uri_from_env else "Not Set")

if valid_mongo_uri(uri_from_env):
    files_db_url = uri_from_env
else:
    files_db_url = "mongodb://localhost:27017/filesdb"
    logger.warning("FILES_DATABASE_URL was missing or invalid. Falling back to localhost.")

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

if SECOND_FILES_DATABASE_URL and valid_mongo_uri(SECOND_FILES_DATABASE_URL):
    second_client = MongoClient(SECOND_FILES_DATABASE_URL)
    second_db = second_client[DATABASE_NAME]
    second_collection = second_db[COLLECTION_NAME]
    second_collection.create_index([("file_name", TEXT)])

# The rest of your existing functions remain unchanged
