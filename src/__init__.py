import os
import re
from typing import Any, List, Tuple

from anki.errors import NotFoundError
from anki.hooks import field_filter
from anki.notes import NoteId
from anki.template import TemplateRenderContext
from aqt import mw
from aqt.editor import Editor
from aqt.gui_hooks import editor_did_init_buttons, webview_did_receive_js_message
from aqt.sound import play

from . import consts

PLAY_BUTTON = """<a class="replay-button soundLink" href=# onclick="pycmd('{cmd}:play:{filename}'); return false;">
    <svg class="playImage" viewBox="0 0 64 64" version="1.1" style="{transform}">
        <circle cx="32" cy="32" r="29" />
        <path d="M56.502,32.301l-37.502,20.101l0.329,-40.804l37.173,20.703Z" />
    </svg>
</a>"""

SOUND_REF_RE = re.compile(r"\[sound:(.*?)\]")


def get_subs2srs_audio_filename(nid: NoteId) -> str:
    try:
        note = mw.col.get_note(nid)
    except NotFoundError:
        return ""
    if "Audio" not in note:
        return ""
    sound = note["Audio"]
    match = SOUND_REF_RE.match(sound)
    if match:
        return match.group(1)
    return ""


def get_subs2srs_audio_button(nid: NoteId, position: str) -> str:
    button_text = ""
    neighbor_nid = (nid + 1) if position == "next" else (nid - 1)
    filename = get_subs2srs_audio_filename(NoteId(neighbor_nid))
    if filename:
        button_text = PLAY_BUTTON.format(
            cmd=consts.FILTER_NAME,
            filename=filename,
            transform="transform: scale(-1,1);" if position == "prev" else "",
        )
    return button_text


def add_filter(
    field_text: str, field_name: str, filter_name: str, ctx: TemplateRenderContext
) -> str:
    if not filter_name.startswith(consts.FILTER_NAME):
        return field_text
    prev_button_text = get_subs2srs_audio_button(ctx.note().id, "prev")
    next_button_text = get_subs2srs_audio_button(ctx.note().id, "next")
    buttons_text = f"<div>{prev_button_text}{next_button_text}</div>"
    return field_text + buttons_text


def handle_play_message(
    handled: Tuple[bool, Any], message: str, context: Any
) -> Tuple[bool, Any]:
    parts = message.split(":")
    cmd = parts[0]
    if cmd != consts.FILTER_NAME:
        return handled
    subcmd = parts[1]
    if subcmd == "play":
        filename = parts[2]
        play(filename)
    return (True, None)


def play_previous(editor: Editor) -> None:
    audio = get_subs2srs_audio_filename(NoteId(editor.note.id - 1))
    if audio:
        play(audio)


def play_next(editor: Editor) -> None:
    audio = get_subs2srs_audio_filename(NoteId(editor.note.id + 1))
    if audio:
        play(audio)


def add_editor_buttons(buttons: List[str], editor: Editor) -> None:
    prev_button = editor.addButton(
        icon=os.path.join(consts.ICONS_DIR, "previous.svg"),
        cmd="subs2srs_context_previous",
        tip="Play previous subs2srs recording",
        func=play_previous,
    )
    next_button = editor.addButton(
        icon=os.path.join(consts.ICONS_DIR, "next.svg"),
        cmd="subs2srs_context_next",
        tip="Play next subs2srs recording",
        func=play_next,
    )
    buttons.append(prev_button)
    buttons.append(next_button)


field_filter.append(add_filter)
webview_did_receive_js_message.append(handle_play_message)
editor_did_init_buttons.append(add_editor_buttons)
