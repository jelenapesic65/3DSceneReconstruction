'''
Script to create a dataset from RGB and depth frames for SplaTAM.
This replaces the original NeRFCapture iOS App data capture.
'''
#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
from pathlib import Path
import json
import numpy as np
import cv2
from importlib.machinery import SourceFileLoader

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="./configs/iphone/nerfcapture.py", type=str, help="Path to config file.")
    return parser.parse_args()


def create_dataset_from_files(save_path: Path, overwrite: bool, data_config: dict):
    """
    Create dataset from RGB and depth files
    """
    if save_path.exists():
        if overwrite:
            # Prompt user to confirm deletion
            if (input(f"warning! folder '{save_path}' will be deleted/replaced. continue? (Y/n)").lower().strip()+"y")[:1] != "y":
                sys.exit(1)
            shutil.rmtree(save_path)
        else:
            print(f"save_path {save_path} already exists")
            sys.exit(1)

    # Create directories
    images_dir = save_path.joinpath("rgb")
    depth_dir = save_path.joinpath("depth")
    save_path.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    depth_dir.mkdir(exist_ok=True)

    # Get data configuration
    data_dir = Path(data_config['data_dir'])
    num_frames = data_config['num_frames']
    depth_scale = data_config.get('depth_scale', 1000.0)
    
    # Camera intrinsics (you may need to adjust these based on your camera)
    fl_x = data_config.get('fl_x',  1425.20648)  # focal length x
    fl_y = data_config.get('fl_y', 1514.51572)  # focal length y
    cx = data_config.get('cx', 960.0)      # principal point x
    cy = data_config.get('cy', 540.0)      # principal point y
    width = data_config.get('width', 1920)  # image width
    height = data_config.get('height', 1080) # image height

    print(f"Creating dataset from {num_frames} frames...")

    manifest = {
        "fl_x": fl_x,
        "fl_y": fl_y,
        "cx": cx,
        "cy": cy,
        "w": width,
        "h": height,
        "integer_depth_scale": float(depth_scale)/65535.0,
        "frames": []
    }

    for frame_idx in range(num_frames):
        print(f"Processing frame {frame_idx + 1}/{num_frames}")

        # Load RGB image
        rgb_path = data_dir / data_config['rgb_format'].format(frame_idx)
        if not rgb_path.exists():
            print(f"RGB file {rgb_path} not found, skipping frame {frame_idx}")
            continue
            
        # Load and process RGB
        if rgb_path.suffix.lower() in ['.npy']:
            rgb_data = np.load(rgb_path)
            # Assume RGB data is in 0-255 range or 0-1 range
            if rgb_data.max() <= 1.0:
                rgb_data = (rgb_data * 255).astype(np.uint8)
            else:
                rgb_data = rgb_data.astype(np.uint8)
        else:  # Assume image file
            rgb_data = cv2.imread(str(rgb_path))
            rgb_data = cv2.cvtColor(rgb_data, cv2.COLOR_BGR2RGB)
        
        # Resize if necessary
        if rgb_data.shape[:2] != (height, width):
            rgb_data = cv2.resize(rgb_data, (width, height))
        
        # Save RGB
        rgb_save_path = images_dir / f"{frame_idx}.png"
        cv2.imwrite(str(rgb_save_path), cv2.cvtColor(rgb_data, cv2.COLOR_RGB2BGR))

        # Load depth
        depth_path = data_dir / data_config['depth_format'].format(frame_idx)
        depth = None
        if depth_path.exists():
            if depth_path.suffix.lower() in ['.npy']:
                depth_data = np.load(depth_path)
            else:  # Assume image file
                depth_data = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
            
            # Convert depth to meters if needed
            if data_config.get('depth_in_millimeters', False):
                depth_data = depth_data / 1000.0  # Convert mm to meters
            
            # Convert to uint16 for storage
            depth_uint16 = (depth_data * depth_scale).astype(np.uint16)
            
            # Resize if necessary
            if depth_uint16.shape[:2] != (height, width):
                depth_uint16 = cv2.resize(depth_uint16, (width, height), interpolation=cv2.INTER_NEAREST)
            
            # Save depth
            depth_save_path = depth_dir / f"{frame_idx}.png"
            cv2.imwrite(str(depth_save_path), depth_uint16)
            depth = depth_uint16

        # Create transform matrix (identity as placeholder - you may need to load actual poses)
        # If you have pose files, load them here
        transform_matrix = np.eye(4).tolist()
        
        # Try to load pose if available
        pose_path = data_dir / data_config.get('pose_format', '').format(frame_idx)
        if data_config.get('pose_format') and pose_path.exists():
            try:
                if pose_path.suffix.lower() in ['.npy']:
                    pose_data = np.load(pose_path)
                    transform_matrix = pose_data.tolist()
                else:  # Assume text file or other format
                    # You may need to adjust this based on your pose file format
                    pose_data = np.loadtxt(pose_path)
                    transform_matrix = pose_data.tolist()
            except Exception as e:
                print(f"Error loading pose from {pose_path}: {e}")
                print("Using identity matrix as fallback")

        frame_data = {
            "transform_matrix": transform_matrix,
            "file_path": f"rgb/{frame_idx}.png",
            "fl_x": fl_x,
            "fl_y": fl_y,
            "cx": cx,
            "cy": cy,
            "w": width,
            "h": height
        }

        if depth is not None:
            frame_data["depth_path"] = f"depth/{frame_idx}.png"

        manifest["frames"].append(frame_data)

    print("Saving manifest...")
    # Write manifest as json
    manifest_json = json.dumps(manifest, indent=4)
    with open(save_path.joinpath("transforms.json"), "w") as f:
        f.write(manifest_json)
    print(f"Dataset created successfully at {save_path}")


if __name__ == "__main__":
    args = parse_args()

    # Load config
    experiment = SourceFileLoader(
        os.path.basename(args.config), args.config
    ).load_module()

    config = experiment.config
    
    # Call the dataset creation function
    create_dataset_from_files(
        Path(config['workdir']), 
        config['overwrite'], 
        config['data_config']
    )