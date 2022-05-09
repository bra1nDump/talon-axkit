import itertools
import re
from typing import Dict, List

from talon import Module, Context, actions, app, clip, ui, cron, canvas, screen

'''
Different websites have different accessibility
Example of a shitty one https://realpython.com/iterate-through-dictionary-python/

I suspect that will be hard to select specific parts off a paragraph for example.
A potential solution is to first address the paragraph as a whole 
and then arrange within it.
Also there's a lot of collisions for the same buttons, to disambiguate 
we could actually render something on canvas to specify which number to click.

Would also be called to change a frame of a group (for example a debugging area)
I always have to drag those things which is super annoying.

Useful snippets for debugging in repel:

children = ui.apps(name="Google Chrome")[0].children
button = children.find(role="AXButton")[1]
link = children.find(role="AXLink")[1]
'''

mod = Module()
mod.list("clickable_targets", desc="Descriptions of all clickable targets onscreen, for example a name of a button or a link name")
ctx = Context()

# AXDescription -> ui.Element
description_element_map: Dict[str, ui.Element] = {}
clickables: List[ui.Element] = []

def try_or(func, default=None, expected_exc=(Exception,)):
    try:
        return func()
    except expected_exc:
        return default

def update_clickable_list():
    global description_element_map
    global clickables
    description_element_map = {}
    
    target_app = ui.active_app()
    buttons = target_app.children.find(role="AXButton")
    links = target_app.children.find(role="AXLink")


    clickables = target_app.children.find(visible_only=True)
    # clickables = itertools.chain(buttons, links)

    for clickable in clickables:
        description_element_map[
            try_or(lambda: clickable["AXDescription"], default="")
        ] = clickable

    clickable_targets = actions.user.create_spoken_forms_from_list(
        description_element_map.keys(),
        generate_subsequences=True,
    )

    lists = {
        "self.clickable_targets": clickable_targets,
    }

    # batch update lists
    ctx.lists.update(lists)

def debug_draw_clickable_targets(canvas):
    paint = canvas.paint
    # for description, element in list(description_element_map.items()):
    def predicate(element):
        return not element.children and try_or(lambda: element["AXValue"], "")
    leaf_with_text = filter(predicate, clickables)
    
    for element in leaf_with_text:
        paint.style = 'stroke'
        paint.color = 'green'
        try:
            frame = element['AXFrame']
            canvas.draw_rect(frame)
            paint.style = 'fill'
            paint.color = 'white'
            canvas.draw_text(element['AXValue'], frame.left, frame.bot)
        except:
            continue

# cron.interval('1s', update_clickable_list)

main_canvas = canvas.Canvas.from_screen(screen.main())
main_canvas.allows_capture = False 
main_canvas.register('draw', debug_draw_clickable_targets)

@mod.capture(rule="{self.clickable_targets}")
def clickable_targets(m) -> str:
    "Returns a single application name"
    try:
        return m.clickable_targets
    except AttributeError:
        return m.text

@mod.action_class
class Actions:
    def click(clickable_targets: str):
        '''
        Click one of the visible buttons or links on screen
        based on its description
        '''
        target = description_element_map[clickable_targets]
        target.perform("AXPress")

ctx.lists["user.clickable_targets"] = {}
