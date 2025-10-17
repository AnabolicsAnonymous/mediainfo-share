"""
NOTICE OF LICENSE.

Copyright 2025 @AnabolicsAnonymous

Licensed under the Affero General Public License v3.0 (AGPL-3.0)

This program is free software: you can redistribute it and/or modify
it under the terms of the Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, Any
from dotenv import load_dotenv
from models import MediaInfo

load_dotenv()


class Database:
    """Database class for managing media information storage."""

    def __init__(self, db_path: str = "mediainfo.db"):
        """Initialize database connection and setup.

        Args:
            db_path (str): Path to the SQLite database file
        """
        configured_path = os.getenv("DATABASE_PATH")
        self.db_path = configured_path if configured_path else db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.media_folder = os.getenv("UPLOAD_FOLDER", "static/media")
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get a new database connection.

        Returns:
            sqlite3.Connection: A new database connection with Row factory
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database with required tables."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_info (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    original_filename TEXT,
                    uploaded_on TIMESTAMP NOT NULL,
                    expiration TIMESTAMP,
                    password TEXT,
                    raw_output TEXT,
                    parsed_info TEXT
                )
            """
            )

    def save_media_info(self, media: MediaInfo) -> bool:
        """Save media information to database."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO media_info (
                        id, filename, original_filename, uploaded_on, 
                        expiration, password, raw_output, parsed_info
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        media.media_id,
                        media.filename,
                        media.original_filename,
                        media.uploaded_on.isoformat(),
                        media.expiration.isoformat() if media.expiration else None,
                        media.password,
                        media.raw_output,
                        json.dumps({
                            "general": media.general.__dict__,
                            "video": {
                                **media.video.__dict__,
                            },
                            "audio": [track.__dict__ for track in media.audio],
                            "subtitles": [sub.__dict__ for sub in media.subtitles]
                        })
                    ),
                )
            return True
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            return False

    def get_media_info(self, media_id: str) -> Optional[MediaInfo]:
        """Get media info by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM media_info WHERE id = ?", (media_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                columns = [description[0] for description in cursor.description]
                row_dict = dict(zip(columns, row))

                if row_dict.get("parsed_info"):
                    try:
                        parsed_info = json.loads(row_dict["parsed_info"])
                        row_dict["parsed"] = parsed_info
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON data: {str(e)}")
                        row_dict["parsed"] = {}

                return MediaInfo.from_dict(row_dict)
        except sqlite3.Error as e:
            print(f"Database error while getting media info: {str(e)}")
            return None
        except (KeyError, TypeError) as e:
            print(f"Data structure error while getting media info: {str(e)}")
            return None

    def delete_expired_media(self) -> int:
        """Delete expired media entries and their files.

        Returns:
            int: Number of entries deleted
        """
        try:
            with self.get_connection() as conn:
                # Get expired entries
                cursor = conn.execute(
                    "SELECT filename FROM media_info WHERE expiration < ?",
                    (datetime.now().isoformat(),),
                )
                expired_files = cursor.fetchall()

                # Delete files
                for file in expired_files:
                    file_path = os.path.join(self.media_folder, file["filename"])
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {str(e)}")

                # Delete database entries
                cursor = conn.execute(
                    "DELETE FROM media_info WHERE expiration < ?",
                    (datetime.now().isoformat(),),
                )
                deleted_count = cursor.rowcount

                return deleted_count
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            return 0

    def update_media_info(self, media_id: str, **kwargs: Any) -> bool:
        """Update media information in database.

        Args:
            media_id (str): ID of the media to update
            **kwargs: Fields to update and their values

        Returns:
            bool: True if update was successful, False otherwise
        """
        valid_fields = {
            "filename",
            "original_filename",
            "expiration",
            "password",
            "raw_output",
            "parsed_info",
        }
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not update_fields:
            return False

        try:
            with self.get_connection() as conn:
                placeholders = ", ".join(f"{k} = ?" for k in update_fields)
                query = f"UPDATE media_info SET {placeholders} WHERE id = ?"
                values = list(update_fields.values()) + [media_id]
                conn.execute(query, values)
                return True
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            return False


