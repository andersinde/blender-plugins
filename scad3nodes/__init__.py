bl_info = {
    "name": "scad3nodes",
    "version": (0, 1),
    "blender": (3, 4, 0),
}

import bpy
import re
import os
import sys
import math
import mathutils
import sys
import importlib
import time

def make_polygon(vertices):
    vertices = [[float(v[0]), float(v[1]), 0.0] for v in vertices]

    mesh = bpy.data.meshes.new("scad_poly")
    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("Collection")
    col.objects.link(obj)

    saved = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = obj

    edges = []
    faces = [list(range(0, len(vertices)))]
    mesh.from_pydata(vertices, edges, faces)
    bpy.context.view_layer.objects.active = saved

    obj.hide_viewport = True
    obj.hide_render = True
    obj.hide_set(True)
    return obj

def make_polyhedron(vertices, faces):
    vertices = [[float(v[0]), float(v[1]), float(v[2])] for v in vertices]
    faces = [[int(i) for i in f] for f in faces]

    mesh = bpy.data.meshes.new("scad_polyhedron")
    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("Collection")
    col.objects.link(obj)

    saved = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = obj

    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    bpy.context.view_layer.objects.active = saved

    obj.hide_viewport = True
    obj.hide_render = True
    obj.hide_set(True)
    return obj

# search for a node by type in a tree
def get_node_index(nodes, datatype):
    idx = 0
    for m in nodes:
        if (m.type == datatype):
            return idx
        idx += 1
    return 1  # by default

def getColorMat(rgba, colorMaterials = {}):
    name = str(rgba)
    # name = re.sub(r'\s', '_', name)
    # name = re.sub(r'\.', 'D', name)
    name = re.sub(r'^', 'col_', name)


    if name in colorMaterials:
        return colorMaterials[name]

    mat = colorMaterials[name] = bpy.data.materials.new(name)

    rgba = [float(x) for x in rgba]
    mat.diffuse_color = rgba
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    node = nodes.new('ShaderNodeBsdfDiffuse')
    node.name = f'Auto-generated diffuse bsdf for color {name}'
    node.inputs[0].default_value = rgba
    out = node.outputs[0]
    inn = nodes[get_node_index(nodes, 'OUTPUT_MATERIAL')].inputs[0]
    mat.node_tree.links.new(out, inn)
    return mat

# quick and dirty arg parsing for OpenSCAD operators
# --------------------------------------------------
def parseArgs(args):
    args = re.sub(r'\$', '_ss_', args)
    args = re.sub(r'undef', 'None', args)
    code = f'''
def evalArgs(local_dict, *args, **kwargs):
  i = 0
  for arg in args:
    local_dict['arg_%d' % i] = arg
    i += 1
  local_dict.update(kwargs)

true = True
false = False
evalArgs(locals(), {args})
'''
    result = {}
    exec(code, None, result)
    return result

def getGeomOutput(node):
    for output in node.outputs:
        if 'GEOMETRY' == output.type:
            return output
    raise Exception('node has no geometry output')


