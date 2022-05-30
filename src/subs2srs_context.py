import re
from typing import List, Optional

from anki.collection import Collection
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

    def get_audio_filename(self, nid: NoteId, col: Optional[Collection] = None) -> str:
        col = col or mw.col
        try:
            note = col.get_note(nid)
        except NotFoundError:
            return ""
        if "Audio" not in note:
            return ""
        sound = note["Audio"]
        match = self.SOUND_REF_RE.match(sound)
        if match:
            return match.group(1)
        return ""

    def get_audio_button(
        self,
        nid: NoteId,
        position: str,
        flip: bool = False,
        col: Optional[Collection] = None,
    ) -> str:
        button_text = ""
        neighbor_nid = (nid + 1) if position == "next" else (nid - 1)
        filename = self.get_audio_filename(NoteId(neighbor_nid), col=col)
        if filename:
            button_text = self.PLAY_BUTTON.format(
                cmd=consts.FILTER_NAME,
                filename=filename,
                transform="transform: scale(-1,1);" if flip else "",
            )
        return button_text

    def get_audio_buttons(
        self, nid: NoteId, flip: bool = True, col: Optional[Collection] = None
    ) -> List[str]:
        prev_button = self.get_audio_button(nid, "prev", flip=flip, col=col)
        next_button = self.get_audio_button(nid, "next", col=col)
        return [prev_button, next_button]

    def get_expressions(
        self, nid: NoteId, col: Optional[Collection] = None
    ) -> List[str]:
        """Get the contents of the Expression field for the previous and next subs2srs notes."""
        col = col or mw.col
        contents = []
        nids = [nid - 1, nid + 1]
        for n in nids:
            try:
                note = col.get_note(NoteId(n))
            except NotFoundError:
                contents.append("")
                continue
            if "Expression" not in note:
                contents.append("")
                continue
            expression = note["Expression"]
            contents.append(expression)

        return contents
