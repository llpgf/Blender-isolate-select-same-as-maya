bl_info = {
    "name": "Maya-style Isolate Select (Local & Global)",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D",
    "description": "Provides both local and global isolation features with separate hotkeys",
    "category": "3D View",
}

import bpy
import bmesh
from bpy.types import Operator, AddonPreferences, Panel
from bpy.props import BoolProperty, EnumProperty

# Global state tracking dictionaries
isolate_states = {
    # Local isolation states
    'LOCAL': {
        'OBJECT': {'active': False, 'hidden_objects': [], 'selected_objects': []},
        'EDIT_MESH': {'active': False, 'selected_faces': [], 'selected_edges': [], 'selected_verts': []},
        'POSE': {'active': False, 'selected_bones': []},
        'EDIT_ARMATURE': {'active': False, 'selected_bones': []}
    },
    # Global isolation states
    'GLOBAL': {
        'OBJECT': {'active': False, 'hidden_objects': [], 'selected_objects': []},
        'EDIT_MESH': {'active': False, 'selected_faces': [], 'selected_edges': [], 
                      'selected_verts': [], 'hidden_objects': []},
        'POSE': {'active': False, 'selected_bones': [], 'hidden_objects': []},
        'EDIT_ARMATURE': {'active': False, 'selected_bones': [], 'hidden_objects': []}
    }
}

