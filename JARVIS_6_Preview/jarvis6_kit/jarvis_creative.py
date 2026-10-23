"""Local creative-app launch controls for the Jarvis preview."""
import os
import subprocess
from pathlib import Path

import streamlit as st

SCENES = Path(r"C:\Users\Riley\OneDrive\Documents\ChatGPT\Jarvis\D5_Starter\JARVIS_6_D5_Render_Starter\01_IMPORT_INTO_D5")
D5 = Path(os.environ['APPDATA']) / 'D5/D5 Render/d5_launcher.exe'


def blender_path():
    base = Path(os.environ.get('PROGRAMFILES', r'C:\Program Files')) / 'Blender Foundation'
    return next(iter(sorted(base.glob('Blender */blender.exe'), reverse=True)), None)


def render():
    st.subheader('Blender and D5 Render')
    blender = blender_path()
    left, right = st.columns(2)
    left.metric('Blender', 'Installed' if blender else 'Not detected')
    right.metric('D5 Render', 'Installed' if D5.is_file() else 'Not detected')
    if left.button('Open Blender', disabled=blender is None):
        try:
            subprocess.Popen([str(blender)], creationflags=subprocess.CREATE_NO_WINDOW)
            st.success('Blender launched.')
        except OSError as error:
            st.error(f'Could not launch Blender: {error}')
    if right.button('Open D5 Render', disabled=not D5.is_file()):
        try:
            subprocess.Popen([str(D5)], creationflags=subprocess.CREATE_NO_WINDOW)
            st.success('D5 launch requested.')
        except OSError as error:
            st.error(f'Could not launch D5: {error}')
    if st.button('Open shared scene folder', disabled=not SCENES.is_dir()):
        os.startfile(str(SCENES))
    st.caption(str(SCENES))
    st.info('Launch controls are ready. LiveSync must be installed and enabled separately in Blender; its connection has not yet been verified.')
    st.markdown('1. In D5 Launcher, open **Workflow** and install **D5 LiveSync for Blender**.\n2. In Blender, enable the D5 add-on in **Edit → Preferences → Add-ons**.\n3. Import a GLB scene from the shared folder, then use the D5 panel to start synchronization.')
    st.link_button('Official Blender–D5 connection guide', 'https://www.d5render.com/workflow/blender')
    fbx = SCENES / 'FBX_FALLBACK_FROM_BLENDER'
    if fbx.is_dir():
        st.write('FBX files ready for D5 import:')
        for scene in sorted(fbx.glob('*.fbx')):
            st.text(scene.name)
