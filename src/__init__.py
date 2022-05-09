import os
from typing import Any, Dict, List, Tuple

from anki.hooks import field_filter
from anki.notes import NoteId
from anki.template import TemplateRenderContext
from aqt import mw
from aqt.editor import Editor
from aqt.gui_hooks import editor_did_init_buttons, webview_did_receive_js_message
from aqt.sound import play
from bs4 import BeautifulSoup

from . import consts
from .subs2srs_context import Subs2srsContext

subs2srs_context = Subs2srsContext()
mw.subs2srs_context = subs2srs_context


def get_bool_filter_option(options: Dict, key: str, default: bool = False) -> bool:
    return (options[key].lower() == "true") if key in options else default


def get_context(field_text: str, nid: NoteId, options: Dict) -> str:
    text = ""
    # Default to fetching audios only
    audio = get_bool_filter_option(options, "audio", True)
    expression = get_bool_filter_option(options, "expression", False)
    if audio and not expression:
        # text += subs2srs_context.get_audio_buttons(nid)
        prev_button_text = subs2srs_context.get_audio_button(nid, "prev", flip=True)
        next_button_text = subs2srs_context.get_audio_button(nid, "next")
        buttons_text = f"<div>{prev_button_text}{next_button_text}</div>"
        text = field_text + buttons_text
    else:
        buttons = subs2srs_context.get_audio_buttons(nid, flip=False)
        expressions = subs2srs_context.get_expressions(nid)
        text += '<div style="display: inline-flex; flex-direction: row;">'
        flex_items = []
        for i in range(len(buttons)):
            expr = expressions[i]
            btn = buttons[i]
            item = ""
            item += "<div>"
            item += f"<span>{expr}</span>"
            item += f"<span>{btn}</span>"
            item += "</div>"
            flex_items.append(item)
        flex_items.insert(len(buttons) // 2, f"<div>{field_text}</div>")
        text += "".join(flex_items)
    return text


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
        for nid_element in nid_elements:
            try:
                nid = int(nid_element.get("data-nid"))
            except:
                pass
            text = get_context(field_text, NoteId(nid), options)
            nid_element.append(BeautifulSoup(text, "html.parser"))
        return str(soup)

    return get_context(field_text, ctx.note().id, options)


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
