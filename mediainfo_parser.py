"""
NOTICE OF LICENSE.

Copyright 2025 @AnabolicsAnonymous

Licensed under the Affero General Public License v3.0 (AGPL-3.0)

This program is free software: you can redistribute it and/or modify
it under the terms of the Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple
from models import AudioTrack

Rule = Tuple[str, Callable[[str], str]]


@dataclass
class ParserState:
    """Keep track of the current section and audio track during parsing."""

    section: Optional[str] = None
    track: Optional[AudioTrack] = None
    track_type: Optional[str] = None

class MediaInfoParser:
    """Class for parsing MediaInfo output into a dictionary"""
    def __init__(self):
        self.language_flags = {
            "JP": "🇯🇵",
            "JA": "🇯🇵",
            "EN": "🇺🇸",
            "US": "🇺🇸",
            "GB": "🇬🇧",
            "FR": "🇫🇷",
            "ES": "🇪🇸",
            "DE": "🇩🇪",
            "IT": "🇮🇹",
            "CN": "🇨🇳",
            "ZH": "🇨🇳",
            "KO": "🇰🇷",
            "KR": "🇰🇷",
            "RU": "🇷🇺",
        }
        self._general_rules: Dict[str, Rule] = {}
        self._video_rules: Dict[str, Rule] = {}
        self._audio_rules: Dict[str, Rule] = {}

        self._register_rules(self._general_rules, "format", "format", self._identity)
        self._register_rules(self._general_rules, "duration", "duration", self._identity)
        self._register_rules(
            self._general_rules,
            ["overall bit rate", "bit rate"],
            "bitrate",
            self._identity,
        )
        self._register_rules(
            self._general_rules,
            ["file size", "size"],
            "size",
            self._identity,
        )
        self._register_rules(
            self._general_rules,
            "frame rate",
            "frame_rate",
            self._identity,
        )
        self._register_rules(
            self._general_rules,
            "complete name",
            "complete_name",
            self._identity,
        )

        self._register_rules(self._video_rules, "format", "format", self._identity)
        self._register_rules(
            self._video_rules,
            "width",
            "width",
            self._normalize_dimension,
        )
        self._register_rules(
            self._video_rules,
            "height",
            "height",
            self._normalize_dimension,
        )
        self._register_rules(
            self._video_rules,
            ["display aspect ratio", "aspect ratio"],
            "aspect_ratio",
            self._identity,
        )
        self._register_rules(
            self._video_rules,
            ["frame rate", "frame rate mode"],
            "frame_rate",
            self._identity,
        )
        self._register_rules(
            self._video_rules,
            ["bit rate", "nominal bit rate"],
            "bit_rate",
            self._identity,
        )
        self._register_rules(
            self._video_rules,
            ["bit depth", "bit depth (bits)"],
            "bit_depth",
            self._identity,
        )
        self._register_rules(
            self._video_rules,
            "hdr format",
            "hdr_format",
            self._identity,
        )
        self._register_rules(
            self._video_rules,
            "color primaries",
            "color_primaries",
            self._identity,
        )
        self._register_rules(
            self._video_rules,
            "transfer characteristics",
            "transfer_characteristics",
            self._identity,
        )

        self._register_rules(self._audio_rules, "language", "language", self._identity)
        self._register_rules(self._audio_rules, "format", "format", self._identity)
        self._register_rules(
            self._audio_rules,
            ["channel(s)", "channels"],
            "channels",
            self._identity,
        )
        self._register_rules(
            self._audio_rules,
            ["bit rate", "nominal bit rate"],
            "bit_rate",
            self._identity,
        )
        self._register_rules(
            self._audio_rules,
            "format settings",
            "format_settings",
            self._identity,
        )
        self._register_rules(
            self._audio_rules,
            ["sampling rate", "sampling frequency"],
            "sampling_rate",
            self._identity,
        )
        self._register_rules(
            self._audio_rules,
            "commercial name",
            "commercial_name",
            self._identity,
        )
        self._register_rules(self._audio_rules, "title", "title", self._identity)

    def get_language_flag(self, lang_code: Optional[str]) -> str:
        """Get the language flag for a given language code"""
        if not lang_code:
            return ""

        code = lang_code.strip().upper()
        if "(" in code and ")" in code:
            code = code[code.find("(") + 1 : code.find(")")].strip()

        return self.language_flags.get(code, "")

    def parse_file(self, file_path: str) -> Dict:
        """Parse the MediaInfo output file into a dictionary"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = "\n".join(line.strip() for line in f if line.strip())

            info = {
                "general": {},
                "video": {},
                "audio": [],
                "subtitles": []
            }

            state = ParserState()

            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue

                if self._update_section(line, state, info):
                    continue

                if ":" in line:
                    key, value = map(str.strip, line.split(":", 1))
                    self._parse_key_value(key, value, state, info)

            self._flush_audio_track(info, state)

            for track in info["audio"]:
                if track.get("language"):
                    track["flag"] = self.get_language_flag(track["language"])

            return info

        except Exception as e:
            print(f"Error parsing MediaInfo: {str(e)}")
            raise

    def _parse_key_value(
        self,
        key: str,
        value: str,
        state: ParserState,
        info: Dict,
    ) -> None:
        key = key.lower()
        section = state.section

        if section is None:
            return

        if section == "general":
            self._apply_rule(info["general"], key, value, self._general_rules)
            return

        if section == "video":
            self._apply_rule(info["video"], key, value, self._video_rules)
            return

        if section == "audio" and state.track:
            self._apply_audio_rule(state.track, key, value)
            return

        if section == "text" and key == "language":
            info["subtitles"].append({
                "language": value,
                "flag": self.get_language_flag(value)
            })

    @staticmethod
    def _register_rules(
        target: Dict[str, Rule],
        keys,
        field: str,
        transformer: Callable[[str], str],
    ) -> None:
        if isinstance(keys, (list, tuple, set)):
            for key in keys:
                target[key] = (field, transformer)
        else:
            target[keys] = (field, transformer)

    @staticmethod
    def _identity(value: str) -> str:
        return value

    @staticmethod
    def _normalize_dimension(value: str) -> str:
        return value.replace("pixels", "").replace(" ", "").strip()

    def _apply_rule(
        self,
        target: Dict,
        key: str,
        value: str,
        rules: Dict[str, Rule],
    ) -> None:
        rule = rules.get(key)
        if not rule:
            return
        field, transformer = rule
        target[field] = transformer(value)

    def _apply_audio_rule(self, track: AudioTrack, key: str, value: str) -> None:
        rule = self._audio_rules.get(key)
        if not rule:
            return
        field, transformer = rule
        setattr(track, field, transformer(value))

    def _update_section(
        self,
        line: str,
        state: ParserState,
        info: Dict,
    ) -> bool:
        header = line.lower()
        if header == "general":
            self._flush_audio_track(info, state)
            state.section = "general"
            state.track = None
            state.track_type = None
            return True

        if header.startswith("video"):
            self._flush_audio_track(info, state)
            state.section = "video"
            state.track = None
            state.track_type = None
            return True

        if header.startswith("audio"):
            self._flush_audio_track(info, state)
            state.section = "audio"
            state.track = AudioTrack()
            state.track_type = "audio"
            return True

        if header.startswith("text"):
            self._flush_audio_track(info, state)
            state.section = "text"
            state.track = None
            state.track_type = "text"
            return True

        if header == "menu":
            self._flush_audio_track(info, state)
            state.section = "menu"
            state.track = None
            state.track_type = None
            return True

        return False

    @staticmethod
    def _flush_audio_track(info: Dict, state: ParserState) -> None:
        if state.track and state.track_type == "audio":
            info["audio"].append(state.track.__dict__)
            state.track = None
            state.track_type = None