# convert a SCAD operator to Blender geometry node
def Node(name, args, group, inputNodes, code_line):
    node = None
    args = parseArgs(args)

    if name == 'sphere':
        fn = int(args['_ss_fn'])
        if fn == 0: 
            fn = 24
        radius = float(args['r'])
        sphere = group.nodes.new('GeometryNodeMeshUVSphere')
        sphere.inputs['Radius'].default_value = radius
        sphere.inputs['Segments'].default_value = fn
        sphere.inputs['Rings'].default_value = fn
        node = sphere

    elif name == 'cube':
        center = args['center']
        size = [float(x) for x in args['size']]
        cube = group.nodes.new('GeometryNodeMeshCube')
        cube.inputs['Size'].default_value = size
        node = cube

        if center is False:
            offset = [x / 2.0 for x in size]
            transform = group.nodes.new('GeometryNodeTransform')
            transform.inputs['Translation'].default_value = offset
            group.links.new(transform.inputs[0], getGeomOutput(cube))
            node = transform

    elif name == 'cylinder':
        h = float(args['h'])
        r1 = float(args['r1'])
        r2 = float(args['r2'])
        center = args['center']
        fn = int(args['_ss_fn'])
        if fn == 0: 
            fn = 24
        cylinder = group.nodes.new('GeometryNodeMeshCone')
        cylinder.inputs['Depth'].default_value = h
        cylinder.inputs['Radius Top'].default_value = r1
        cylinder.inputs['Radius Bottom'].default_value = r2
        cylinder.inputs['Vertices'].default_value = fn
        node = cylinder

        if center is True:
            offset = [0.0, 0.0, -h / 2.0]
            transform = group.nodes.new('GeometryNodeTransform')
            transform.inputs['Translation'].default_value = offset
            group.links.new(transform.inputs[0], getGeomOutput(cylinder))
            node = transform

    elif name == 'multmatrix':
        # https://docs.blender.org/api/current/mathutils.html#mathutils.Matrix
        m = args['arg_0']
        bm = mathutils.Matrix()
        for i in range(0, 4):
            for j in range(0, 4):
                bm[i][j] = m[i][j]
        t, q, s = bm.decompose()
        r = q.to_euler()

        transform = group.nodes.new('GeometryNodeTransform')
        transform.inputs['Translation'].default_value = t
        transform.inputs['Rotation'].default_value = r
        transform.inputs['Scale'].default_value = s
        if 0 < len(inputNodes):
            group.links.new(transform.inputs[0], getGeomOutput(inputNodes[0]))
        node = transform

    elif name == 'color':
        color = group.nodes.new('GeometryNodeSetMaterial')
        print("anders material:", args['arg_0'])
        # color.inputs['Material'].default_value = getColorMat(args['arg_0'])
        if 0 < len(inputNodes):
            group.links.new(color.inputs[0], getGeomOutput(inputNodes[0]))
        node = color

    elif name == 'difference':
        difference = group.nodes.new('GeometryNodeMeshBoolean')
        if len(inputNodes) > 0:
            group.links.new(difference.inputs[0], getGeomOutput(inputNodes[0]))
        for inputNode in inputNodes[1:]:
            group.links.new(difference.inputs[1], getGeomOutput(inputNode))
        node = difference

    elif name == 'union':
        union = group.nodes.new('GeometryNodeMeshBoolean')
        union.operation = 'UNION'
        for inputNode in inputNodes:
            group.links.new(union.inputs[1], getGeomOutput(inputNode))
        node = union

    elif name == 'group':
        join = group.nodes.new('GeometryNodeJoinGeometry')
        for inputNode in inputNodes:
            group.links.new(join.inputs[0], getGeomOutput(inputNode))
            # create_new_object(inputNode(0))
        node = join

    elif name == 'intersection':
        intersection = group.nodes.new('GeometryNodeMeshBoolean')
        intersection.operation = 'INTERSECT'
        for inputNode in inputNodes:
            group.links.new(intersection.inputs[1], getGeomOutput(inputNode))
        node = intersection

    elif name == 'text':
        text = args['text']
        string2Curve = group.nodes.new('GeometryNodeStringToCurves')
        string2Curve.inputs['String'].default_value = text
        node = string2Curve

        if True:
            fillCurve = group.nodes.new('GeometryNodeFillCurve')
            fillCurve.mode = 'NGONS'
            group.links.new(fillCurve.inputs[0], getGeomOutput(string2Curve))
            node = fillCurve

    elif name == 'circle':
        radius = float(args['r'])
        circle = group.nodes.new('GeometryNodeCurvePrimitiveCircle')
        circle.inputs['Radius'].default_value = radius
        node = circle

        if True:
            fillCurve = group.nodes.new('GeometryNodeFillCurve')
            fillCurve.mode = 'NGONS'
            group.links.new(fillCurve.inputs[0], getGeomOutput(circle))
            node = fillCurve

    elif name == 'square':
        size = args['size']
        center = args['center']
        square = group.nodes.new('GeometryNodeCurvePrimitiveQuadrilateral')
        square.inputs['Width'].default_value = float(size[0])
        square.inputs['Height'].default_value = float(size[1])
        node = square

        if True:
            fillCurve = group.nodes.new('GeometryNodeFillCurve')
            fillCurve.mode = 'NGONS'
            group.links.new(fillCurve.inputs[0], getGeomOutput(square))
            node = fillCurve

    elif name == 'polygon':
        points = args['points']
        poly_obj = make_polygon(points)
        poly_node = group.nodes.new('GeometryNodeObjectInfo')
        poly_node.inputs[0].default_value = poly_obj
        node = poly_node

    elif name == 'polyhedron':
        faces = args['faces']
        points = args['points']
        poly_obj = make_polyhedron(points, faces)
        poly_node = group.nodes.new('GeometryNodeObjectInfo')
        poly_node.inputs[0].default_value = poly_obj
        node = poly_node

    elif name == 'linear_extrude':
        height = float(args['height'])
        extrudeMesh = group.nodes.new('GeometryNodeExtrudeMesh')
        extrudeMesh.inputs['Individual'].default_value = True
        extrudeMesh.inputs['Offset Scale'].default_value = height
        if 0 < len(inputNodes):
            group.links.new(extrudeMesh.inputs[0], getGeomOutput(inputNodes[0]))

        union = group.nodes.new('GeometryNodeMeshBoolean')
        union.operation = 'UNION'
        if 0 < len(inputNodes):
            group.links.new(union.inputs[1], getGeomOutput(inputNodes[0]))
        group.links.new(union.inputs[1], getGeomOutput(extrudeMesh))

        transform = group.nodes.new('GeometryNodeTransform')
        transform.inputs['Translation'].default_value = [0, 0, height / 2];
        group.links.new(transform.inputs[0], getGeomOutput(union))
        node = transform

    elif name == 'hull':
        hull = group.nodes.new('GeometryNodeConvexHull') #GeometryNodeJoinGeometry
        if 1<len(inputNodes):
            union = group.nodes.new('GeometryNodeMeshBoolean')
            union.operation = 'UNION'
            for inputNode in inputNodes:
                group.links.new(union.inputs[1], getGeomOutput(inputNode))
            group.links.new(hull.inputs[0], getGeomOutput(union))
        elif 0<len(inputNodes):
            group.links.new(hull.inputs[0], getGeomOutput(inputNodes[0]))
        node = hull

    elif name == 'minkowski':
        print(f'unimplemented operator {name}, replace with hull')
        mink = group.nodes.new('GeometryNodeConvexHull')
        if 1 < len(mink.inputs):
            union = group.nodes.new('GeometryNodeMeshBoolean')
            union.operation = 'UNION'
            for inputNode in inputNodes:
                group.links.new(union.inputs[1], getGeomOutput(inputNode))
            group.links.new(mink.inputs[0], getGeomOutput(union))
        else:
            if 0 < len(inputNodes):
                group.links.new(mink.inputs[0], getGeomOutput(inputNodes[0]))
        node = mink

    else:
        print(f'unknown operator {name}, replace with cube')
        node = group.nodes.new('GeometryNodeMeshCube')
        node.inputs['Size'].default_value = [1, 1, 1]

    return node