#----------------------------------------------------------------------------------
# LOCAL ISOLATION OPERATOR
#----------------------------------------------------------------------------------
class VIEW3D_OT_local_isolate(Operator):
    """Toggle isolation of selected elements within the current object"""
    bl_idname = "view3d.local_isolate"
    bl_label = "Local Isolate Select"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        # Check if feature is enabled in preferences
        try:
            prefs = context.preferences.addons[__name__].preferences
            return context.area.type == 'VIEW_3D' and prefs.enable_local_isolate
        except:
            return context.area.type == 'VIEW_3D'
    
    def execute(self, context):
        mode = context.mode
        
        # OBJECT MODE
        if mode == 'OBJECT':
            state = isolate_states['LOCAL']['OBJECT']
            
            if not state['active']:
                # Get selected objects
                selected = [obj for obj in context.selected_objects]
                if not selected:
                    self.report({'WARNING'}, "No objects selected")
                    return {'CANCELLED'}
                
                # Store selected objects (for later restoration)
                state['selected_objects'] = selected.copy()
                
                # Store and hide unselected objects
                hidden = []
                for obj in context.view_layer.objects:
                    if obj not in selected and not obj.hide_viewport:
                        hidden.append(obj)
                        obj.hide_viewport = True
                
                state['hidden_objects'] = hidden
                state['active'] = True
                self.report({'INFO'}, "Local isolate mode enabled (Object Mode)")
            
            else:
                # Remember current selection before revealing
                last_selected = [obj for obj in context.selected_objects]
                
                # Clear selection
                bpy.ops.object.select_all(action='DESELECT')
                
                # Restore hidden objects
                for obj in state['hidden_objects']:
                    obj.hide_viewport = False
                
                # Restore original selection
                for obj in state['selected_objects']:
                    if obj and obj.name in bpy.data.objects:
                        obj.select_set(True)
                
                # Set active object if possible
                if state['selected_objects'] and state['selected_objects'][0]:
                    context.view_layer.objects.active = state['selected_objects'][0]
                
                state['hidden_objects'] = []
                state['active'] = False
                self.report({'INFO'}, "Local isolate mode disabled (Object Mode)")
        
        # EDIT MESH MODE
        elif mode == 'EDIT_MESH':
            state = isolate_states['LOCAL']['EDIT_MESH']
            obj = context.edit_object
            mesh = obj.data
            
            if not state['active']:
                # Get the BMesh to access selection data
                bm = bmesh.from_edit_mesh(mesh)
                
                # Store indices of selected elements based on current selection mode
                state['selected_verts'] = [v.index for v in bm.verts if v.select]
                state['selected_edges'] = [e.index for e in bm.edges if e.select]
                state['selected_faces'] = [f.index for f in bm.faces if f.select]
                
                # Hide unselected elements in current edit mesh
                bpy.ops.mesh.hide(unselected=True)
                state['active'] = True
                self.report({'INFO'}, "Local isolate mode enabled (Edit Mode)")
            
            else:
                # Reveal all hidden elements in current mesh
                bpy.ops.mesh.reveal()
                
                # First deselect everything
                bpy.ops.mesh.select_all(action='DESELECT')
                
                # Get the BMesh to restore selection
                bm = bmesh.from_edit_mesh(mesh)
                
                # Restore selection based on component indices
                # For vertices
                if state['selected_verts']:
                    for index in state['selected_verts']:
                        if index < len(bm.verts):
                            bm.verts[index].select = True
                
                # For edges
                if state['selected_edges']:
                    for index in state['selected_edges']:
                        if index < len(bm.edges):
                            bm.edges[index].select = True
                
                # For faces
                if state['selected_faces']:
                    for index in state['selected_faces']:
                        if index < len(bm.faces):
                            bm.faces[index].select = True
                
                # Update the edit mesh
                bmesh.update_edit_mesh(mesh)
                
                state['active'] = False
                self.report({'INFO'}, "Local isolate mode disabled (Edit Mode)")
        
        # POSE MODE
        elif mode == 'POSE':
            state = isolate_states['LOCAL']['POSE']
            armature = context.object
            
            if not state['active']:
                # Store selected bone names
                selected_bones = [bone.name for bone in armature.data.bones if bone.select]
                if not selected_bones:
                    self.report({'WARNING'}, "No bones selected")
                    return {'CANCELLED'}
                
                state['selected_bones'] = selected_bones
                
                # Hide unselected bones
                for bone in armature.data.bones:
                    if bone.name not in selected_bones:
                        bone.hide = True
                
                state['active'] = True
                self.report({'INFO'}, "Local isolate mode enabled (Pose Mode)")
            
            else:
                # Unhide all bones
                for bone in armature.data.bones:
                    bone.hide = False
                
                # Restore original bone selection
                bpy.ops.pose.select_all(action='DESELECT')
                for bone_name in state['selected_bones']:
                    if bone_name in armature.data.bones:
                        armature.data.bones[bone_name].select = True
                
                state['active'] = False
                self.report({'INFO'}, "Local isolate mode disabled (Pose Mode)")
        
        # EDIT ARMATURE MODE
        elif mode == 'EDIT_ARMATURE':
            state = isolate_states['LOCAL']['EDIT_ARMATURE']
            armature = context.object
            
            if not state['active']:
                # Store selected bone names
                selected_bones = [bone.name for bone in armature.data.edit_bones if bone.select]
                if not selected_bones:
                    self.report({'WARNING'}, "No bones selected")
                    return {'CANCELLED'}
                
                state['selected_bones'] = selected_bones
                
                # Hide unselected bones
                for bone in armature.data.edit_bones:
                    if bone.name not in selected_bones:
                        bone.hide = True
                
                state['active'] = True
                self.report({'INFO'}, "Local isolate mode enabled (Armature Edit Mode)")
            
            else:
                # Unhide all bones
                for bone in armature.data.edit_bones:
                    bone.hide = False
                
                # Restore original bone selection
                bpy.ops.armature.select_all(action='DESELECT')
                for bone_name in state['selected_bones']:
                    if bone_name in armature.data.edit_bones:
                        armature.data.edit_bones[bone_name].select = True
                        armature.data.edit_bones[bone_name].select_head = True
                        armature.data.edit_bones[bone_name].select_tail = True
                
                state['active'] = False
                self.report({'INFO'}, "Local isolate mode disabled (Armature Edit Mode)")
        
        else:
            self.report({'WARNING'}, f"Local isolate not supported in {mode} mode")
            return {'CANCELLED'}
        
        # Force viewport update
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

