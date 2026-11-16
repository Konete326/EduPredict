import os
import threading
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import ConnectionFailure

COLLECTIONS = (
    "users",
    "student_records",
    "predictions",
    "datasets_log",
    "notifications",
    "support_tickets",
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
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def _build_client(self, uri):
        return MongoClient(
            uri,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
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
        client = self.get_client()
        if client is None:
            return {
                "connected": False,
                "error": self._last_error or "MONGODB_URI is not configured.",
            }
        try:
            client.admin.command("ping")
            return {"connected": True, "error": None}
        except Exception as exc:
            return {"connected": False, "error": str(exc)}

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
        return True
    except Exception:
        return False


def check_db_health():
    return MongoDBClient().check_health()
