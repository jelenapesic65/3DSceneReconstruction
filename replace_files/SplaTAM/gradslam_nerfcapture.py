import glob
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import torch
from natsort import natsorted

from .basedataset import GradSLAMDataset


def create_filepath_index_mapping(frames):
    return {frame["file_path"]: index for index, frame in enumerate(frames)}


class NeRFCaptureDataset(GradSLAMDataset):
    def __init__(
        self,
        basedir,
        sequence,
        stride: Optional[int] = None,
        start: Optional[int] = 0,
        end: Optional[int] = -1,
        desired_height: Optional[int] = 1440,
        desired_width: Optional[int] = 1920,
        load_embeddings: Optional[bool] = False,
        embedding_dir: Optional[str] = "embeddings",
        embedding_dim: Optional[int] = 512,
        **kwargs,
    ):
        self.input_folder = os.path.join(basedir, sequence)
        config_dict = {}
        config_dict["dataset_name"] = "nerfcapture"
        self.pose_path = None
        
        # Load NeRFStudio format camera & poses data
        self.cams_metadata = self.load_cams_metadata()
        self.frames_metadata = self.cams_metadata["frames"]
        self.filepath_index_mapping = create_filepath_index_mapping(self.frames_metadata)

        # Load RGB & Depth filepaths
        # CHANGED: Use the frames metadata to get image paths instead of directory listing
        self.image_names = [frame["file_path"] for frame in self.frames_metadata]
        
        # NEW: Sort frames by their index to ensure proper ordering
        self.image_names = natsorted(self.image_names, key=lambda x: int(Path(x).stem))

        # Init Intrinsics
        config_dict["camera_params"] = {}
        
        # CHANGED: Use integer_depth_scale from metadata if available, otherwise fallback
        if "integer_depth_scale" in self.cams_metadata:
            # Convert from the scale used in transforms.json to png_depth_scale
            # integer_depth_scale = depth_scale / 65535.0
            # So png_depth_scale = 1.0 / integer_depth_scale
            integer_depth_scale = self.cams_metadata["integer_depth_scale"]
            config_dict["camera_params"]["png_depth_scale"] = 1.0 / integer_depth_scale
        else:
            # Fallback to original value
            config_dict["camera_params"]["png_depth_scale"] = 6553.5
            
        config_dict["camera_params"]["image_height"] = self.cams_metadata["h"]
        config_dict["camera_params"]["image_width"] = self.cams_metadata["w"]
        config_dict["camera_params"]["fx"] = self.cams_metadata["fl_x"]
        config_dict["camera_params"]["fy"] = self.cams_metadata["fl_y"]
        config_dict["camera_params"]["cx"] = self.cams_metadata["cx"]
        config_dict["camera_params"]["cy"] = self.cams_metadata["cy"]

        super().__init__(
            config_dict,
            stride=stride,
            start=start,
            end=end,
            desired_height=desired_height,
            desired_width=desired_width,
            load_embeddings=load_embeddings,
            embedding_dir=embedding_dir,
            embedding_dim=embedding_dim,
            **kwargs,
        ) 

    def load_cams_metadata(self):
        cams_metadata_path = f"{self.input_folder}/transforms.json"
        cams_metadata = json.load(open(cams_metadata_path, "r"))
        return cams_metadata
    
    def get_filepaths(self):
        base_path = f"{self.input_folder}"
        color_paths = []
        depth_paths = []
        self.tmp_poses = []
        P = torch.tensor(
            [
                [1, 0, 0, 0],
                [0, -1, 0, 0],
                [0, 0, -1, 0],
                [0, 0, 0, 1]
            ]
        ).float()
        
        # CHANGED: Iterate through frames metadata instead of image_names
        for i, frame_metadata in enumerate(self.frames_metadata):
            # Get path of image and depth from frame metadata
            color_path = f"{base_path}/{frame_metadata['file_path']}"
            color_paths.append(color_path)
            
            # NEW: Check if depth path exists in metadata
            if "depth_path" in frame_metadata:
                depth_path = f"{base_path}/{frame_metadata['depth_path']}"
            else:
                # Fallback: try to construct depth path from color path
                depth_path = f"{base_path}/{frame_metadata['file_path'].replace('rgb', 'depth')}"
            depth_paths.append(depth_path)
            
            # Get pose of image in GradSLAM format
            c2w = torch.from_numpy(np.array(frame_metadata["transform_matrix"])).float()
            _pose = P @ c2w @ P.T
            self.tmp_poses.append(_pose)
            
        embedding_paths = None
        if self.load_embeddings:
            embedding_paths = natsorted(glob.glob(f"{base_path}/{self.embedding_dir}/*.pt"))
        return color_paths, depth_paths, embedding_paths

    def load_poses(self):
        return self.tmp_poses

    def read_embedding_from_file(self, embedding_file_path):
        print(embedding_file_path)
        embedding = torch.load(embedding_file_path, map_location="cpu")
        return embedding.permute(0, 2, 3, 1)  # (1, H, W, embedding_dim)