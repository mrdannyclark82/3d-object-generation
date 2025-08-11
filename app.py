
"""Main Chat-to-3D Gradio Application.

This is the entry point for the Chat-to-3D application that integrates:
- LLM Agent for scene planning
- Object gallery UI 
- 3D generation pipeline

Configuration:
- ENABLE_STATUS_PANEL: Set to True to enable the status console panel
"""

import gradio as gr
import os
import base64
import signal
import sys
import time
from components.chat_interface import create_chat_interface, handle_scene_description
from components.image_gallery import create_image_gallery
from components.blender_export import create_blender_export_section, update_export_section, create_export_modal, open_export_modal, close_export_modal, export_3d_assets_to_folder
from components.status_panel import create_status_panel
from components.modal import create_modal, open_image_settings, close_modal, create_edit_modal
from components.image_card import create_refresh_handler, create_3d_generation_handler, create_convert_all_3d_handler, invalidate_3d_model
from services.agent_service import AgentService
from services.image_generation_service import ImageGenerationService
from services.model_3d_service import Model3DService
import config
import threading
import subprocess
import requests
from pathlib import Path
from nim_llm.manager import stop_container

# Global flag to track if we're shutting down
_shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
    _shutdown_requested = True
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Load custom CSS and JS
try:
    with open(config.CUSTOM_CSS_FILE) as f:
        custom_css = f.read()
    with open(config.CUSTOM_JS_FILE) as f:
        custom_js = f.read()
except FileNotFoundError:
    print("Custom CSS and JS not found")
    custom_css = ""
    custom_js = ""

