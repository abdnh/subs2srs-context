import os
from typing import Any, List, Tuple

from anki.hooks import field_filter
from anki.notes import NoteId
from anki.template import TemplateRenderContext
from aqt.editor import Editor
from aqt.gui_hooks import editor_did_init_buttons, webview_did_receive_js_message
from aqt.sound import play
from bs4 import BeautifulSoup

from . import consts
from .subs2srs_context import Subs2srsContext

subs2srs_context = Subs2srsContext()


def add_filter(
    field_text: str, field_name: str, filter_name: str, ctx: TemplateRenderContext
) -> str:
    if not filter_name.startswith(consts.FILTER_NAME):
        return field_text
    options = {}
    for key, value in (pair.split("=") for pair in filter_name.split()[1:]):
        options[key] = value
    # FIXME: doesn't support selectors with spaces or "="
    nid_selector = options.get("nid_selector", "")
    if nid_selector:
        soup = BeautifulSoup(field_text, "html.parser")
        nid_elements = soup.select(nid_selector)
        if not nid_elements:
            return field_text
        if nid_elements:
            for nid_element in nid_elements:
                try:
                    nid = int(nid_element.get("data-nid"))
                except:
                    pass
                buttons_text = subs2srs_context.get_audio_buttons(NoteId(nid))
                nid_element.append(BeautifulSoup(buttons_text, "html.parser"))
        return str(soup)
    else:
        buttons_text = subs2srs_context.get_audio_buttons(ctx.note().id)
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
    audio = subs2srs_context.get_audio_filename(NoteId(editor.note.id - 1))
    if audio:
        play(audio)


def play_next(editor: Editor) -> None:
    audio = subs2srs_context.get_audio_filename(NoteId(editor.note.id + 1))
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
