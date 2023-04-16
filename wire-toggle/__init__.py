import bpy

bl_info = {
    "name": "Toggle wireframe display",
    "version": (0, 1),
    "blender": (3, 5, 0),
}


class WireToggleOperator(bpy.types.Operator):
    bl_idname = "object.wire_toggle"
    bl_label = "Toggle wireframe display"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        if bpy.context.object.display_type == 'SOLID':
            bpy.context.object.display_type = 'WIRE'
        elif bpy.context.object.display_type == 'WIRE':
            bpy.context.object.display_type = 'SOLID'
        return {'FINISHED'}

def register():
    bpy.utils.register_class(WireToggleOperator)

def unregister():
    bpy.utils.unregister_class(WireToggleOperator)

if __name__ == "__main__":
    register()