def main(context):
    print("\n  ------------ running scad3nodes\n")
    start_timer = time.time()

    create_new_object = False # bpy.context.scene.scad_create_new_object
    scad_object = bpy.context.active_object

    my_props = bpy.context.scene.my_props

    if my_props.scad_create_new_object:
        # create new object geometry node modifier to object
        mesh = bpy.data.meshes.new("SCAD mesh")
        scad_object = bpy.data.objects.new("SCAD object", mesh)

        # add object to SCAD collection
        scad_collection = bpy.data.collections.get("SCAD")
        if scad_collection is None:
            scad_collection = bpy.data.collections.new("SCAD")
            bpy.context.scene.collection.children.link(scad_collection)
        scad_collection.color_tag = "COLOR_03"
        scad_collection.objects.link(scad_object)

        bpy.context.view_layer.objects.active = bpy.data.objects['SCAD object']

    # create new geometry node group with no input node and one output node
    group = bpy.data.node_groups.new("Geometry Nodes", 'GeometryNodeTree')
    group.outputs.new('NodeSocketGeometry', "Geometry")
    output_node = group.nodes.new('NodeGroupOutput')
    output_node.is_active_output = True
    output_node.select = False

    # add modifier to object
    mod = scad_object.modifiers.new("GeometryNodes", 'NODES')
    mod.node_group = group

    # load scad render output from /tmp/nodes.py and link to output node
    sys.path.append("/tmp")
    import nodes
    importlib.reload(nodes)
    from nodes import get_output_node

    output = get_output_node(group, Node)
    group.links.new(output_node.inputs[0], getGeomOutput(output))

    # TODO: user setting
    if False:
        mod.apply(modifier="GeometryNodes", report=True)
        scad_object.modifier_apply(modifier="GeometryNodes", report=True)
        scad_object.shade_smooth(use_auto_smooth=True)


    end_timer = time.time()
    print("\ntimer:",  end_timer - start_timer, "\n ------------\n")


class Scad3NodesOperator(bpy.types.Operator):
    """Converts py (parsed .csg file) to geomtery node modifier"""
    bl_idname = "object.scad3nodes"
    bl_label = "scad3nodes"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        main(context)
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(Scad3NodesOperator.bl_idname, text=Scad3NodesOperator.bl_label)

def register():
    bpy.utils.register_class(Scad3NodesOperator)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(Scad3NodesOperator)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()