#----------------------------------------------------------------------------------
# GLOBAL ISOLATION OPERATOR
#----------------------------------------------------------------------------------
class VIEW3D_OT_global_isolate(Operator):
    """Toggle isolation of selected elements and hide everything else in the scene"""
    bl_idname = "view3d.global_isolate"
    bl_label = "Global Isolate Select"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        # Check if feature is enabled in preferences
        try:
            prefs = context.preferences.addons[__name__].preferences
            return context.area.type == 'VIEW_3D' and prefs.enable_global_isolate
        except:
            return context.area.type == 'VIEW_3D'
    
    def execute(self, context):
        mode = context.mode
        
        # OBJECT MODE
        if mode == 'OBJECT':
            state = isolate_states['GLOBAL']['OBJECT']
            
            if not state['active']:
                # Get selected objects
                selected = [obj for obj in context.selected_objects]
                if not selected:
                    self.report({'WARNING'}, "No objects selected")
                    return {'CANCELLED'}
                
                # Store selected objects (for later restoration)
                state['selected_objects'] = selected.copy()
                
                # Store and hide unselected objects
                hidden = []
                for obj in context.view_layer.objects:
                    if obj not in selected and not obj.hide_viewport:
                        hidden.append(obj)
                        obj.hide_viewport = True
                
                state['hidden_objects'] = hidden
                state['active'] = True
                self.report({'INFO'}, "Global isolate mode enabled (Object Mode)")
            
            else:
                # Remember current selection before revealing
                last_selected = [obj for obj in context.selected_objects]
                
                # Clear selection
                bpy.ops.object.select_all(action='DESELECT')
                
                # Restore hidden objects
                for obj in state['hidden_objects']:
                    obj.hide_viewport = False
                
                # Restore original selection
                for obj in state['selected_objects']:
                    if obj and obj.name in bpy.data.objects:
                        obj.select_set(True)
                
                # Set active object if possible
                if state['selected_objects'] and state['selected_objects'][0]:
                    context.view_layer.objects.active = state['selected_objects'][0]
                
                state['hidden_objects'] = []
                state['active'] = False
                self.report({'INFO'}, "Global isolate mode disabled (Object Mode)")
        
        # EDIT MESH MODE
        elif mode == 'EDIT_MESH':
            state = isolate_states['GLOBAL']['EDIT_MESH']
            obj = context.edit_object
            mesh = obj.data
            
            if not state['active']:
                # Get the BMesh to access selection data
                bm = bmesh.from_edit_mesh(mesh)
                
                # Store indices of selected elements based on current selection mode
                state['selected_verts'] = [v.index for v in bm.verts if v.select]
                state['selected_edges'] = [e.index for e in bm.edges if e.select]
                state['selected_faces'] = [f.index for f in bm.faces if f.select]
                
                # Hide unselected elements in current edit mesh
                bpy.ops.mesh.hide(unselected=True)
                
                # Also hide all other objects in the scene (global isolation)
                hidden = []
                for scene_obj in context.view_layer.objects:
                    if scene_obj != obj and not scene_obj.hide_viewport:
                        hidden.append(scene_obj)
                        scene_obj.hide_viewport = True
                
                state['hidden_objects'] = hidden
                state['active'] = True
                self.report({'INFO'}, "Global isolate mode enabled (Edit Mode)")
            
            else:
                # Reveal all hidden elements in current mesh
                bpy.ops.mesh.reveal()
                
                # First deselect everything
                bpy.ops.mesh.select_all(action='DESELECT')
                
                # Get the BMesh to restore selection
                bm = bmesh.from_edit_mesh(mesh)
                
                # Restore selection based on component indices
                # For vertices
                if state['selected_verts']:
                    for index in state['selected_verts']:
                        if index < len(bm.verts):
                            bm.verts[index].select = True
                
                # For edges
                if state['selected_edges']:
                    for index in state['selected_edges']:
                        if index < len(bm.edges):
                            bm.edges[index].select = True
                
                # For faces
                if state['selected_faces']:
                    for index in state['selected_faces']:
                        if index < len(bm.faces):
                            bm.faces[index].select = True
                
                # Update the edit mesh
                bmesh.update_edit_mesh(mesh)
                
                # Also restore all other objects in the scene
                for scene_obj in state['hidden_objects']:
                    scene_obj.hide_viewport = False
                
                state['hidden_objects'] = []
                state['active'] = False
                self.report({'INFO'}, "Global isolate mode disabled (Edit Mode)")
        
        # POSE MODE
        elif mode == 'POSE':
            state = isolate_states['GLOBAL']['POSE']
            armature = context.object
            
            if not state['active']:
                # Store selected bone names
                selected_bones = [bone.name for bone in armature.data.bones if bone.select]
                if not selected_bones:
                    self.report({'WARNING'}, "No bones selected")
                    return {'CANCELLED'}
                
                state['selected_bones'] = selected_bones
                
                # Hide unselected bones
                for bone in armature.data.bones:
                    if bone.name not in selected_bones:
                        bone.hide = True
                
                # Also hide all other objects in the scene (global isolation)
                hidden = []
                for scene_obj in context.view_layer.objects:
                    if scene_obj != armature and not scene_obj.hide_viewport:
                        hidden.append(scene_obj)
                        scene_obj.hide_viewport = True
                
                state['hidden_objects'] = hidden
                state['active'] = True
                self.report({'INFO'}, "Global isolate mode enabled (Pose Mode)")
            
            else:
                # Unhide all bones
                for bone in armature.data.bones:
                    bone.hide = False
                
                # Restore original bone selection
                bpy.ops.pose.select_all(action='DESELECT')
                for bone_name in state['selected_bones']:
                    if bone_name in armature.data.bones:
                        armature.data.bones[bone_name].select = True
                
                # Also restore all other objects in the scene
                for scene_obj in state['hidden_objects']:
                    scene_obj.hide_viewport = False
                
                state['hidden_objects'] = []
                state['active'] = False
                self.report({'INFO'}, "Global isolate mode disabled (Pose Mode)")
        
        # EDIT ARMATURE MODE
        elif mode == 'EDIT_ARMATURE':
            state = isolate_states['GLOBAL']['EDIT_ARMATURE']
            armature = context.object
            
            if not state['active']:
                # Store selected bone names
                selected_bones = [bone.name for bone in armature.data.edit_bones if bone.select]
                if not selected_bones:
                    self.report({'WARNING'}, "No bones selected")
                    return {'CANCELLED'}
                
                state['selected_bones'] = selected_bones
                
                # Hide unselected bones
                for bone in armature.data.edit_bones:
                    if bone.name not in selected_bones:
                        bone.hide = True
                
                # Also hide all other objects in the scene (global isolation)
                hidden = []
                for scene_obj in context.view_layer.objects:
                    if scene_obj != armature and not scene_obj.hide_viewport:
                        hidden.append(scene_obj)
                        scene_obj.hide_viewport = True
                
                state['hidden_objects'] = hidden
                state['active'] = True
                self.report({'INFO'}, "Global isolate mode enabled (Armature Edit Mode)")
            
            else:
                # Unhide all bones
                for bone in armature.data.edit_bones:
                    bone.hide = False
                
                # Restore original bone selection
                bpy.ops.armature.select_all(action='DESELECT')
                for bone_name in state['selected_bones']:
                    if bone_name in armature.data.edit_bones:
                        armature.data.edit_bones[bone_name].select = True
                        armature.data.edit_bones[bone_name].select_head = True
                        armature.data.edit_bones[bone_name].select_tail = True
                
                # Also restore all other objects in the scene
                for scene_obj in state['hidden_objects']:
                    scene_obj.hide_viewport = False
                
                state['hidden_objects'] = []
                state['active'] = False
                self.report({'INFO'}, "Global isolate mode disabled (Armature Edit Mode)")
        
        else:
            self.report({'WARNING'}, f"Global isolate not supported in {mode} mode")
            return {'CANCELLED'}
        
        # Force viewport update
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

