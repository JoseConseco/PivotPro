# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


bl_info = {
    "name": "PivotPro",
    "author": "Jose Conseco",
    "version": (1, 0),
    "blender": (2, 75, 0),
    "location": "3D view",
    "description": "Gives ability to snap pivot",
    "warning": "",
    "wiki_url": "https://github.com/JoseConseco/PivotPro",
    "category": "3D View",
    }


import bpy
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_location_3d
import bgl


class PivotProSettings(bpy.types.PropertyGroup):  # seems fucked upp
    activeObject = bpy.props.StringProperty()
    snap_target = bpy.props.StringProperty()
    pivot_point = bpy.props.StringProperty()
bpy.utils.register_class(PivotProSettings)
bpy.types.Scene.PPSettings = bpy.props.CollectionProperty(type=PivotProSettings)


class SelectedObjects():
    storedSelectedObjects = []


def UpdatePivotPro(self, context):  # just when enabling disablig button 'pivotPro'
    if self.pivot_pro_enabled:
        context.scene.PPSettings.add()
        RegisterHotkeys()
    else:
        UnRegisterHotkeys()
        context.scene.PPSettings.remove(0)
        disablePivot(context)


bpy.types.Scene.pivot_pro_enabled = bpy.props.BoolProperty(name="Enable PivotPro", description="Turns on/off pivot", default=False,update=UpdatePivotPro)


def enablePivot(context):  # unhides pivot (or create if dosn't exist)
    try:
        pivot = bpy.data.objects['PivotPro']
    except:
        print('No pivot found! Creating New one')
        createPivot(context)
    try:
        context.scene.objects.link(pivot)
    except:
        pass
    pivot = bpy.data.objects['PivotPro']  # now pivot should be created
    layers = [False]*20
    layers[context.scene.active_layer] = True
    pivot.layers = layers

    pivot.hide_select = False
    pivot.select = True
    context.scene.objects.active = pivot


def disablePivot(context):  # hides pivot but do not deletes it
    pivot = bpy.data.objects['PivotPro']
    pivot.hide_select = True
    pivot.select = False
    try:
        context.scene.objects.unlink(pivot)
    except:
        pass


def createPivot(context):  # just when enabling addon
    newEmpty = bpy.data.objects.new('PivotPro', None)
    context.scene.objects.link(newEmpty)
    layers = [False]*20
    layers[context.scene.active_layer] = True
    newEmpty.layers = layers
    newEmpty.empty_draw_type = "PLAIN_AXES"
    newEmpty.empty_draw_size = 0.01
    bpy.ops.object.select_all(action='DESELECT')
    newEmpty.select = True
    context.scene.objects.active = newEmpty


def setSnapping(context):
    TempStorage = context.scene.PPSettings[0]
    TempStorage.snap_target = context.scene.tool_settings.snap_target
    TempStorage.pivot_point = context.space_data.pivot_point
    TempStorage.activeObject = context.scene.objects.active.name
    context.scene.tool_settings.snap_target = 'ACTIVE'
    context.space_data.pivot_point = 'CURSOR'
    context.scene.cursor_location = bpy.data.objects['PivotPro'].location


def resetSnapping(context):
    TempStorage = context.scene.PPSettings[0]
    context.scene.tool_settings.snap_target = TempStorage.snap_target
    context.space_data.pivot_point = TempStorage.pivot_point
    context.scene.objects.active = bpy.data.objects[TempStorage.activeObject]
    context.scene.cursor_location = bpy.data.objects['PivotPro'].location


