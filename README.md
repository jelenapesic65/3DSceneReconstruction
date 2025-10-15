

# README

## Project overview

This project bundles three 3D Scene reconstruction algorithm repositories. Each algorithm is provided as a cloned repository and has a small set of `.py` files that you will replace with updated versions. All algorithms use the **same video file** as input. There are three separate Jupyter notebooks (one per method) that make running each algorithm on the video easy.

This README explains folder layout, how to replace files, how to run the notebooks, dependency suggestions, and troubleshooting tips.

---

## Recommended folder structure

Place everything under a single project folder. Example structure:

```
project-root/      
├── replace_files/
│   └── SplaTAM/
│       ├── nerfcapture.py
│       ├── dataset2config.py
│       └── config.py
├── scripts/
│   ├── 3DGS/         #pip install gsplat/ wheel build
│   ├── 3DGS SSR/      # git clone https://github.com/ThinkXca/3DGS.git --recursive
│   ├── SplaTAM/       # git clone https://github.com/spla-tam/SplaTAM.git
│   ├── gSplat.ipynb
│   ├── 3DGS_SSR.ipynb
│   └── SplaTAM.ipynb
├── data/
│   ├── nagoya.mp4
│   └── nagoya/
│     ├── frame_00.png
│     ├── ...
│     ├── frame_xx.png
│     ├── depth_00.png

│     ├── depth_xx.png 
│     ├── sparse/
│       ├── 0/
│         ├── cameras.bin     #containts parameters for camera calibration 
│         ├── images.bin
│         └── database.db
│   └── nagoya.ply
└── README.md               # this file
```

Notes:
* `replace_files/SplaTAM/` contains the replacement `.py` files you want copied into the cloned repo prior to running.

---

## How to prepare (one-time)

1. Create project root and subfolders as above.
2. Clone each repository inside `scripts/`
3. Put the video file in `project-root/data/video.mp4` (rename if needed and update the notebooks accordingly).
4. Replace modified `.py` files 

---

## Replacing files automatically (recommended)

To avoid manual copying, create a simple script (`apply_replacements.sh`) in `project-root` and run it before running a notebook. Example `apply_replacements.sh`:

```bash
#!/usr/bin/env bash
set -e
ROOT_DIR="$(pwd)"

# Algorithm A
cp "$ROOT_DIR/replace_files/SplaTAM/my_modified_file.py" \
   "$ROOT_DIR/notebooks/SplaTAM/path/to/target/my_original_file.py"

echo "All replacement files copied."
```
The `path/to/target` where the new `my_modified_file.py` should be is specified inside the notebook.

Make the script executable and run:

```bash
chmod +x apply_replacements.sh
./apply_replacements.sh
```

If you prefer Windows, create an analogous PowerShell script using `Copy-Item`.

---

## Notebooks: where to look and how to run

Each notebook is responsible for invoking its corresponding algorithm. Recommended pattern inside each notebook:

1. Set the project root and add the cloned repo to `sys.path` if necessary.
2. Confirm `data/video.mp4` exists.
3. For using data different than provided, the steps to integrate them in the pipeline are following: <br>
3a. Prepare COLMAP processed data and upload as in example data structure - gSplat, 3DGS SSR <br>
3b. Upload video, segment the video into RGB frames and run `LoadSplaTAMData.py` to create depth files (structure as in example).  - SplaTAM
4. Run cells sequentially
5. Outputs will be saved as specified in the original repositories.



---

## Python environment & dependencies

All dependencies and environments are set for each separate algorithm/notebook. By sequentially running the cells, `requirements.txt` installs the dependencies. Additional needed packages are installed.
```bash 
pip install -r requirements.txt
```

## Changes to SplaTAM pipeline

SplaTAM does not support only RGB frames as input; it requires depth frames as well. This is realized by using a MiDAS monocular model to estimate the depth of each frame. The closest pipeline already existing for SplaTAM utilizes the RGB-D format directly from an iPhone. In the `replace_files`, are the files needed to run any video. 
- Process the video in frames
- Estimate depth with `LoadSplaTAMData.py`
- Run the frames through COLMAP structure to get the calibration parameters
- Update fx,fy,cx,cy in config file 


## Troubleshooting tips

* "Module not found" errors: ensure `sys.path` points to the cloned repo or install the repo as a local package with `pip install -e cloned_repos/algorithm`.
* Dependency conflicts: use isolated virtual environments per algorithm if necessary (or Docker).
* Video not found: notebooks assert the path at start — check `data/video.mp4` and the filename.
* Follow additional instructions in each notebook script


---

## Future works 

Building on the adapted SLAM pipeline presented in the SplaTAM work, future efforts could focus on improving occlusion handling, inspired by techniques used in the 3DGS SSR framework. Current occlusions are detected with the Segment Anything Model (SAM), which could be replaced with more efficient approaches, such as sparse optical flow or frame differencing. No changes would be made to the format of the provided data (segmented frames + depth frames), but there is room for improvement in the depth estimation, such as using LiDAR-rendered depth or a similar approach.

## Acknowledgements

This repository is built on works provided by [gSplat](https://github.com/nerfstudio-project/gsplat), [3D Gaussian Splatting Street Scene Reconstruction](https://github.com/ThinkXca/3DGS/tree/main) and [SplaTAM](https://github.com/spla-tam/SplaTAM/tree/main)
