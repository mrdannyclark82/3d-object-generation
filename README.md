# chat-to-3d

An application that combines natural language processing with 3D asset generation using SANA and TRELLIS.

## Features

- Chat interface for scene planning
- AI-assisted object and prompt generation
- Automatic 3D asset generation from text prompts
- Blender import functionality for generated assets
- VRAM management with model termination

## Installation 

### Prerequisites
The NIM Prerequisite Installer requires Microsoft User Account Control (UAC) to be enabled.  UAC is enabled by default for Windows, but if it has been disabled, it must be enabled to ensure successful installation of the NIM Prerequisite Installer.  More information on Microsoft UAC can found [HERE](https://support.microsoft.com/en-us/windows/user-account-control-settings-d5b2046b-dcb8-54eb-f732-059f321afe18)

Download the [MS Visual Studio Build Tools vs_buildTools.exe](https://aka.ms/vs/17/release/vs_BuildTools.exe)
Open a command prompt at the vs_BuildTools.exe file location and send the following command:
```
vs_buildtools.exe --norestart --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
```
Use winget to install Miniconda:
```
winget install miniconda3
```
Download the NVIDIA CUDA Toolkit 12.9
[NVIDIA CUDA Toolkit 12.9](https://developer.download.nvidia.com/compute/cuda/12.9.0/local_installers/cuda_12.9.0_576.02_windows.exe)
Run the installer and select a custom installation.
![Screenshot 2025-05-22 221843](https://github.com/user-attachments/assets/e2e7fe07-d530-4aca-9668-a8566d1d5864)
From the options select ONLY:  
CUDA  >> Development >> Compiler
CUDA >> Runtime >> Libraries
![Screenshot 2025-05-22 222023](https://github.com/user-attachments/assets/9ccd92cc-55a5-467d-b4f3-f1e821a07689)
Complete the installation

Download the [NIM Prerequisite Installer](https://assets.ngc.nvidia.com/products/api-catalog/rtx/NIMSetup.exe), and run the NIMSetup.exe file, and follow the instructions in the setup dialogs. This will install the necessary system components to work with NVIDIA NIMs on your system.

You will need to reboot your computer to complete the installation.

Git is required and should be installed using winget from a command prompt::
```
winget install --id Git.Git 
```
Install Git LFS (large file system) support
```
winget install --id=GitHub.GitLFS  -e
```

Install Microsoft Visual C++ 2015-2022 Redistributable Package  
[https://aka.ms/vs/17/release/vc\_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)
or
```
winget install Microsoft.VCRedist.2015+.x64
```
![Untitled-8](https://github.com/user-attachments/assets/29184836-3791-4c22-8a40-3254590faa0e)

This blueprint requires the installation of Blender. The blueprint has been tested with the Blender 4.27 LTS (Long Term Support) build.   
[https://www.blender.org/download/release/Blender4.2/blender-4.2.7-windows-x64.msi](https://www.blender.org/download/release/Blender4.2/blender-4.2.7-windows-x64.msi)

Blender 4.27 can also be installed using winget from a command prompt:
```
winget install --id 9NW1B444LDLW
```
### Initilize Conda
1. From the Windows Start button, open a Anaconda (Miniconda) Prompt
2. <img width="827" height="78" alt="image" src="https://github.com/user-attachments/assets/0cd7a72f-54ba-44b1-91b5-f58628665568" />
3. You should see the command prompt with prompt prefixed with the (base) conda environment name
4. Initialize Conda for your system
```
conda init
```
5. <img width="1159" height="863" alt="image" src="https://github.com/user-attachments/assets/12cd9d81-1803-488f-83b4-d556fb72bd3c" />

6. Close the command prompt

#### Installation Steps
1. Open a new command prompt
2. Clone this repository:
```bash
git clone https://github.com/NVIDIA-AI-Blueprints/3d-object-generation.git

```

3. Run the installer script:
```bash
cd 3d-object-generation
.\install.bat
```

The installation process will:
- Create a Conda virtual environment
- Install all required dependencies
- Set up necessary configurations

After successful installation, you'll see:
```
Installation completed successfully
Press any key to continue . . .
```

## Usage - Manual Steps

### Starting the Application
1. In a new terminal window, start the main application:
```
conda activate trellis
cd 3d-object-generation

python app.py
```
4. Open your browser to the URL shown in the terminal (typically http://127.0.0.1:7860/?__theme=light)

**💡 Recommended**: For the best experience, use the light theme by accessing the application with: `http://127.0.0.1:7860/?__theme=light`

**⚠️ Important Note**: Browser refresh is not supported and may cause the application to crash. In that case, please restart the application instead.

### Managing the Application

To terminate the application and free VRAM:
Open a command prompt at the 3d-object-generation install directory
```
conda activate trellis
cd 3d-object-generation
python terminator.py
```
This will:
- Gracefully terminate the Gradio application
- Free up GPU memory
- Allow you to proceed with other operations which may require VRAM (e.g., Blender)

## Usage - Blender Add On
The CHAT-TO-3D Blender add-on can automatically manage the CHAT-TO-3D services without the need to manually start or stop these services outside of Blender.
### Initial Setup Step
1. Open Blender
2. Open Edit >> Preferences >> Add-Ons
3.<img width="995" height="380" alt="image" src="https://github.com/user-attachments/assets/02c7fb78-52fc-4e36-a4d9-89dbc150a3ef" />
4. Enable CHAT-To-3D and Asset Importer by checking the boxes next to the add on names.
5. Open the CHAT-TO-3D add on preferences and set the CHAT-TO-3D base folder to the chat-to-3d local repository directory.
6. <img width="1492" height="699" alt="image" src="https://github.com/user-attachments/assets/a22521a8-14e4-4890-80e5-9a1167c5a846" />
### Normal Usage
7. In the 3D layout view look for the Add On tabs on the right edge of the viewport, press N if they are not visible
8. <img width="598" height="808" alt="image" src="https://github.com/user-attachments/assets/76e6332a-0945-4b60-a073-03e8bed29e63" />

9. Note: It is recommended to open a system console viewer to monitor the services and any information or errors that may be output.
   a. Blender Menu >> Window >> Toggle System Console
10. Click the Start CHAT-TO-3D button to start the LLM agent, and the Trellis 3D services. (It may take up to 3 minutes for all services to fully load and start)
11. Once all services have successfully started, the service will indicate: READY and the OPEN CHAT-TO-3D UI button will become available
12. <img width="400" height="309" alt="image" src="https://github.com/user-attachments/assets/adfb5d40-b2e1-486a-8230-d003dd04b886" />
13. Click the OPEN CHAT-TO-3D UI button to launch the CHAT-TO-3D interface
    
### Using the Interface
Once the application is running, you can:
1. **Scene Planning**:
   - Describe your desired scene in natural language
   <kbd>
   <img width="1508" height="999" alt="image" src="https://github.com/user-attachments/assets/a65600ee-3507-4bb1-86d9-66d734134f63" />
   </kbd>
2. **Asset Generation**:
   - The LLM will automatically create prompts for suggested items which will be sent to the 2D image generator
     <kbd>
     <img width="1606" height="1352" alt="image" src="https://github.com/user-attachments/assets/55b11095-1b0a-42c5-95e6-7d32f56ed72f" />
     </kbd>
     
   - Each image contains additional controls
     
     <kbd>
     <img width="640" height="370" alt="image" src="https://github.com/user-attachments/assets/6a03b8ab-ee65-40ee-a458-ef64475d7a50" />
     </kbd>
     
     - <img width="86" height="74" alt="image" src="https://github.com/user-attachments/assets/4dd79a46-bb97-46f9-bcba-905606c168bf" /> **Refresh** - Generate a new image based on the existing prompt.
     - <img width="87" height="69" alt="image" src="https://github.com/user-attachments/assets/577d88ee-fc54-47f2-be77-922d0df2fba0" /> **Edit** - Edit the prompt an generate a new image.
     - <img width="77" height="65" alt="image" src="https://github.com/user-attachments/assets/7e740931-29e0-4ff4-af0b-cc080e130c2a" /> **Delete** - Remove the image from the gallery display.
     - <img width="114" height="63" alt="image" src="https://github.com/user-attachments/assets/e125e259-bf10-4e28-97f1-b416c08a168e" /> **Generate 3D** - Generate a 3D object from the image.



<img width="2313" height="125" alt="image" src="https://github.com/user-attachments/assets/8ca38e36-c245-4e06-93e9-5bec518025c9" />
   - Convert all images to 3D Objects (Delete unwanted images before converting to 3D)

2. **Save Objects**:
   - The Export Objects to File allows saving the generated objects to a folder.
   <kbd>
   <img width="2384" height="613" alt="image" src="https://github.com/user-attachments/assets/21a5b43f-7dda-42d9-bbf3-40518a3d3754" />
   </kbd>
   <img width="50%" height="50%" alt="image" src="https://github.com/user-attachments/assets/b302f89a-e282-4a22-ba8a-607cc2a40c82" />

4. **Blender Integration**:
   - Import generated assets directly into Blender
   - <img width="455" height="222" alt="image" src="https://github.com/user-attachments/assets/11b4f471-3fb1-4980-bba6-338886219202" />
   - Use the Asset Importer add-on and select the desired scene folder, and click Import assets
   - <img width="498" height="133" alt="image" src="https://github.com/user-attachments/assets/da88971b-ce42-454c-b3db-3ec8f32d0f68" />
   - Assets are imported and the asset tag is applied, saving the scene to the %userprofile%\Documents\Blender\assets folder will add the imported objects to the Blender asset browser.
   - <img width="1933" height="1234" alt="image" src="https://github.com/user-attachments/assets/f148936c-27da-428c-9d92-5603446deb37" />
   - Continue working with the assets in your 3D workflow
   - Can be used with  [3D Guided Gen AI BP](https://github.com/NVIDIA-AI-Blueprints/3d-guided-genai-rtx)

## Troubleshooting

Common issues and solutions:

1. **Installation Issues**:
   - Ensure all prerequisites are installed correctly
   - Check if Python is in your system PATH
   - Verify Visual Studio Build Tools installation

2. **Runtime Issues**:
   - Make sure both NIM and main application are running
   - Check GPU memory usage
   - Verify all environment variables are set correctly

## Acknowledgments

- [TRELLIS](https://github.com/microsoft/TRELLIS) for the 3D generation capabilities
- [Griptape](https://github.com/griptape-ai/griptape) for the agent framework
- [Gradio](https://github.com/gradio-app/gradio) for the web interface