class PivotMacro(bpy.types.Macro):
    """Overall macro declaration - knife then delete"""
    bl_idname = "object.pivot_macro"
    bl_label = "Pivot Macro"
    bl_options = {'REGISTER', "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'


class PivotInit(bpy.types.Operator):  # sets pivot location after double click (create pivot if first run)
    """Move an object with the mouse, example"""
    bl_idname = "object.pivot_init"
    bl_label = "Ini Pivot"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        if context.mode == 'OBJECT':

            coord = event.mouse_region_x, event.mouse_region_y
            region = context.region
            rv3d = context.space_data.region_3d
            vec = region_2d_to_vector_3d(region, rv3d, coord)
            loc = region_2d_to_location_3d(region, rv3d, coord, vec)

            SelectedObjects.storedSelectedObjects = [obj for obj in context.visible_objects if obj.select]
            for obj in SelectedObjects.storedSelectedObjects:
                obj.select = False

            oldPivot = bpy.data.objects.get('PivotPro', None)
            context.scene.tool_settings.use_snap = True
            if oldPivot is not None:
                enablePivot(context)
                oldPivot.location = loc
            else:
                createPivot(context)
                pivot = bpy.data.objects.get('PivotPro', None)  # it exist now after CreatePivot
                pivot.location = loc  # so put pivot under cursor
        return {'FINISHED'}


class PivotHide(bpy.types.Operator):
    bl_idname = "object.pivot_hide"
    bl_label = "Hide Pivot"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        context.scene.tool_settings.use_snap = False
        if context.mode == 'OBJECT':
            for obj in SelectedObjects.storedSelectedObjects:
                obj.select = True
            SelectedObjects.storedSelectedObjects.clear()
            context.scene.cursor_location = bpy.data.objects['PivotPro'].location
            disablePivot(context)
        return {'FINISHED'}


class PivotTransform(bpy.types.Operator):
    """Enable Fast Transform"""
    bl_idname = "object.pivot_transform"
    bl_label = "Pivot Transform"

    operator = bpy.props.StringProperty("")

    count = 0

    def modal(self, context, event):
        self.count += 1

        if self.count == 1:
            if self.operator == "Translate":
                bpy.ops.transform.translate('INVOKE_DEFAULT')
            if self.operator == "Rotate":
                bpy.ops.transform.rotate('INVOKE_DEFAULT')
            if self.operator == "Scale":
                bpy.ops.transform.resize('INVOKE_DEFAULT')

        if event.type in {'X', 'Y', 'Z'}:
            return {'PASS_THROUGH'}

        if event.type in {'RIGHTMOUSE', 'ESC', 'LEFTMOUSE'}:
            disablePivot(context)
            resetSnapping(context)
            return {'FINISHED'}

        return {'PASS_THROUGH'}  # was running modal

    def invoke(self, context, event):
        if bpy.context.scene.pivot_pro_enabled:
            enablePivot(context)
            setSnapping(context)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}  # was CANCELL but broke edit mesh G, R, S


def drawPivotRed():
    if bpy.context.scene.pivot_pro_enabled:
        oldPivot = bpy.data.objects.get('PivotPro', None)
        if oldPivot is not None:

            bgl.glEnable(bgl.GL_BLEND)

            bgl.glColor3f(1, 0, 0)
            bgl.glPointSize(10)
            bgl.glBegin(bgl.GL_POINTS)
            bgl.glVertex3f(*oldPivot.location)
            bgl.glEnd()
            bgl.glDisable(bgl.GL_BLEND)

            # restore  defaults
            bgl.glPointSize(1)
            bgl.glDisable(bgl.GL_BLEND)
            bgl.glColor3f(0.0, 0.0, 0.0)


def addon_button(self, context):
    layout = self.layout
    if bpy.context.scene.pivot_pro_enabled:
        layout.prop(context.scene, "pivot_pro_enabled", text='PivotPro', icon='OUTLINER_OB_EMPTY')
    else:
        layout.prop(context.scene, "pivot_pro_enabled", text='PivotPro', icon='OUTLINER_OB_EMPTY')


addon_keymaps = []  # put on out of register()
handleDrawPivot = []


def RegisterHotkeys():
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = km.keymap_items.new(PivotMacro.bl_idname, 'LEFTMOUSE', 'DOUBLE_CLICK')
    #kmi.properties.my_prop = 'some'
    addon_keymaps.append((km, kmi))

    kmi = km.keymap_items.new(PivotTransform.bl_idname, 'G', 'PRESS', shift=True)
    kmi.properties.operator = "Translate"
    addon_keymaps.append((km, kmi))

    kmi = km.keymap_items.new(PivotTransform.bl_idname, 'R', 'PRESS', shift=True)
    kmi.properties.operator = "Rotate"
    addon_keymaps.append((km, kmi))

    kmi = km.keymap_items.new(PivotTransform.bl_idname, 'S', 'PRESS', shift=True)
    kmi.properties.operator = "Scale"
    addon_keymaps.append((km, kmi))


def UnRegisterHotkeys():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


def register():
    bpy.utils.register_module(__name__)
    PivotMacro.define("OBJECT_OT_pivot_init")
    PivotMacro.define("TRANSFORM_OT_translate")
    PivotMacro.define("OBJECT_OT_pivot_hide")

    if handleDrawPivot:
        bpy.types.SpaceView3D.draw_handler_remove(handleDrawPivot[0], 'WINDOW')
    handleDrawPivot[:] = [bpy.types.SpaceView3D.draw_handler_add(drawPivotRed, (), 'WINDOW', 'POST_VIEW')]

    bpy.types.VIEW3D_HT_header.append(addon_button)

    try:
        if bpy.context.scene.pivot_pro_enabled:
            RegisterHotkeys()
        else:
            UnRegisterHotkeys()
    except:
        pass
        #RegisterHotkeys() #if there is no property  pivot_pro_enabled means we run it first time. By default is is disabled


def unregister():
    bpy.utils.unregister_module(__name__)

    if handleDrawPivot:
        bpy.types.SpaceView3D.draw_handler_remove(handleDrawPivot[0], 'WINDOW')
        handleDrawPivot[:] = []

    bpy.types.VIEW3D_HT_header.remove(addon_button)

    bpy.utils.unregister_class(PivotProSettings)
    UnRegisterHotkeys()


if __name__ == "__main__":
    register()
