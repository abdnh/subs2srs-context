import json
from typing import Any, Tuple
import re

from aqt.gui_hooks import webview_did_receive_js_message
from anki.hooks import field_filter
from anki.template import TemplateRenderContext
from anki.collection import SearchNode
from aqt import mw
from aqt.sound import play
from aqt.browser.previewer import Previewer
from aqt.clayout import CardLayout

from . import consts

PLAY_BUTTON = """<a class="replay-button soundLink" href=# onclick="pycmd('{cmd}:play:{filename}'); return false;">
    <svg class="playImage" viewBox="0 0 64 64" version="1.1" style="{transform}">
        <circle cx="32" cy="32" r="29" />
        <path d="M56.502,32.301l-37.502,20.101l0.329,-40.804l37.173,20.703Z" />
    </svg>
</a>"""

TOGGLE_CONTEXT_BUTTON = """<button id="subs2srs-context-toggle" onclick="pycmd('{cmd}:show:{notetype}:{ep}:{seq}'); return false;" style="display: block; margin: 5px auto;">{label}</button>"""

SOUND_REF_RE = re.compile(r"\[sound:(.*?)\]")
NOTES_FIELD_RE = re.compile(r"(?P<ep>\d+)_(?P<seq>\d+)")


def add_filter(
    field_text: str, field_name: str, filter_name: str, ctx: TemplateRenderContext
):
    if filter_name != consts.FILTER_NAME:
        return field_text
    note = ctx.note()
    if "Notes" not in note:
        return
    notes = note["Notes"]
    match = NOTES_FIELD_RE.match(notes)
    if not match:
        return field_text
    notetype = mw.col.models.get(note.mid)["name"]
    ep = match.group("ep")
    seq = int(match.group("seq"))

    button_text = TOGGLE_CONTEXT_BUTTON.format(
        cmd=consts.FILTER_NAME,
        label=consts.ADDON_NAME,
        notetype=notetype,
        ep=ep,
        seq=seq,
    )
    return field_text + button_text


def toggle_context_buttons(context: Any, notetype: str, ep: int, seq: int):
    if isinstance(context, Previewer):
        web = context._web
    elif isinstance(context, CardLayout):
        web = context.preview_web
    else:
        web = context.web

    def add_sound_button(side: str, seq: str) -> str:
        nonlocal notetype, ep
        # FIXME: do we need to pad with zeros?
        search_terms = [f"Notes:{ep}_{seq}*", SearchNode(note=notetype)]
        search = mw.col.build_search_string(*search_terms)
        nids = mw.col.find_notes(search)
        if not nids:
            return ""
        next_note = mw.col.get_note(nids[0])
        next_sound = next_note["Audio"]
        m = SOUND_REF_RE.match(next_sound)
        if m:
            filename = m.group(1)
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
        ep = int(parts[3])
        seq = int(parts[4])
        toggle_context_buttons(context, notetype, ep, seq)
    return (True, None)


field_filter.append(add_filter)
webview_did_receive_js_message.append(handle_play_message)