# Load NVIDIA logo
try:
    with open(config.NVIDIA_LOGO_FILE, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    
    nvidia_html = f"""<div class='nvidia-logo-container'> 
            <img src='data:image/png;base64,{encoded}' alt='NVIDIA Logo' class='nvidia-logo' width='24' height='24'> 
            <span class='nvidia-text'></span> 
            </div>"""
except FileNotFoundError:
    # Fallback if logo not found
    nvidia_html = """<div class='nvidia-logo-container'> 
            <span class='nvidia-text'>Chat-to-3D</span> 
            </div>"""

# Background bootstrap for LLM NIM
_nim_bootstrap_started = False
_nim_process = None  # Store reference to the LLM NIM process

# Global state to track if we're in workspace mode
_in_workspace_mode = False

# Configuration flag to enable/disable status panel
# Set to True to enable the status console panel functionality
ENABLE_STATUS_PANEL = False

def _ensure_llm_nim_started():
    """Start the LLM NIM container in the background if it's not already healthy."""
    global _nim_bootstrap_started
    if _nim_bootstrap_started:
        return
    _nim_bootstrap_started = True

    health_url = f"{config.AGENT_BASE_URL}/health/ready"
    try:
        resp = requests.get(health_url, timeout=1.5)
        if resp.status_code == 200:
            print("✅ LLM NIM already running")
            return
    except Exception:
        pass

    def _runner():
        global _nim_process
        try:
            script_path = Path(__file__).parent / "nim_llm" / "run_llama.py"
            print(f"🚀 Starting LLM NIM via {script_path}")
            popen_kwargs = {}
            if os.name == "nt":
                popen_kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                popen_kwargs["start_new_session"] = True
            _nim_process = subprocess.Popen([sys.executable, str(script_path)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, **popen_kwargs)
        except Exception as e:
            print(f"❌ Failed to start LLM NIM: {e}")

    threading.Thread(target=_runner, daemon=True).start()


def stop_llm_container():
    """Stop the LLM container after workspace transition."""
    # Only proceed if we're in workspace mode (valid scene input)
    global _in_workspace_mode, _nim_bootstrap_started
    if not _in_workspace_mode:
        return
    
    try:
        print("🛑 Stopping LLM NIM container...")
        success = stop_container()
        _nim_bootstrap_started = False
        if success:
            print("✅ LLM NIM container stopped and bootstrap reset")
        else:
            print("⚠️ LLM NIM container stop command executed (may not have been running)")
    except Exception as e:
        print(f"❌ Error stopping LLM container: {e}")
        _nim_bootstrap_started = False

def create_app():
    """Create and configure the main Gradio application."""
    
    # Initialize services
    agent_service = AgentService()
    image_generation_service = ImageGenerationService()
    model_3d_service = Model3DService()

    # Kick off NIM container in background if needed (non-blocking)
    _ensure_llm_nim_started()

    with gr.Blocks(
        title="Chat-to-3D", 
        # css_paths=["static/css/custom.css"]
    ) as app:
        
        
        # Inject custom CSS and JS
        gr.HTML(f"<style>{custom_css}</style>")
        gr.HTML(f"<script>{custom_js}</script>")
        
        # Header with NVIDIA branding and status
        with gr.Row(elem_classes=["header-section"]):
            with gr.Column(scale=1):
                with gr.Row():
                    gr.HTML(nvidia_html)
            with gr.Column(scale=1):
                with gr.Row(elem_classes=["status-row"]):
                    llm_status = gr.HTML("""
                    <div>
                        <span class="status-text"></span>
                    </div>
                    """)
                    refresh_status_btn = gr.Button("🔄", elem_classes=["refresh-status-btn"], size="sm", visible=False)
                    toggle_btn = gr.Button(">", elem_classes=["toggle-status-btn"], size="sm")
            
        # Global spinner overlay shown until LLM is ready
        llm_spinner = gr.HTML(
            """
            <div class="llm-spinner-overlay">
                <div class="llm-spinner-content">
                    <div class="llm-spinner-ring"></div>
                    <div>
                        <div class="llm-spinner-title">Loading LLM model</div>
                        <div class="llm-spinner-subtitle">This could take a few minutes...</div>
                    </div>
                </div>
            </div>
            """,
            visible=True,
        )
        
        # Main layout
        with gr.Row(elem_classes=["content-row"]):
            # Left: Chat and Gallery
            with gr.Column(scale=4, elem_classes=["main-content", "landing"]) as main_col:
                # Chat interface (landing screen) - hidden until LLM is ready
                chat_components = create_chat_interface()
                chat_components["section"].visible = False
                # Don't set visible=False here, let the Timer control it

                # Workspace (hidden initially): gallery + export
                with gr.Column(visible=False, elem_classes=["workspace-section"]) as workspace_section:
                    with gr.Row():
                        start_over_btn = gr.Button("← Start over with a new scene prompt", elem_classes=["start-over-btn"], size="sm")
                    # Object gallery
                    gallery_components = create_image_gallery()
                    
                    # Blender export section
                    export_components = create_blender_export_section()
                
                # Export status textbox
                export_status = gr.Textbox(label="Export Status", interactive=False, visible=False)
                
                # Modal UI
                modal_visible = gr.State(False)
                overlay = gr.HTML("""
                <div id='modal-overlay' style='display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.4); z-index:999;'></div>
                """)
                
                # Modal components
                settings_modal, modal_image_title, close_btn, modal_image, modal_3d, no_3d_message = create_modal()
                settings_modal.visible = False
                
                # Edit modal components
                edit_modal, edit_image_title, edit_description, cancel_edit_btn, update_edit_btn = create_edit_modal()
                edit_modal.visible = False
                edit_current_index = gr.State(None)
                
                # Export modal components
                export_modal, scene_folder_input, export_cancel_btn, export_save_btn = create_export_modal()
                export_modal.visible = False
                
                # State to track if we're in workspace mode (to prevent health poller from showing chat)
                in_workspace_mode = gr.State(False)
                
            # Right: Status panel
            # Right: Status panel (conditionally enabled)
            if ENABLE_STATUS_PANEL:
                with gr.Column(scale=1, elem_classes=["right-panel"], visible=False) as right_panel:
                    status_components = create_status_panel()
            else:
                # Placeholder for when status panel is disabled
                right_panel = gr.Column(visible=False)
                status_components = {"close_btn": gr.Button(visible=False)}
        
        # Wire up the event handlers
        def process_scene_description(scene_description, gallery_data):
            """Process scene description and generate objects, then update gallery."""
            if not scene_description.strip():
                tip_html = """
                <div class="tip-message">
                    <span class="tip-icon">💡</span>
                    <span class="tip-text">Please enter a scene description.</span>
                </div>
                """
                return "", gallery_data, tip_html, True
            
            message, new_gallery_data, tip_html, show_tip = handle_scene_description(scene_description, agent_service, gallery_data, None)
            
            # If we should show a tip (non-scene input), don't proceed with gallery updates
            if show_tip:
                return "", gallery_data, tip_html, True
            
            # If it's a valid scene, proceed with normal flow
            return message, new_gallery_data, "", False
        
        def handle_scene_with_conditional_flow(scene_description, gallery_data):
            """Handle scene processing with conditional workspace transition."""
            message, new_gallery_data, tip_html, show_tip = process_scene_description(scene_description, gallery_data)
            
            # If it's a valid scene, proceed with all the normal flow
            if not show_tip:
                # This will trigger the workspace transition
                return message, new_gallery_data, "", False, True
            else:
                # This will just show the tip and stay on first screen
                return "", gallery_data, tip_html, True, False
        
        def handle_scene_input(scene_description, gallery_data):
            """Handle scene input and proceed with workspace transition."""
            message, new_gallery_data, tip_html, show_tip, proceed_to_workspace = handle_scene_with_conditional_flow(scene_description, gallery_data)
            
            if proceed_to_workspace:
                # Valid scene - proceed with normal flow, hide tip
                return message, new_gallery_data, gr.update(value="", visible=False)
            else:
                # Non-scene input - don't update gallery, show tip
                return "", gallery_data, gr.update(value=tip_html, visible=True)
        
        # Helper to reveal workspace and switch layout out of landing mode
        def reveal_workspace(gallery_data):
            global _in_workspace_mode
            # Only proceed with workspace transition if there's actual gallery data
            if not gallery_data or len(gallery_data) == 0:
                # No gallery data means it was a non-scene input, don't transition
                return (
                    gr.update(visible=False),                 # keep workspace hidden
                    gr.update(elem_classes=["main-content", "landing"]), # keep landing centering
                    gr.update(visible=True),                  # keep chat section visible
                    False,                                    # keep workspace mode False
                )
            
            # Valid scene with gallery data - proceed with transition
            _in_workspace_mode = True
            return (
                gr.update(visible=True),                 # show workspace
                gr.update(elem_classes=["main-content"]), # remove landing centering
                gr.update(visible=False),                # hide chat section
                True,                                    # set workspace mode to True
            )

        # Helper to reset all UI/state and return to landing
        def go_to_first_screen():
            global _in_workspace_mode
            _in_workspace_mode = False
            # Check if LLM is ready before showing chat
            health_url = f"{config.AGENT_BASE_URL}/health/ready"
            try:
                resp = requests.get(health_url, timeout=1.0)
                llm_ready = (resp.status_code == 200)
            except Exception:
                llm_ready = False
                
            #start the llM again
            if not llm_ready:
                _ensure_llm_nim_started()
            
            return (
                gr.update(visible=False),               # hide workspace
                gr.update(elem_classes=["main-content", "landing"]),  # restore landing centering
                gr.update(visible=llm_ready),           # show chat section only if LLM is ready
                gr.update(value=""),                   # clear chat input
                gr.update(visible=False),               # hide export status
                gr.update(visible=False) if ENABLE_STATUS_PANEL else gr.update(visible=False),  # hide right panel if open
                False,                                  # set workspace mode to False
                gr.update(active=True),                 # restart health timer
            )

        # New: Mark items as image-generating to disable Start Over immediately
        def mark_images_generating(gallery_data):
            if not gallery_data:
                return gallery_data
            
            # Only proceed if we're in workspace mode (valid scene input)
            global _in_workspace_mode
            if not _in_workspace_mode:
                return gallery_data
            
            updated_data = []
            for obj in gallery_data:
                new_obj = obj.copy()
                new_obj["image_generating"] = True
                updated_data.append(new_obj)
            return updated_data
        
        # New: Generate images for all objects after moving to workspace
        def generate_images_for_gallery(gallery_data):
            # Only proceed if we're in workspace mode (valid scene input)
            global _in_workspace_mode
            if not _in_workspace_mode:
                return gallery_data
                
            try:
                if not gallery_data:
                    return gallery_data
                print("🎨 Generating images for all objects (step 2)...")
                success, message, generated_images = image_generation_service.generate_images_for_objects(gallery_data)
                if success and generated_images:
                    updated_data = []
                    for obj in gallery_data:
                        object_name = obj.get("title")
                        new_obj = obj.copy()
                        if object_name in generated_images:
                            new_obj["path"] = generated_images[object_name]
                            print(f"✅ Generated image for {object_name}: {generated_images[object_name]}")
                        else:
                            print(f"⚠️ No image generated for {object_name}")
                        # Clear image generation flag after completion
                        if "image_generating" in new_obj:
                            new_obj["image_generating"] = False
                        updated_data.append(new_obj)
                    return updated_data
                else:
                    print(f"❌ Image generation failed: {message}")
                    # Clear image generation flag even on failure
                    if not gallery_data:
                        return gallery_data
                    updated_data = []
                    for obj in gallery_data:
                        new_obj = obj.copy()
                        if "image_generating" in new_obj:
                            new_obj["image_generating"] = False
                        updated_data.append(new_obj)
                    return updated_data
            except Exception as e:
                print(f"❌ Error during image generation: {str(e)}")
                # Clear image generation flag even on exception
                if not gallery_data:
                    return gallery_data
                updated_data = []
                for obj in gallery_data:
                    new_obj = obj.copy()
                    if "image_generating" in new_obj:
                        new_obj["image_generating"] = False
                    updated_data.append(new_obj)
                return updated_data
        
        # Toggle start-over availability based on processing state
        def update_start_over_state(gallery_data):
            """Update the Start Over button state based on gallery data."""
            # Only proceed if we're in workspace mode (valid scene input)
            global _in_workspace_mode
            if not _in_workspace_mode:
                return gr.update(visible=False)
            
            if not gallery_data:
                return gr.update(visible=False)
            
            # Check if any items are being processed
            any_processing = any(
                obj.get("image_generating", False) or 
                obj.get("3d_generating", False) or 
                obj.get("batch_processing", False)
                for obj in gallery_data
            )
            
            if any_processing:
                return gr.update(visible=False)  # Hide button during processing
            else:
                return gr.update(visible=True)   # Show button when ready
        
        # Health check function for LLM NIM; updates status and controls UI visibility
        def check_llm_health():
            global _in_workspace_mode
            health_url = f"{config.AGENT_BASE_URL}/health/ready"
            try:
                resp = requests.get(health_url, timeout=1.0)
                ready = (resp.status_code == 200)
            except Exception:
                ready = False
            status_color = "#16be16" if ready else "#f59e0b"
            status_label = "LLM: ready" if ready else "LLM: down"
            status_html = f'<div class="status-section"><span class="status-text" style="color:{status_color}">{status_label}</span></div>'
            show_spinner = not ready and not _in_workspace_mode
            # Only show chat when LLM is ready AND we're not in workspace mode
            show_chat = ready and not _in_workspace_mode
            # Show refresh button when in workspace mode, hide when in landing mode
            show_refresh = True
            # Stop timer if we're in workspace mode
            timer_active = not _in_workspace_mode
            print(f"🔍 Checking LLM health... in_workspace_mode: {_in_workspace_mode} timer_active: {timer_active}")
            return gr.update(visible=show_spinner), gr.update(value=status_html), gr.update(visible=show_chat), gr.update(visible=show_refresh), gr.update(active=timer_active)
        
        # Timer for initial health polling (only active until we reach workspace mode)
        health_timer = gr.Timer(5, active=True)
        health_timer.tick(
            fn=check_llm_health,
            outputs=[llm_spinner, llm_status, chat_components["section"], refresh_status_btn, health_timer]
        )
        
        # Wire up manual refresh button
        refresh_status_btn.click(
            fn=check_llm_health,
            outputs=[llm_spinner, llm_status, chat_components["section"], refresh_status_btn, health_timer]
        )
        
        # Connect send button to process scene description
        chat_components["send_btn"].click(
            fn=handle_scene_input,
            inputs=[chat_components["input"], gallery_components["data"]],
            outputs=[chat_components["input"], gallery_components["data"], chat_components["tip"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_export_section,
            inputs=[gallery_components["data"]],
            outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
        ).then(
            fn=reveal_workspace,
            inputs=[gallery_components["data"]],
            outputs=[workspace_section, main_col, chat_components["section"], in_workspace_mode]
        ).then(
            fn=mark_images_generating,
            inputs=[gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_start_over_state,
            inputs=[gallery_components["data"]],
            outputs=[start_over_btn]
        ).then(
            fn=stop_llm_container,
            inputs=[],
            outputs=[]
        ).then(
            fn=generate_images_for_gallery,
            inputs=[gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_export_section,
            inputs=[gallery_components["data"]],
            outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
        ).then(
            fn=update_start_over_state,
            inputs=[gallery_components["data"]],
            outputs=[start_over_btn]
        )
        
        # Connect Enter key for scene input
        chat_components["input"].submit(
            fn=handle_scene_input,
            inputs=[chat_components["input"], gallery_components["data"]],
            outputs=[chat_components["input"], gallery_components["data"], chat_components["tip"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_export_section,
            inputs=[gallery_components["data"]],
            outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
        ).then(
            fn=reveal_workspace,
            inputs=[gallery_components["data"]],
            outputs=[workspace_section, main_col, chat_components["section"], in_workspace_mode]
        ).then(
            fn=mark_images_generating,
            inputs=[gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_start_over_state,
            inputs=[gallery_components["data"]],
            outputs=[start_over_btn]
        ).then(
            fn=stop_llm_container,
            inputs=[],
            outputs=[]
        ).then(
            fn=generate_images_for_gallery,
            inputs=[gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_export_section,
            inputs=[gallery_components["data"]],
            outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
        ).then(
            fn=update_start_over_state,
            inputs=[gallery_components["data"]],
            outputs=[start_over_btn]
        )

        # Start over button: clear gallery/export and return to landing screen
        def clear_gallery_state(_):
            return []

        start_over_btn.click(
            fn=clear_gallery_state,
            inputs=[gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=go_to_first_screen,
            inputs=[],
            outputs=[workspace_section, main_col, chat_components["section"], chat_components["input"], export_status, right_panel, in_workspace_mode, health_timer]
        )
        
        # Connect toggle button to show/hide right panel (only if status panel is enabled)
        if ENABLE_STATUS_PANEL:
            toggle_btn.click(
                fn=lambda: gr.update(visible=True),
                outputs=[right_panel]
            )
            
            # Connect close button to hide right panel
            status_components["close_btn"].click(
                fn=lambda: gr.update(visible=False),
                outputs=[right_panel]
            )
        else:
            # Hide toggle button when status panel is disabled
            toggle_btn.visible = False
        
        # Modal functionality
        def debug_card_click(path, title, gallery_data, card_idx):
            print(f"DEBUG: Card clicked! Path: {path}, Title: {title}, Card Index: {card_idx}")
            return open_image_settings(path, title, gallery_data, card_idx)
        
        # Wire up card click events for modal
        for idx, card in enumerate(gallery_components["card_components"]):
            def create_dynamic_click_handler(card_idx):
                def click_handler(gallery_data):
                    if card_idx < len(gallery_data):
                        item = gallery_data[card_idx]
                        print(f"DEBUG: Dynamic click for card {card_idx}: {item['title']}")
                        return debug_card_click(item["path"], item["title"], gallery_data, card_idx)
                    else:
                        print(f"DEBUG: Card {card_idx} not found in gallery_data")
                        return debug_card_click("", "", gallery_data, card_idx)
                return click_handler
            
            card["card_click_btn"].click(
                fn=create_dynamic_click_handler(idx),
                inputs=[gallery_components["data"]],
                outputs=[modal_image_title, modal_image, modal_visible, overlay, modal_3d]
            ).then(
                fn=lambda: gr.update(visible=True),
                outputs=[settings_modal]
            ).then(
                fn=lambda glb_path: (gr.update(visible=(glb_path is not None)), gr.update(visible=(glb_path is None))),
                inputs=[modal_3d],
                outputs=[modal_3d, no_3d_message]
            )
        
        # Close modal button
        close_btn.click(
            fn=close_modal,
            inputs=[],
            outputs=[modal_image_title, modal_image, modal_visible, overlay, modal_3d]
        ).then(
            fn=lambda: gr.update(visible=False),
            outputs=[settings_modal]
        ).then(
            fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
            outputs=[modal_3d, no_3d_message]
        )
        
        # Edit modal functionality
        def open_edit_modal(idx, gallery_data):
            """Open edit modal for the specified card index."""
            if idx < len(gallery_data):
                item = gallery_data[idx]
                return (
                    gr.update(visible=True),  # Show modal
                    idx,                     # Set current index
                    f"### Edit {item['title']}",  # Modal title
                    item["description"]      # Populate description
                )
            else:
                return (gr.update(visible=True), idx, "### Edit", "")
        
        # Create refresh handler
        refresh_handler = create_refresh_handler(image_generation_service)
        
        # Create 3D generation handler
        three_d_handler = create_3d_generation_handler(model_3d_service)
        
        # Create convert all to 3D handler (two-stage process)
        disable_buttons_handler, convert_all_handler = create_convert_all_3d_handler(model_3d_service)
        
        def update_modal_3d_components(gallery_data, card_idx):
            """Update modal 3D components based on 3D model availability."""
            if card_idx < len(gallery_data):
                obj = gallery_data[card_idx]
                if obj.get("glb_path") and os.path.exists(obj["glb_path"]):
                    return gr.update(value=obj["glb_path"], visible=True), gr.update(visible=False)
                else:
                    return gr.update(value=None, visible=False), gr.update(visible=True)
            else:
                return gr.update(value=None, visible=False), gr.update(visible=True)
        
        # Wire up refresh button events for each card
        for idx, card in enumerate(gallery_components["card_components"]):
            def create_refresh_function(card_idx):
                def refresh_specific_card(gallery_data):
                    return refresh_handler(card_idx, gallery_data)
                return refresh_specific_card
            
            card["refresh_btn"].click(
                fn=create_refresh_function(idx),
                inputs=[gallery_components["data"]],
                outputs=[gallery_components["data"]]
            ).then(
                fn=gallery_components["shift_card_ui"],
                inputs=[gallery_components["data"]],
                outputs=gallery_components["get_all_card_outputs"]()
            ).then(
                fn=update_export_section,
                inputs=[gallery_components["data"]],
                outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
            )
        
        # Wire up 3D generation button events for each card
        for idx, card in enumerate(gallery_components["card_components"]):
            def create_3d_function(card_idx):
                def generate_3d_for_card(gallery_data):
                    # Immediately update the button to show "generating" state
                    if card_idx < len(gallery_data):
                        # Create a copy and mark as generating
                        updated_data = gallery_data.copy()
                        updated_data[card_idx]["3d_generating"] = True
                        print(f"🔍 DEBUG: Set 3d_generating=True for card {card_idx}")
                        
                        # Return the updated data immediately to show "⏳ 3D..." state
                        return updated_data
                    else:
                        print(f"🔍 DEBUG: Card index {card_idx} out of range")
                        return gallery_data
                
                def perform_3d_generation(gallery_data):
                    print(f"🔍 DEBUG: Performing actual 3D generation for card {card_idx}")
                    result = three_d_handler(card_idx, gallery_data)
                    return result
                
                return generate_3d_for_card, perform_3d_generation
            
            # Create the functions for this specific card
            immediate_update_fn, generation_fn = create_3d_function(idx)
            
            # First click: immediate UI update
            card["to_3d_btn"].click(
                fn=immediate_update_fn,
                inputs=[gallery_components["data"]],
                outputs=[gallery_components["data"]]
            ).then(
                fn=gallery_components["shift_card_ui"],
                inputs=[gallery_components["data"]],
                outputs=gallery_components["get_all_card_outputs"]()
            ).then(
                fn=update_start_over_state,              # immediately disable Start Over
                inputs=[gallery_components["data"]],
                outputs=[start_over_btn]
            ).then(
                fn=generation_fn,
                inputs=[gallery_components["data"]],
                outputs=[gallery_components["data"]]
            ).then(
                fn=gallery_components["shift_card_ui"],
                inputs=[gallery_components["data"]],
                outputs=gallery_components["get_all_card_outputs"]()
            ).then(
                fn=update_export_section,
                inputs=[gallery_components["data"]],
                outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
            ).then(
                fn=update_start_over_state,
                inputs=[gallery_components["data"]],
                outputs=[start_over_btn]
            ).then(
                fn=lambda data, idx=idx: update_modal_3d_components(data, idx),
                inputs=[gallery_components["data"]],
                outputs=[modal_3d, no_3d_message]
            )
        
        # Wire up edit button events for each card
        for idx, card in enumerate(gallery_components["card_components"]):
            card["edit_btn"].click(
                fn=open_edit_modal,
                inputs=[gr.State(idx), gallery_components["data"]],
                outputs=[edit_modal, edit_current_index, edit_image_title, edit_description]
            )
        
        # Cancel edit button
        cancel_edit_btn.click(
            fn=lambda: (gr.update(visible=False), None, "", ""),
            outputs=[edit_modal, edit_current_index, edit_image_title, edit_description]
        )
        
        # Update edit button
        def update_object_description(edit_idx, new_description, gallery_data):
            """Update the description of an object in the gallery and generate a new image."""
            if edit_idx is not None and edit_idx < len(gallery_data):
                # Validate the new description
                if not new_description or not new_description.strip():
                    print(f"❌ Empty description provided for card {edit_idx}")
                    return gallery_data
                
                updated_data = gallery_data.copy()
                obj = updated_data[edit_idx]
                object_name = obj["title"]
                
                # Update the description
                updated_data[edit_idx]["description"] = new_description.strip()

                # if gallery_data[edit_idx]["description"] == updated_data[edit_idx]["description"] :
                #     print(f"❌ No change in description for card {edit_idx}")
                #     return gallery_data
                
                # Generate a new random seed for the updated prompt
                import random
                new_seed = random.randint(1, 999999)
                
                print(f"🔄 Updating image for '{object_name}' with new prompt and seed {new_seed}")
                print(f"   New prompt: {new_description}")
                
                # Generate new image using SANA service with the updated prompt
                success, message, new_image_path = image_generation_service.generate_image_from_prompt(
                    object_name=object_name,
                    prompt=new_description.strip(),
                    output_dir=config.GENERATED_IMAGES_DIR,
                    seed=new_seed
                )
                
                if success and new_image_path:
                    # Update the image path and seed
                    updated_data[edit_idx]["path"] = new_image_path
                    updated_data[edit_idx]["seed"] = new_seed
                    
                                    # Invalidate 3D model using the helper function
                updated_data = invalidate_3d_model(updated_data, edit_idx, object_name, "image update")
                
                # Clear batch processing flag if it was set
                if "batch_processing" in updated_data[edit_idx]:
                    del updated_data[edit_idx]["batch_processing"]
                    
                    print(f"✅ Successfully generated new image: {new_image_path}")
                else:
                    print(f"❌ Failed to generate new image: {message}")
                
                return updated_data
            return gallery_data
        
        update_edit_btn.click(
            fn=update_object_description,
            inputs=[edit_current_index, edit_description, gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_export_section,
            inputs=[gallery_components["data"]],
            outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
        ).then(
            fn=lambda: (gr.update(visible=False), None, "", ""),
            outputs=[edit_modal, edit_current_index, edit_image_title, edit_description]
        )
        
        # Wire up delete button events for each card
        for idx, card in enumerate(gallery_components["card_components"]):
            def create_delete_function(card_idx):
                def delete_specific_card(gallery_data):
                    if card_idx < len(gallery_data):
                        print(f"🗑️ Deleting card at index: {card_idx} title: {gallery_data[card_idx]['title']}")
                        # Check if this card has a 3D asset that will be removed
                        has_3d_asset = gallery_data[card_idx].get("glb_path") and gallery_data[card_idx]["glb_path"]
                        if has_3d_asset:
                            print(f"🗑️ Removing 3D asset: {gallery_data[card_idx]['glb_path']}")
                        
                        # Remove the card from gallery data
                        updated_data = [item for i, item in enumerate(gallery_data) if i != card_idx]
                        return updated_data
                    else:
                        print(f"❌ Card index {card_idx} out of range")
                        return gallery_data
                return delete_specific_card
            
            card["delete_btn"].click(
                fn=create_delete_function(idx),
                inputs=[gallery_components["data"]],
                outputs=[gallery_components["data"]]
            ).then(
                fn=gallery_components["shift_card_ui"],
                inputs=[gallery_components["data"]],
                outputs=gallery_components["get_all_card_outputs"]()
            ).then(
                fn=update_export_section,
                inputs=[gallery_components["data"]],
                outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
            )
        
        # Wire up convert all to 3D button (two-stage process)
        gallery_components["convert_all_btn"].click(
            fn=disable_buttons_handler,
            inputs=[gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_start_over_state,                  # immediately disable Start Over during batch
            inputs=[gallery_components["data"]],
            outputs=[start_over_btn]
        ).then(
            fn=convert_all_handler,
            inputs=[gallery_components["data"]],
            outputs=[gallery_components["data"]]
        ).then(
            fn=gallery_components["shift_card_ui"],
            inputs=[gallery_components["data"]],
            outputs=gallery_components["get_all_card_outputs"]()
        ).then(
            fn=update_export_section,
            inputs=[gallery_components["data"]],
            outputs=[export_components["count_display"], export_components["thumbnails_container"], export_components["export_btn"], export_components["placeholder"], export_components["export_content_active"]]
        ).then(
            fn=update_start_over_state,
            inputs=[gallery_components["data"]],
            outputs=[start_over_btn]
        )
        
        # Wire up export button to open modal
        export_components["export_btn"].click(
            fn=open_export_modal,
            inputs=[gallery_components["data"]],
            outputs=[export_modal]
        )
        
        # Wire up export modal event handlers
        export_cancel_btn.click(
            fn=close_export_modal,
            outputs=[export_modal, scene_folder_input]
        )
        
        # Wire up save button to export assets
        export_save_btn.click(
            fn=export_3d_assets_to_folder,
            inputs=[gallery_components["data"], scene_folder_input],
            outputs=[export_modal]
        ).then(
            fn=close_export_modal,
            outputs=[export_modal, scene_folder_input]
        )
        
    return app


if __name__ == "__main__":
    app = None
    try:
        print("🚀 Starting Chat-to-3D application...")
        app = create_app()
        app.launch(debug=True, server_name="127.0.0.1", server_port=7860, share=False, quiet=True)
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        print("🧹 Cleaning up resources...")
        try:
            # Stop the LLM NIM process if it's running
            if _nim_process and _nim_process.poll() is None:
                print("🛑 Stopping LLM NIM process...")
                try:
                    _nim_process.terminate()
                    _nim_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("⚠️ LLM NIM process didn't stop gracefully, forcing...")
                    _nim_process.kill()
                except Exception as e:
                    print(f"⚠️ Error stopping LLM NIM process: {e}")
            
            # Stop the LLM NIM container
            print("🛑 Stopping LLM NIM container...")
            stop_llm_container()
            
            # Give the container a moment to stop
            time.sleep(2)
            
            # Force stop if still running (Windows-specific)
            if os.name == "nt":
                try:
                    subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                except:
                    pass
            
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
        finally:
            print("👋 Application shutdown complete") 