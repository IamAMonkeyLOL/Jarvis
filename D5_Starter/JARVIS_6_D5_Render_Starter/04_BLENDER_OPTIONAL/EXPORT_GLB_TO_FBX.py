"""Run inside Blender. Converts packaged .glb files to .fbx for D5 fallback.
Blender > Scripting > Open > Run Script. Save the script location inside ZIP extracted folder.
"""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'01_IMPORT_INTO_D5'
DEST=SOURCE/'FBX_FALLBACK_FROM_BLENDER'
DEST.mkdir(exist_ok=True,parents=True)
for file in sorted(SOURCE.glob('*.glb')):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(file))
    bpy.ops.export_scene.fbx(filepath=str(DEST/(file.stem+'.fbx')),
        use_selection=False,apply_unit_scale=True,path_mode='AUTO',
        mesh_smooth_type='FACE',axis_forward='-Z',axis_up='Y')
    print('Exported:',file.name)
print('FBX export complete:',DEST)
