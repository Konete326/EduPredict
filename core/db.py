import os
import threading
import time
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import ConnectionFailure

HEALTH_CACHE_TTL_SECONDS = 60.0

_CACHE_LOCK = threading.Lock()
_MEMORY_CACHE = {}
_CACHE_EPOCH = 0


def get_cached(key, second, third=None, ttl=45.0):
    if callable(second):
        builder_fn = second
        ttl_seconds = float(third) if third is not None else float(ttl)
    elif callable(third):
        ttl_seconds = float(second)
        builder_fn = third
    else:
        raise TypeError("get_cached requires a callable builder function.")

    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _MEMORY_CACHE.get(key)
        if entry is not None and now < entry[0]:
            return entry[1]
        epoch = _CACHE_EPOCH
    value = builder_fn()
    expires_at = time.monotonic() + ttl_seconds
    with _CACHE_LOCK:
        if _CACHE_EPOCH == epoch:
            _MEMORY_CACHE[key] = (expires_at, value)
    return value


def invalidate_cache(prefix=""):
    global _CACHE_EPOCH
    with _CACHE_LOCK:
        _CACHE_EPOCH += 1
        if not prefix:
            _MEMORY_CACHE.clear()
            return
        target = str(prefix)
        for k in [key for key in _MEMORY_CACHE if str(key).startswith(target)]:
            del _MEMORY_CACHE[k]

COLLECTIONS = (
    "users", "student_records", "predictions",
    "datasets_log", "notifications", "support_tickets", "courses",
    "classes", "semesters",
)


class MongoDBClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._client = None
                    instance._uri = None
                    instance._db_name = None
                    instance._last_error = None
                    instance._health_cache = None
                    instance._health_cache_at = 0.0
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def _build_client(self, uri):
        max_pool = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
        min_pool = int(os.getenv("MONGODB_MIN_POOL_SIZE", "2"))
        idle_time = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "45000"))
        socket_timeout = int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "10000"))
        selection_timeout = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "3000"))
        connect_timeout = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "3000"))
        return MongoClient(
            uri,
            maxPoolSize=max_pool,
            minPoolSize=min_pool,
            maxIdleTimeMS=idle_time,
            socketTimeoutMS=socket_timeout,
            serverSelectionTimeoutMS=selection_timeout,
            connectTimeoutMS=connect_timeout,
        )

    def get_client(self):
        uri = (os.getenv("MONGODB_URI") or "").strip()
        db_name = (os.getenv("MONGODB_DB_NAME") or "edupredict_db").strip() or "edupredict_db"
        with self._lock:
            if self._client is not None and self._uri == uri and self._db_name == db_name:
                return self._client
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            if self._uri != uri or self._db_name != db_name:
                self._health_cache = None
                self._health_cache_at = 0.0
            self._uri = uri
            self._db_name = db_name
            if not uri:
                self._last_error = "MONGODB_URI environment variable is not set."
                return None
            try:
                self._client = self._build_client(uri)
                self._last_error = None
            except Exception as exc:
                self._client = None
                self._last_error = str(exc)
            return self._client

    def get_db(self):
        client = self.get_client()
        if client is None:
            raise ConnectionFailure(self._last_error or "MongoDB client is not available.")
        return client[self._db_name]

    def get_collection(self, name):
        return self.get_db()[name]

    @property
    def client(self):
        return self.get_client()

    @property
    def db(self):
        return self.get_db()

    def check_health(self):
        uri = (os.getenv("MONGODB_URI") or "").strip()
        db_name = (os.getenv("MONGODB_DB_NAME") or "edupredict_db").strip() or "edupredict_db"
        now = time.monotonic()
        with self._lock:
            if (
                self._health_cache is not None
                and self._uri == uri
                and self._db_name == db_name
                and (now - self._health_cache_at) < HEALTH_CACHE_TTL_SECONDS
            ):
                return dict(self._health_cache)

        client = self.get_client()
        if client is None:
            result = {
                "connected": False,
                "error": self._last_error or "MONGODB_URI is not configured.",
            }
        else:
            try:
                client.admin.command("ping")
                result = {"connected": True, "error": None}
            except Exception as exc:
                result = {"connected": False, "error": str(exc)}

        with self._lock:
            if self._uri == uri and self._db_name == db_name:
                self._health_cache = dict(result)
                self._health_cache_at = time.monotonic()
        return result

    def close(self):
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            self._uri = None
            self._db_name = None
            self._last_error = None
            self._health_cache = None
            self._health_cache_at = 0.0
        invalidate_cache()


def get_client():
    return MongoDBClient().get_client()


def get_db():
    return MongoDBClient().get_db()


def get_collection(name):
    return MongoDBClient().get_collection(name)


def users_col():
    return get_collection("users")


def student_records_col():
    return get_collection("student_records")


def predictions_col():
    return get_collection("predictions")


def datasets_log_col():
    return get_collection("datasets_log")


def notifications_col():
    return get_collection("notifications")


def support_tickets_col():
    return get_collection("support_tickets")


def courses_col():
    return get_collection("courses")


def classes_col():
    return get_collection("classes")


def semesters_col():
    return get_collection("semesters")


def ensure_indexes():
    try:
        users = users_col()
        users.create_index([("email", ASCENDING)], unique=True, sparse=True)
        users.create_index([("user_id", ASCENDING)])
        records = student_records_col()
        records.create_index([("student_id", ASCENDING)])
        records.create_index([("batch", ASCENDING)])
        records.create_index([("updated_at", DESCENDING)])
        preds = predictions_col()
        preds.create_index([("student_id", ASCENDING)])
        preds.create_index([("generated_at", DESCENDING)])
        notifs = notifications_col()
        notifs.create_index([("target_role", ASCENDING)])
        notifs.create_index([("target_user_id", ASCENDING)])
        notifs.create_index([("is_read", ASCENDING)])
        notifs.create_index([("created_at", DESCENDING)])
        courses_col().create_index([("course_code", ASCENDING)], unique=True)
        return True
    except Exception:
        return False


def check_db_health():
    return MongoDBClient().check_health()


DEFAULT_PORTAL_BRANDING = ("EduPredict Academic Portal", "Fall 2026")


def resolve_portal_branding(data=None, db_connected=True):
    inst = str(data.get("institution_name") or "").strip() if isinstance(data, dict) else ""
    term = str(data.get("current_term") or "").strip() if isinstance(data, dict) else ""
    if (not inst or not term) and db_connected:
        try:
            doc = get_cached(
                "portal:branding",
                lambda: get_collection("system_settings").find_one({"setting_key": "portal_config"}, {"_id": 0}) or {},
                ttl=30.0,
            )
            if isinstance(doc, dict):
                inst = inst or str(doc.get("institution_name") or "").strip()
                term = term or str(doc.get("current_term") or "").strip()
        except Exception:
            pass
    return inst or DEFAULT_PORTAL_BRANDING[0], term or DEFAULT_PORTAL_BRANDING[1]
