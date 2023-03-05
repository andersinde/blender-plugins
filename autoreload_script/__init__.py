bl_info = {
    "name": "Autoreload script",
    "version": (0, 1),
    "blender": (3, 4, 0),
}

import bpy
import sys
import os
import logging
from bpy.props import StringProperty, FloatProperty
from bpy.types import Operator, Panel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(levelname)8s %(name)s %(message)s"
)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


STOPPED = 2
RUNNING = 3

TEMP_FILE = "/tmp/blender/tmp.io"
statemachine = {
    'status': STOPPED,
}

def empty_file_content(fp, temp_path):
    if fp.strip():
        log.debug("Stripping file contents...")
        with open(temp_path, 'w'):
            pass


def check_file(path):
    if not os.path.isfile(path):
        log.debug("Closing file {}".format(path))
        open(path, 'w').close()


def filepath_read_handler():
    """
    this reads the filepath io file, and returns the filepath found.
    """
    log.debug("Reading file " + TEMP_FILE)
    check_file(TEMP_FILE)

    fp = ""
    with open(TEMP_FILE) as f:
        fp = f.read()
        logging.debug('File path: {}'.format(fp))

    empty_file_content(fp, TEMP_FILE)
    return fp.strip()


def execute_file(fp):
    texts = bpy.data.texts
    tf = 'temp_file'
    if tf in texts:
        text = texts[tf]
    else:
        text = texts.new(tf)

    if os.path.splitext(fp)[-1].lower() == ".json":
        print("JSON")
        print(f"cp {fp} /tmp/blender/tmp.json")
        os.system(f"cp {fp} /tmp/blender/tmp.json")
        bpy.ops.object.scad3nodes()
        return

    text.from_string(open(fp).read())
    ctx = bpy.context.copy()
    ctx['edit_text'] = text

    log.debug(text)

    try:
        bpy.ops.text.run_script(ctx)
    except Exception as err:
        log.error('ERROR: {}'.format(str(err)))
        log.debug(sys.exc_info()[-1].tb_frame.f_code)
        log.debug('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))


class BPY_OT_external_editor_client(Operator):

    bl_idname = "wm.bpy_autoreload_script"
    bl_label = "Autoreload external script"

    _timer = None
    speed : FloatProperty()
    mode : StringProperty()

    def process(self):
        fp = filepath_read_handler()
        if fp:
            log.debug('Processing filepath: {}'.format(fp))
            logging.debug('-- action {}'.format(fp))
            execute_file(fp)
        else: 
            log.debug('Processing filepath: not found')


    def modal(self, context, event):
        if statemachine['status'] == STOPPED:
            logging.debug("Closing server...")
            self.cancel(context)
            return {'FINISHED'}

        if not (event.type == 'TIMER'):
            return {'PASS_THROUGH'}

        self.process()
        return {'PASS_THROUGH'}

    def event_dispatcher(self, context, type_op):
        if type_op == 'start':
            log.info("Entering modal operator...")
            statemachine['status'] = RUNNING
            wm = context.window_manager
            #self._timer = wm.event_timer_add(self.speed, context.window)
            self._timer = wm.event_timer_add(self.speed, window=context.window)
            wm.modal_handler_add(self)

        if type_op == 'end':
            logging.info('Exiting modal operator...')
            statemachine['status'] = STOPPED

    def execute(self, context):
        self.event_dispatcher(context, self.mode)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)


class BPY_PT_external_editor_panel(Panel):

    bl_idname = "BPY_PT_ext"
    bl_label = "Autoreload script"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    use_pin = True

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        state = statemachine['status']

        # promising! continue
        tstr = ''
        if state == STOPPED:
            tstr = 'start'
        elif state == RUNNING:
            col.label(text='Listening: \n' + TEMP_FILE)
            tstr = 'end'

        if tstr:
            op = col.operator('wm.bpy_autoreload_script', text=tstr)
            op.mode = tstr
            op.speed = 1


def menu_func(self, context):
    self.layout.operator(BPY_OT_external_editor_client.bl_idname, text=BPY_OT_external_editor_client.bl_label)

def register():
    bpy.utils.register_class(BPY_PT_external_editor_panel)
    bpy.utils.register_class(BPY_OT_external_editor_client)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(BPY_PT_external_editor_panel)
    bpy.utils.unregister_class(BPY_OT_external_editor_client)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == '__main__':
    register()
    bpy.ops.wm.bpy_autoreload_script(speed=1, mode="start")

