#
# SPDX-FileCopyrightText: Copyright (c) 1993-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Status panel component for system monitoring."""

import gradio as gr


def create_status_panel():
    """Create the status monitoring panel."""
    
    with gr.Column(elem_classes=["status-panel"]) as status_section:
        # Panel header with close button
        with gr.Row(elem_classes=["panel-header"]):
            gr.Markdown("### Operations Status")
            close_panel_btn = gr.Button("✕", elem_classes=["close-panel-btn"], size="sm")
        
        # Status indicators
        llm_status = gr.HTML("""
            <div class="status-item">
                <span class="status-indicator online"></span>
                <span>LLM Agent: Online</span>
            </div>
        """)
        
        generation_status = gr.HTML("""
            <div class="status-item">
                <span class="status-indicator idle"></span>
                <span>3D Generation: Idle</span>
            </div>
        """)
        
        # Refresh button
        refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
        
        # Status log
        status_log = gr.Textbox(
            label="Status Log",
            lines=8,
            max_lines=20,
            interactive=False,
            value="System initialized...\n"
        )
    
    return {
        "section": status_section,
        "close_btn": close_panel_btn,
        "llm_status": llm_status,
        "generation_status": generation_status,
        "refresh_btn": refresh_btn,
        "log": status_log
    } 