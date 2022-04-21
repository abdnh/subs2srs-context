import json
import math
import os
from typing import Any, List, Optional, Tuple
import re

from aqt.gui_hooks import webview_did_receive_js_message, editor_did_init_buttons
from anki.hooks import field_filter
from anki.template import TemplateRenderContext
from anki.collection import SearchNode
from aqt import mw
from aqt.sound import play
from aqt.browser.previewer import Previewer
from aqt.clayout import CardLayout
from aqt.editor import Editor
from anki.notes import Note

from . import consts

PLAY_BUTTON = """<a class="replay-button soundLink" href=# onclick="pycmd('{cmd}:play:{filename}'); return false;">
    <svg class="playImage" viewBox="0 0 64 64" version="1.1" style="{transform}">
        <circle cx="32" cy="32" r="29" />
        <path d="M56.502,32.301l-37.502,20.101l0.329,-40.804l37.173,20.703Z" />
    </svg>
</a>"""

TOGGLE_CONTEXT_BUTTON = """<button id="subs2srs-context-toggle" onclick="pycmd('{cmd}:show:{notetype}:{marker}:{ep}:{seq}'); return false;" style="display: block; margin: 5px auto;">{label}</button>"""

SOUND_REF_RE = re.compile(r"\[sound:(.*?)\]")
NOTES_FIELD_RE = re.compile(r"(?P<ep>\d+)_(?P<seq>\d+)")


def get_subs2srs_context(note: Note) -> Optional[Tuple[str, str, int, int]]:
    if "Notes" not in note or "SequenceMarker" not in note:
        return None
    notes = note["Notes"]
    match = NOTES_FIELD_RE.match(notes)
    if not match:
        return None
    notetype = mw.col.models.get(note.mid)["name"]
    ep = int(match.group("ep"))
    seq = int(match.group("seq"))
    marker = note["SequenceMarker"]
    return (notetype, marker, ep, seq)


def get_subs2srs_audio_filename(notetype: str, marker: str, ep: int, seq: int) -> str:
    # TODO: optimize queries
    marker_search = f"SequenceMarker:{marker}"
    search = mw.col.build_search_string(marker_search, f"Notes:{ep}_*")
    ep_nids = mw.col.find_notes(search)
    zero_pad = math.ceil(math.log10(len(ep_nids)))
    seq = str(seq).zfill(zero_pad)
    search_terms = [marker_search, f"Notes:{ep}_{seq}*", SearchNode(note=notetype)]
    search = mw.col.build_search_string(*search_terms)
    nids = mw.col.find_notes(search)
    if not nids:
        return ""
    note = mw.col.get_note(nids[0])
    sound = note["Audio"]
    m = SOUND_REF_RE.match(sound)
    if m:
        return m.group(1)
    return ""


def add_filter(
    field_text: str, field_name: str, filter_name: str, ctx: TemplateRenderContext
):
    if filter_name != consts.FILTER_NAME:
        return field_text
    context = get_subs2srs_context(ctx.note())
    if not context:
        return field_text
    notetype, marker, ep, seq = context
    button_text = TOGGLE_CONTEXT_BUTTON.format(
        cmd=consts.FILTER_NAME,
        label=consts.ADDON_NAME,
        notetype=notetype,
        marker=marker,
        ep=ep,
        seq=seq,
    )
    return field_text + button_text


def toggle_context_buttons(context: Any, notetype: str, marker: str, ep: int, seq: int):
    if isinstance(context, Previewer):
        web = context._web
    elif isinstance(context, CardLayout):
        web = context.preview_web
    else:
        web = context.web

    def add_sound_button(side: str, seq: str) -> str:
        nonlocal notetype, marker, ep
        filename = get_subs2srs_audio_filename(notetype, marker, ep, seq)
        if filename:
            if side == "next":
                button_text = PLAY_BUTTON.format(
                    cmd=consts.FILTER_NAME, filename=filename, transform=""
                )
            else:
                button_text = PLAY_BUTTON.format(
                    cmd=consts.FILTER_NAME,
                    filename=filename,
                    transform="transform: scale(-1,1);",
                )
            return button_text

    next_button_text = add_sound_button("next", seq + 1)
    prev_button_text = add_sound_button("prev", seq - 1)
    buttons_text = f"<div>{prev_button_text}{next_button_text}</div>"
    js = f"""
var subs2srsContextToggle = document.getElementById('subs2srs-context-toggle');
if(!subs2srsContextToggle.dataset.shown) {{
    subs2srsContextToggle.insertAdjacentHTML('afterend', {json.dumps(buttons_text)});
    subs2srsContextToggle.dataset.shown = true;
}}
"""
    web.eval(js)


def handle_play_message(handled: Tuple[bool, Any], message: str, context: Any):
    parts = message.split(":")
    cmd = parts[0]
    if cmd != consts.FILTER_NAME:
        return handled
    subcmd = parts[1]
    if subcmd == "play":
        filename = parts[2]
        play(filename)
    elif subcmd == "show":
        notetype = parts[2]
        marker = parts[3]
        ep = int(parts[4])
        seq = int(parts[5])
        toggle_context_buttons(context, notetype, marker, ep, seq)
    return (True, None)


def play_previous(editor: Editor):
    context = get_subs2srs_context(editor.note)
    if not context:
        return
    notetype, marker, ep, seq = context
    audio = get_subs2srs_audio_filename(notetype, marker, ep, seq - 1)
    if audio:
        play(audio)


def play_next(editor: Editor):
    context = get_subs2srs_context(editor.note)
    if not context:
        return
    notetype, marker, ep, seq = context
    audio = get_subs2srs_audio_filename(notetype, marker, ep, seq + 1)
    if audio:
        play(audio)


def add_editor_buttons(buttons: List[str], editor: Editor):
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
