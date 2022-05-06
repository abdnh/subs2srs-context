import re

from anki.errors import NotFoundError
from anki.notes import NoteId
from aqt import mw

from . import consts


class Subs2srsContext:
    PLAY_BUTTON = """<a class="replay-button soundLink" href=# onclick="pycmd('{cmd}:play:{filename}'); return false;">
        <svg class="playImage" viewBox="0 0 64 64" version="1.1" style="{transform}">
            <circle cx="32" cy="32" r="29" />
            <path d="M56.502,32.301l-37.502,20.101l0.329,-40.804l37.173,20.703Z" />
        </svg>
    </a>"""

    SOUND_REF_RE = re.compile(r"\[sound:(.*?)\]")

    def get_audio_filename(self, nid: NoteId) -> str:
        try:
            note = mw.col.get_note(nid)
        except NotFoundError:
            return ""
        if "Audio" not in note:
            return ""
        sound = note["Audio"]
        match = self.SOUND_REF_RE.match(sound)
        if match:
            return match.group(1)
        return ""

    def get_audio_button(self, nid: NoteId, position: str) -> str:
        button_text = ""
        neighbor_nid = (nid + 1) if position == "next" else (nid - 1)
        filename = self.get_audio_filename(NoteId(neighbor_nid))
        if filename:
            button_text = self.PLAY_BUTTON.format(
                cmd=consts.FILTER_NAME,
                filename=filename,
                transform="transform: scale(-1,1);" if position == "prev" else "",
            )
        return button_text

    def get_audio_buttons(self, nid: NoteId) -> str:
        prev_button_text = self.get_audio_button(nid, "prev")
        next_button_text = self.get_audio_button(nid, "next")
        buttons_text = f"<div>{prev_button_text}{next_button_text}</div>"
        return buttons_text
