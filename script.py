bl_info = {
    "name": "Bone Wiggler",
    "author": "NECRO MANIA",
    "version": (3, 0),
    "blender": (3, 0, 0),
    "location": "Vue 3D > Onglet Armature",
    "description": "Ajoute des effets physiques dynamiques aux bones sélectionnés",
    "category": "Rigging",
}

import bpy


class AddPhysicsToMultipleBonesOperator(bpy.types.Operator):
    """Ajoute de la physique à plusieurs bones sélectionnés"""
    bl_idname = "armature.add_physics_to_multiple_bones"
    bl_label = "Ajouter Physique Multi-Bones"
    bl_options = {'REGISTER', 'UNDO'}

    helper_size: bpy.props.FloatProperty(
        name="Taille des helpers",
        description="Taille des helpers physiques",
        default=0.5,
        min=0.1,
        max=5.0,
    )

    def execute(self, context):
        obj = context.object

        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Sélectionnez une armature avec des bones actifs.")
            return {'CANCELLED'}

        selected_bones = [bone for bone in obj.data.bones if bone.select]

        if not selected_bones:
            self.report({'ERROR'}, "Aucun bone sélectionné.")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')

        for bone in selected_bones:
            helper_name = f"{bone.name}_phys_helper"
            bpy.ops.mesh.primitive_cube_add(
                size=self.helper_size, 
                location=obj.matrix_world @ bone.head_local
            )
            helper = context.active_object
            helper.name = helper_name
            helper.display_type = 'WIRE'

            # Ajouter rigid body
            bpy.ops.rigidbody.object_add()
            helper.rigid_body.type = 'ACTIVE'

            # Ajouter contrainte pour suivre le bone
            bpy.ops.object.constraint_add(type='CHILD_OF')
            constraint = helper.constraints[-1]
            constraint.target = obj
            constraint.subtarget = bone.name

        self.report({'INFO'}, f"Physique ajoutée à {len(selected_bones)} bones.")
        return {'FINISHED'}


class RemoveAllHelpersOperator(bpy.types.Operator):
    """Supprime tous les helpers physiques de la scène"""
    bl_idname = "armature.remove_all_helpers"
    bl_label = "Supprimer Tous Les Helpers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        helpers = [obj for obj in bpy.data.objects if "_phys_helper" in obj.name]

        if not helpers:
            self.report({'INFO'}, "Aucun helper physique trouvé.")
            return {'CANCELLED'}

        for helper in helpers:
            bpy.data.objects.remove(helper, do_unlink=True)

        self.report({'INFO'}, f"{len(helpers)} helpers supprimés.")
        return {'FINISHED'}


class DebugPhysicsOperator(bpy.types.Operator):
    """Active/Désactive le mode debug des simulations physiques"""
    bl_idname = "armature.debug_physics"
    bl_label = "Mode Debug"
    bl_options = {'REGISTER'}

    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.rigid_body:
                obj.show_wire = not obj.show_wire
                obj.show_bounds = not obj.show_bounds

        self.report({'INFO'}, "Mode Debug activé/désactivé.")
        return {'FINISHED'}


class ExportPhysicsAnimationOperator(bpy.types.Operator):
    """Export des animations avec physique (FBX/GLTF)"""
    bl_idname = "armature.export_physics_animation"
    bl_label = "Exporter Animation Physique"
    bl_options = {'REGISTER', 'UNDO'}

    file_format: bpy.props.EnumProperty(
        name="Format",
        items=[('FBX', "FBX", ""), ('GLTF', "GLTF", "")],
        default='FBX',
    )

    filepath: bpy.props.StringProperty(
        name="Chemin de fichier",
        description="Emplacement pour l'export",
        default="//exported_animation",
        subtype='FILE_PATH',
    )

    def execute(self, context):
        # Définir le chemin avec extension
        extension = ".fbx" if self.file_format == 'FBX' else ".gltf"
        full_path = self.filepath + extension

        if self.file_format == 'FBX':
            bpy.ops.export_scene.fbx(filepath=full_path, use_selection=True, bake_anim=True)
        else:
            bpy.ops.export_scene.gltf(filepath=full_path, export_format='GLTF_EMBEDDED')

        self.report({'INFO'}, f"Animation exportée sous {full_path}")
        return {'FINISHED'}

class SelectBonesWithPhysicsOperator(bpy.types.Operator):
    """Sélectionne tous les bones ayant un helper physique"""
    bl_idname = "armature.select_bones_with_physics"
    bl_label = "Sélectionner Bones avec Physique"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Sélectionnez une armature pour utiliser cet outil.")
            return {'CANCELLED'}

        # Désélectionner tous les bones
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.armature.select_all(action='DESELECT')

        # Revenir en mode objet pour vérifier les helpers
        bpy.ops.object.mode_set(mode='OBJECT')
        armature = obj
        bones_with_helpers = []

        # Vérifier chaque helper physique et trouver son bone parent
        for helper in bpy.data.objects:
            if "_phys_helper" in helper.name:
                for constraint in helper.constraints:
                    if constraint.type == 'CHILD_OF' and constraint.target == armature:
                        bone_name = constraint.subtarget
                        if bone_name:
                            bones_with_helpers.append(bone_name)

        # Réactiver les bones correspondants
        bpy.ops.object.mode_set(mode='EDIT')
        for bone_name in bones_with_helpers:
            bone = armature.data.edit_bones.get(bone_name)
            if bone:
                bone.select = True

        self.report({'INFO'}, f"{len(bones_with_helpers)} bones avec physique sélectionnés.")
        return {'FINISHED'}

class AdvancedPhysicsPanel(bpy.types.Panel):
    """Panneau pour les outils avancés"""
    bl_label = "Physique Avancée : Multi-Bones, Debug et Export"
    bl_idname = "VIEW3D_PT_advanced_physics"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Armature'

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj and obj.type == 'ARMATURE':
            layout.label(text="Outils pour Armature et Physique")

            layout.operator("armature.add_physics_to_multiple_bones", text="Ajouter Physique (Multi-Bones)")
            layout.operator("armature.select_bones_with_physics", text="Sélectionner Bones avec Physique")
            layout.operator("armature.remove_all_helpers", text="Supprimer Tous Les Helpers")
            layout.operator("armature.debug_physics", text="Mode Debug")
            layout.operator("armature.bake_physics_to_keyframes", text="Bake Animation")
            layout.operator("armature.export_physics_animation", text="Exporter Animation")

        else:
            layout.label(text="Sélectionnez une armature pour voir les options.")


# Liste des classes
classes = [
    AddPhysicsToMultipleBonesOperator,
    RemoveAllHelpersOperator,
    DebugPhysicsOperator,
    ExportPhysicsAnimationOperator,
    AdvancedPhysicsPanel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()