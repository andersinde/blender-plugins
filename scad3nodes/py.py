#! blender --python

import re
import sys
import bpy
import sys
import math
import mathutils
from util import *


# start with a clean scene
#
bpy.context.preferences.view.show_splash = False
for obj in bpy.data.objects:
    bpy.data.objects.remove(obj, do_unlink=True)


# set 3d view clipping to something reasonable
#
for a in bpy.context.screen.areas:
    if a.type == 'VIEW_3D':
        for s in a.spaces:
            if s.type == 'VIEW_3D':
                s.clip_end = 100000
                s.clip_start = 0.01


# create a plane, select it, add geometry node modifier
#
bpy.ops.mesh.primitive_plane_add()
bpy.ops.object.select_all(action='SELECT')
obj = bpy.context.active_object
mod = obj.modifiers.new("GeometryNodes", 'NODES')


# create new geometry node group with no input node and one output node
#
group = bpy.data.node_groups.new("Geometry Nodes", 'GeometryNodeTree')
group.outputs.new('NodeSocketGeometry', "Geometry")
output_node = group.nodes.new('NodeGroupOutput')
output_node.is_active_output = True
output_node.select = False
mod.node_group = group


# create or get a simple mat for the 'color' OpenSCAD operator
#
colorMaterials = {}

filename = "dod.json"
output = load_nodes_from_file(group, filename)
group.links.new(output_node.inputs[0], getGeomOutput(output))


# frame selection in all views
#
for a in bpy.context.screen.areas:
    if a.type == 'VIEW_3D':
        ctx = bpy.context.copy()
        ctx['area'] = a
        ctx['region'] = a.regions[-1]
        bpy.ops.view3d.view_selected(ctx)
