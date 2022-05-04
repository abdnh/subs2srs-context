import json
import os
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, Union

from anki.collection import SearchNode
from anki.hooks import field_filter
from anki.notes import Note
from anki.template import TemplateRenderContext
from aqt import mw
from aqt.browser.previewer import Previewer
from aqt.clayout import CardLayout
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

TOGGLE_CONTEXT_BUTTON = """<button id="subs2srs-context-toggle" onclick="pycmd('{cmd}:show:{notetype}:{marker}:{ep}:{seq}'); return false;" style="display: block; margin: 5px auto;">{label}</button>"""

SOUND_REF_RE = re.compile(r"\[sound:(.*?)\]")
NOTES_FIELD_RE = re.compile(r"(?P<ep>\d+)_(?P<seq>\d+)")


@dataclass
class Subs2srsContext:
    notetype: str
    episode: int
    episode_str: str
    sequence: int
    sequence_str: str
    marker: str


def get_subs2srs_context(note: Note) -> Optional[Subs2srsContext]:
    if "Notes" not in note or "SequenceMarker" not in note:
        return None
    notes = note["Notes"]
    match = NOTES_FIELD_RE.match(notes)
    if not match:
        return None
    notetype = mw.col.models.get(note.mid)["name"]
    episode_str = match.group("ep")
    sequence_str = match.group("seq")
    episode = int(episode_str)
    sequence = int(sequence_str)
    marker = note["SequenceMarker"]
    context = Subs2srsContext(
        notetype, episode, episode_str, sequence, sequence_str, marker
    )
    return context


ANKI_WILDCARD_RE = re.compile(r"([\\*_])")


def escape_anki_wildcards(search: str) -> str:
    return ANKI_WILDCARD_RE.sub(r"\\\1", search)


def get_subs2srs_audio_filename(
    notetype: str, marker: str, episode_str: str, sequence: int, sequence_width: int
) -> str:
    sequence_str = str(sequence).zfill(sequence_width)
    search_terms: List[Union[str, SearchNode]] = [
        f"SequenceMarker:{escape_anki_wildcards(marker)}",
        f"Notes:{episode_str}_{sequence_str}*",
        SearchNode(note=notetype),
    ]
    search = mw.col.build_search_string(*search_terms)
    nids = mw.col.find_notes(search)
    if not nids:
        return ""
    note = mw.col.get_note(nids[0])
    sound = note["Audio"]
    match = SOUND_REF_RE.match(sound)
    if match:
        return match.group(1)
    return ""


def add_filter(
    field_text: str, field_name: str, filter_name: str, ctx: TemplateRenderContext
) -> str:
    if filter_name != consts.FILTER_NAME:
        return field_text
    context = get_subs2srs_context(ctx.note())
    if not context:
        return field_text
    button_text = TOGGLE_CONTEXT_BUTTON.format(
        cmd=consts.FILTER_NAME,
        label=consts.ADDON_NAME,
        notetype=context.notetype,
        marker=context.marker,
        ep=context.episode_str,
        seq=context.sequence_str,
    )
    return field_text + button_text


def toggle_context_buttons(
    context: Any, notetype: str, marker: str, episode_str: str, sequence_str: str
) -> None:
    if isinstance(context, Previewer):
        web = context._web  # pylint: disable=protected-access
    elif isinstance(context, CardLayout):
        web = context.preview_web
    else:
        web = context.web

    def add_sound_button(side: str, sequence: int) -> str:
        nonlocal notetype, marker, episode_str
        filename = get_subs2srs_audio_filename(
            notetype, marker, episode_str, sequence, len(sequence_str)
        )
        if not filename:
            return ""
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

    next_button_text = add_sound_button("next", int(sequence_str) + 1)
    prev_button_text = add_sound_button("prev", int(sequence_str) - 1)
    buttons_text = f"<div>{prev_button_text}{next_button_text}</div>"
    js = f"""
var subs2srsContextToggle = document.getElementById('subs2srs-context-toggle');
if(!subs2srsContextToggle.dataset.shown) {{
    subs2srsContextToggle.insertAdjacentHTML('afterend', {json.dumps(buttons_text)});
    subs2srsContextToggle.dataset.shown = true;
}}
"""
    web.eval(js)


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
    elif subcmd == "show":
        notetype = parts[2]
        marker = parts[3]
        episode_str = parts[4]
        sequence_str = parts[5]
        toggle_context_buttons(context, notetype, marker, episode_str, sequence_str)
    return (True, None)


def play_previous(editor: Editor) -> None:
    context = get_subs2srs_context(editor.note)
    if not context:
        return

    audio = get_subs2srs_audio_filename(
        context.notetype,
        context.marker,
        context.episode_str,
        context.sequence - 1,
        len(context.sequence_str),
    )
    if audio:
        play(audio)


def play_next(editor: Editor) -> None:
    context = get_subs2srs_context(editor.note)
    if not context:
        return
    audio = get_subs2srs_audio_filename(
        context.notetype,
        context.marker,
        context.episode_str,
        context.sequence + 1,
        len(context.sequence_str),
    )
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