def get_db():
    """Get database connection."""
    db_path = os.getenv("DATABASE_PATH", "mediainfo.db")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with required tables."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS media_info (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            original_filename TEXT,
            uploaded_on TIMESTAMP NOT NULL,
            expiration TIMESTAMP,
            password TEXT,
            raw_output TEXT,
            parsed_info TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS media_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id TEXT NOT NULL,
            section_type TEXT NOT NULL,
            section_data TEXT NOT NULL,
            FOREIGN KEY (media_id) REFERENCES media_info (id)
        )
    """
    )

    conn.commit()
    conn.close()


def save_media_info(
    media_id,
    filename,
    original_filename,
    raw_output,
    parsed_info,
    expiration=None,
    password=None,
):
    """Save media information to database."""
    conn = get_db()
    cursor = conn.cursor()

    try:
        if not isinstance(parsed_info, dict):
            parsed_info = {}

        if "general" not in parsed_info:
            parsed_info["general"] = {
                "format": "",
                "duration": "",
                "bitrate": "",
                "size": "",
            }
        if "video" not in parsed_info:
            parsed_info["video"] = {
                "format": "",
                "width": "", 
                "height": "",
                "aspect_ratio": "",
                "frame_rate": "",
                "bit_rate": "",
                "bit_depth": "",
                "hdr_format": "",
                "color_primaries": "",
                "transfer_characteristics": ""
            }
        if "audio" not in parsed_info:
            parsed_info["audio"] = []
        if "subtitles" not in parsed_info:
            parsed_info["subtitles"] = []

        cursor.execute(
            """
            INSERT INTO media_info (
                id, filename, original_filename, uploaded_on,
                expiration, password, raw_output, parsed_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                media_id,
                filename,
                original_filename,
                datetime.now().isoformat(),
                expiration.isoformat() if expiration else None,
                password,
                raw_output,
                json.dumps(parsed_info) if parsed_info else None,
            ),
        )

        conn.commit()
        return True
    except (sqlite3.Error, json.JSONDecodeError) as e:
        conn.rollback()
        print(f"Error saving media info: {str(e)}")
        return False
    finally:
        conn.close()


def get_media_info(media_id):
    """Get media information from database."""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM media_info WHERE id = ?", (media_id,))
        media = cursor.fetchone()

        if not media:
            return None

        media_dict = dict(media)

        default_structure = {
            "general": {"format": "", "duration": "", "bitrate": "", "size": ""},
            "video": {
                "format": "",
                "width": "", 
                "height": "",
                "aspect_ratio": "",
                "frame_rate": "",
                "bit_rate": "",
                "bit_depth": "",
                "hdr_format": "",
                "color_primaries": "",
                "transfer_characteristics": ""
            },
            "audio": [],
            "subtitles": [],
            "raw_output": media_dict.get("raw_output", ""),
        }

        if media_dict.get("parsed_info"):
            try:
                parsed_info = json.loads(media_dict["parsed_info"])
                # Update default structure with parsed info
                for key, value in parsed_info.items():
                    if key in default_structure:
                        if isinstance(default_structure[key], dict):
                            default_structure[key].update(value)
                        else:
                            default_structure[key] = value
            except json.JSONDecodeError:
                pass

        if "parsed_info" in media_dict:
            del media_dict["parsed_info"]

        media_dict.update(default_structure)

        return media_dict
    finally:
        conn.close()


def delete_expired_media():
    """Delete expired media entries from database."""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM media_info WHERE expiration < ?",
            (datetime.now().isoformat(),),
        )
        expired = cursor.fetchall()

        if expired:
            # Delete media info
            cursor.execute(
                "DELETE FROM media_info WHERE expiration < ?",
                (datetime.now().isoformat(),),
            )
            conn.commit()

        return len(expired)
    finally:
        conn.close()


def update_media_info(media_id, **kwargs):
    """Update media information in database."""
    conn = get_db()
    cursor = conn.cursor()

    try:

        update_fields = []
        values = []
        for key, value in kwargs.items():
            if key in [
                "filename",
                "original_filename",
                "expiration",
                "password",
                "raw_output",
                "parsed_info",
            ]:
                update_fields.append(f"{key} = ?")
                if key == "parsed_info" and value:
                    values.append(json.dumps(value))
                else:
                    values.append(value)

        if update_fields:
            values.append(media_id)
            cursor.execute(
                f"""
                UPDATE media_info 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """,
                values,
            )
            conn.commit()
            return True
        return False
    finally:
        conn.close()
