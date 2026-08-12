
# Cartoon Eye Rig - UI
# Ade David (adedavid3d)
# Shows up in: 3D Viewport > N-panel > Item tab

import bpy

TOGGLES = [
    ("Main Controls",    "Main_Controls"),
    ("Secondary",        "Sec_Controls"),
    ("Squash & Stretch", "Squash_Stretch"),
    ("Root",             "Root"),
]


class EYERIG_PT_item(bpy.types.Panel):
    bl_label = "Eye Rig"
    bl_idname = "EYERIG_PT_item"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob is not None and ob.type == 'ARMATURE' and "mst_ctrl_eye" in ob.data.bones

    def draw(self, context):
        ob = context.object
        layout = self.layout

        col = layout.column(align=True)
        for label, name in TOGGLES:
            coll = ob.data.collections.get(name)
            if coll is not None:
                col.prop(coll, "is_visible", text=label, toggle=True)

        pb = ob.pose.bones.get("mst_ctrl_eye")
        if pb is not None and "eye-follow" in pb:
            layout.prop(pb, '["eye-follow"]', text="Eye Follow", slider=True)


def register():
    try: bpy.utils.unregister_class(EYERIG_PT_item)
    except Exception: pass
    bpy.utils.register_class(EYERIG_PT_item)


def unregister():
    try: bpy.utils.unregister_class(EYERIG_PT_item)
    except Exception: pass


register()
