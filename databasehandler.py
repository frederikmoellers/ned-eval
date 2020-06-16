#!/usr/bin/env python3

# Licensed under the EUPL

from typing import Tuple, Union
import sqlite3

NULL = "NULL"


class DatabaseHandler:
    def __init__(self, filename):
        self._db = sqlite3.connect(filename)
        self._device_ids = {}

        self._messages = {}
        self._devices = {}
        self._systems = {}
        self._cursor = None
        self._cursor_last_action_read = True
    
    def __del__(self):
        self._db.commit()
        self._db.close()

    def commit(self):
        self._db.commit()

    def cursor(self, read = True):
        if read and not self._cursor_last_action_read:
            del self._cursor
            self._cursor = None
        if self._cursor is None:
            self._cursor = self._db.cursor()
            self._cursor_last_action_read = read
        return self._cursor

    def messages(self, system_id, from_timestamp = None, to_timestamp = None):
        parameters = [system_id]
        from_part = to_part = ""
        if from_timestamp is not None:
            from_part = "AND timestamp >= ?"
            parameters.append(from_timestamp)
        if to_timestamp is not None:
            to_part = "AND timestamp <= ?"
            parameters.append(to_timestamp)
        cursor = self._db.cursor()
        for row in cursor.execute("SELECT * FROM messages WHERE system_id = ? {} {} ORDER BY timestamp ASC;".format(from_part, to_part), parameters):
            yield Message(self, *row)

    def systems(self):
        cursor = self._db.cursor()
        for row in cursor.execute("SELECT * FROM systems;"):
            yield System(self, *row)


class Message:
    def __init__(self, dbhandler, id, system_id, timestamp):
        self._dbh: DatabaseHandler = dbhandler
        self.id: int = id
        self.system_id: Union[str, int] = system_id
        self.timestamp: float = timestamp

class System:
    def __init__(self, dbhandler, id, description):
        self._dbh = dbhandler
        self.id = id
        self.description = description

    def messages(self, from_timestamp = None, to_timestamp = None):
        for message in self._dbh.messages(self.id, from_timestamp, to_timestamp):
            yield message

    def timespan(self, override_from = None, override_to = None, fix = True) -> Tuple[float, float]:
        """
        Return the timespan of the system as a 2-tuple (first_message_timestamp, last_message_timestamp)
        Parameters:
            override_from Override the first message timestamp with this value
            override_to Override the last message timestamp with this value
            fix Fix the override values to match actual timestamps (i.e. return the first timestamp >= override_from and the last timestamp <= override_to)
        """
        cursor = self._dbh.cursor()
        if override_from is not None:
            if fix:
                cursor.execute("SELECT timestamp FROM messages WHERE system_id = ? AND timestamp >= ? ORDER BY timestamp ASC LIMIT 1;", (self.id, override_from))
                from_ts = cursor.fetchone()[0]
            else:
                from_ts = override_from
        else:
            cursor.execute("SELECT timestamp FROM messages WHERE system_id = ? ORDER BY timestamp ASC LIMIT 1;", (self.id,))
            from_ts = cursor.fetchone()[0]
        if override_to is not None:
            if fix:
                cursor.execute("SELECT timestamp FROM messages WHERE system_id = ? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 1;", (self.id, override_to))
                to_ts = cursor.fetchone()[0]
            else:
                to_ts = override_to
        else:
            cursor.execute("SELECT timestamp FROM messages WHERE system_id = ? ORDER BY timestamp DESC LIMIT 1;", (self.id,))
            to_ts = cursor.fetchone()[0]
        return from_ts, to_ts

class Device:
    def __init__(self, dbhandler, id, system_id, description, send_only):
        self._dbh = dbhandler
        self.id = id
        self.system_id = system_id
        self.description = description
        self.send_only = (send_only == 1)