#----------------------------------------------------------------------------------
# PREFERENCES
#----------------------------------------------------------------------------------
class IsolateSelectPreferences(AddonPreferences):
    bl_idname = __name__
    
    # Enable/disable options
    enable_local_isolate: BoolProperty(
        name="Enable Local Isolation",
        description="Enable or disable the local isolation feature",
        default=True
    )
    
    enable_global_isolate: BoolProperty(
        name="Enable Global Isolation",
        description="Enable or disable the global isolation feature",
        default=True
    )
    
    # Local isolate hotkey settings
    local_key_type: EnumProperty(
        name="Hotkey",
        description="Key for the local isolate shortcut",
        items=[
            ('A', 'A', ''), ('B', 'B', ''), ('C', 'C', ''),
            ('D', 'D', ''), ('E', 'E', ''), ('F', 'F', ''),
            ('G', 'G', ''), ('H', 'H', ''), ('I', 'I', ''),
            ('J', 'J', ''), ('K', 'K', ''), ('L', 'L', ''),
            ('M', 'M', ''), ('N', 'N', ''), ('O', 'O', ''),
            ('P', 'P', ''), ('Q', 'Q', ''), ('R', 'R', ''),
            ('S', 'S', ''), ('T', 'T', ''), ('U', 'U', ''),
            ('V', 'V', ''), ('W', 'W', ''), ('X', 'X', ''),
            ('Y', 'Y', ''), ('Z', 'Z', ''),
            ('ZERO', '0', ''), ('ONE', '1', ''), ('TWO', '2', ''),
            ('THREE', '3', ''), ('FOUR', '4', ''), ('FIVE', '5', ''),
            ('SIX', '6', ''), ('SEVEN', '7', ''), ('EIGHT', '8', ''),
            ('NINE', '9', ''),
            ('NUMPAD_0', 'Numpad 0', ''), ('NUMPAD_1', 'Numpad 1', ''),
            ('NUMPAD_2', 'Numpad 2', ''), ('NUMPAD_3', 'Numpad 3', ''),
            ('NUMPAD_4', 'Numpad 4', ''), ('NUMPAD_5', 'Numpad 5', ''),
            ('NUMPAD_6', 'Numpad 6', ''), ('NUMPAD_7', 'Numpad 7', ''),
            ('NUMPAD_8', 'Numpad 8', ''), ('NUMPAD_9', 'Numpad 9', ''),
            ('SPACE', 'Space', ''), ('TAB', 'Tab', ''),
            ('F1', 'F1', ''), ('F2', 'F2', ''), ('F3', 'F3', ''),
            ('F4', 'F4', ''), ('F5', 'F5', ''), ('F6', 'F6', ''),
            ('F7', 'F7', ''), ('F8', 'F8', ''), ('F9', 'F9', ''),
            ('F10', 'F10', ''), ('F11', 'F11', ''), ('F12', 'F12', '')
        ],
        default='I'
    )
    
    local_use_shift: BoolProperty(
        name="Shift",
        description="Use Shift modifier for local isolate",
        default=True
    )
    
    local_use_ctrl: BoolProperty(
        name="Ctrl",
        description="Use Ctrl modifier for local isolate",
        default=False
    )
    
    local_use_alt: BoolProperty(
        name="Alt",
        description="Use Alt modifier for local isolate",
        default=False
    )
    
    # Global isolate hotkey settings
    global_key_type: EnumProperty(
        name="Hotkey",
        description="Key for the global isolate shortcut",
        items=[
            ('A', 'A', ''), ('B', 'B', ''), ('C', 'C', ''),
            ('D', 'D', ''), ('E', 'E', ''), ('F', 'F', ''),
            ('G', 'G', ''), ('H', 'H', ''), ('I', 'I', ''),
            ('J', 'J', ''), ('K', 'K', ''), ('L', 'L', ''),
            ('M', 'M', ''), ('N', 'N', ''), ('O', 'O', ''),
            ('P', 'P', ''), ('Q', 'Q', ''), ('R', 'R', ''),
            ('S', 'S', ''), ('T', 'T', ''), ('U', 'U', ''),
            ('V', 'V', ''), ('W', 'W', ''), ('X', 'X', ''),
            ('Y', 'Y', ''), ('Z', 'Z', ''),
            ('ZERO', '0', ''), ('ONE', '1', ''), ('TWO', '2', ''),
            ('THREE', '3', ''), ('FOUR', '4', ''), ('FIVE', '5', ''),
            ('SIX', '6', ''), ('SEVEN', '7', ''), ('EIGHT', '8', ''),
            ('NINE', '9', ''),
            ('NUMPAD_0', 'Numpad 0', ''), ('NUMPAD_1', 'Numpad 1', ''),
            ('NUMPAD_2', 'Numpad 2', ''), ('NUMPAD_3', 'Numpad 3', ''),
            ('NUMPAD_4', 'Numpad 4', ''), ('NUMPAD_5', 'Numpad 5', ''),
            ('NUMPAD_6', 'Numpad 6', ''), ('NUMPAD_7', 'Numpad 7', ''),
            ('NUMPAD_8', 'Numpad 8', ''), ('NUMPAD_9', 'Numpad 9', ''),
            ('SPACE', 'Space', ''), ('TAB', 'Tab', ''),
            ('F1', 'F1', ''), ('F2', 'F2', ''), ('F3', 'F3', ''),
            ('F4', 'F4', ''), ('F5', 'F5', ''), ('F6', 'F6', ''),
            ('F7', 'F7', ''), ('F8', 'F8', ''), ('F9', 'F9', ''),
            ('F10', 'F10', ''), ('F11', 'F11', ''), ('F12', 'F12', '')
        ],
        default='G'
    )
    
    global_use_shift: BoolProperty(
        name="Shift",
        description="Use Shift modifier for global isolate",
        default=True
    )
    
    global_use_ctrl: BoolProperty(
        name="Ctrl", 
        description="Use Ctrl modifier for global isolate",
        default=False
    )
    
    global_use_alt: BoolProperty(
        name="Alt",
        description="Use Alt modifier for global isolate",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Enable/disable options
        box = layout.box()
        box.label(text="Feature Settings:")
        row = box.row()
        row.prop(self, "enable_local_isolate")
        row.prop(self, "enable_global_isolate")
        
        # Local isolate hotkey settings
        box = layout.box()
        box.label(text="Local Isolate Hotkey Settings (isolates within current object):")
        box.enabled = self.enable_local_isolate
        row = box.row()
        row.prop(self, "local_key_type")
        row = box.row()
        row.prop(self, "local_use_shift")
        row.prop(self, "local_use_ctrl")
        row.prop(self, "local_use_alt")
        
        # Global isolate hotkey settings
        box = layout.box()
        box.label(text="Global Isolate Hotkey Settings (isolates and hides everything else):")
        box.enabled = self.enable_global_isolate
        row = box.row()
        row.prop(self, "global_key_type")
        row = box.row()
        row.prop(self, "global_use_shift")
        row.prop(self, "global_use_ctrl")
        row.prop(self, "global_use_alt")
        
        # Apply button for both
        layout.operator("isolate.update_hotkeys", text="Apply Hotkey Settings")

class ISOLATE_OT_update_hotkeys(Operator):
    """Apply both local and global hotkey settings"""
    bl_idname = "isolate.update_hotkeys"
    bl_label = "Apply Isolate Hotkey Settings"
    
    def execute(self, context):
        # Remove existing hotkeys
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
        addon_keymaps.clear()
        
        # Set up new hotkeys
        setup_keymaps()
        
        self.report({'INFO'}, "Isolate hotkeys updated. If not working, try restarting Blender.")
        return {'FINISHED'}

#----------------------------------------------------------------------------------
# PANEL
#----------------------------------------------------------------------------------
class VIEW3D_PT_isolate_select(Panel):
    bl_label = "Isolate Select"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'View'
    
    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[__name__].preferences
        
        col = layout.column(align=True)
        
        # Only show enabled operators
        if prefs.enable_local_isolate:
            col.operator("view3d.local_isolate", text="Toggle Local Isolation", icon='HIDE_OFF')
        
        if prefs.enable_global_isolate:
            col.operator("view3d.global_isolate", text="Toggle Global Isolation", icon='WORLD')
        
        # Show current state
        mode = context.mode
        if mode in ['OBJECT', 'EDIT_MESH', 'POSE', 'EDIT_ARMATURE']:
            box = layout.box()
            col = box.column()
            
            # Convert mode to dictionary key
            mode_key = mode
            
            # Show local isolation state if enabled
            if prefs.enable_local_isolate:
                local_state = isolate_states['LOCAL'][mode_key]['active']
                if local_state:
                    col.label(text="Local Isolation: Active", icon='CHECKMARK')
                else:
                    col.label(text="Local Isolation: Inactive", icon='X')
                    
            # Show global isolation state if enabled
            if prefs.enable_global_isolate:
                global_state = isolate_states['GLOBAL'][mode_key]['active']
                if global_state:
                    col.label(text="Global Isolation: Active", icon='CHECKMARK')
                else:
                    col.label(text="Global Isolation: Inactive", icon='X')

#----------------------------------------------------------------------------------
# MENU ITEMS
#----------------------------------------------------------------------------------
def draw_items(self, context):
    layout = self.layout
    prefs = context.preferences.addons[__name__].preferences
    
    layout.separator()
    
    if prefs.enable_local_isolate:
        layout.operator("view3d.local_isolate", text="Toggle Local Isolation")
    
    if prefs.enable_global_isolate:
        layout.operator("view3d.global_isolate", text="Toggle Global Isolation")

#----------------------------------------------------------------------------------
# KEYMAPS
#----------------------------------------------------------------------------------
# Store keymaps to remove when unregistering
addon_keymaps = []

def setup_keymaps():
    # Add keymaps
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    
    if kc:
        prefs = bpy.context.preferences.addons[__name__].preferences
        
        # Set up keymaps for all relevant modes
        for mode_name in ['Object Mode', 'Mesh', 'Pose', 'Armature']:
            # Local isolate keymaps (only if enabled)
            if prefs.enable_local_isolate:
                km = kc.keymaps.new(name=mode_name)
                kmi = km.keymap_items.new(
                    "view3d.local_isolate",
                    type=prefs.local_key_type,
                    value='PRESS',
                    shift=prefs.local_use_shift,
                    ctrl=prefs.local_use_ctrl,
                    alt=prefs.local_use_alt
                )
                addon_keymaps.append((km, kmi))
            
            # Global isolate keymaps (only if enabled)
            if prefs.enable_global_isolate:
                km = kc.keymaps.new(name=mode_name)
                kmi = km.keymap_items.new(
                    "view3d.global_isolate",
                    type=prefs.global_key_type,
                    value='PRESS',
                    shift=prefs.global_use_shift,
                    ctrl=prefs.global_use_ctrl,
                    alt=prefs.global_use_alt
                )
                addon_keymaps.append((km, kmi))

#----------------------------------------------------------------------------------
# REGISTRATION
#----------------------------------------------------------------------------------
def register():
    bpy.utils.register_class(ISOLATE_OT_update_hotkeys)
    bpy.utils.register_class(IsolateSelectPreferences)
    bpy.utils.register_class(VIEW3D_OT_local_isolate)
    bpy.utils.register_class(VIEW3D_OT_global_isolate)
    bpy.utils.register_class(VIEW3D_PT_isolate_select)
    
    # Add to context menus
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_items)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(draw_items)
    bpy.types.VIEW3D_MT_armature_context_menu.append(draw_items)
    bpy.types.VIEW3D_MT_pose_context_menu.append(draw_items)
    
    # Setup keymaps
    setup_keymaps()

def unregister():
    # Remove from menus
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_items)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(draw_items)
    bpy.types.VIEW3D_MT_armature_context_menu.remove(draw_items)
    bpy.types.VIEW3D_MT_pose_context_menu.remove(draw_items)
    
    # Remove keymaps
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    bpy.utils.unregister_class(VIEW3D_PT_isolate_select)
    bpy.utils.unregister_class(VIEW3D_OT_global_isolate)
    bpy.utils.unregister_class(VIEW3D_OT_local_isolate)
    bpy.utils.unregister_class(IsolateSelectPreferences)
    bpy.utils.unregister_class(ISOLATE_OT_update_hotkeys)

if __name__ == "__main__":
    register()