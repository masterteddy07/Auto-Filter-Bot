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
    # Minimum valid: must start with "mongodb" and have '@' if username/password in string version
    # SRV uris (MongoDB Atlas) start with mongodb+srv:// and may not have username
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

# ...rest of your existing functions remain unchanged...
async def save_file(media):
    file_id = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    file_caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption))
    
    document = {
        '_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': file_caption
    }
    
    try:
        collection.insert_one(document)
        logger.info(f'Saved - {file_name}')
        return 'suc'
    except DuplicateKeyError:
        logger.warning(f'Already Saved - {file_name}')
        return 'dup'
    except OperationFailure:
        if SECOND_FILES_DATABASE_URL:
            try:
                second_collection.insert_one(document)
                logger.info(f'Saved to 2nd db - {file_name}')
                return 'suc'
            except DuplicateKeyError:
                logger.warning(f'Already Saved in 2nd db - {file_name}')
                return 'dup'
        else:
            logger.error(f'your FILES_DATABASE_URL is already full, add SECOND_FILES_DATABASE_URL')
            return 'err'
