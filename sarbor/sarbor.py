# -*- coding: utf-8 -*-
import numpy as np
import logging

from .config import Config
from .skeletons import Skeleton


"""Main module."""


def _process_skeleton(config: Config) -> Skeleton:

    skel = Skeleton(config)

    nodes = config.skeleton.nodes
    skel.input_nid_pid_x_y_z(nodes)

    if config.skeleton.strahler_filter and False:
        skel.filter_nodes_by_strahler(
            config.skeleton.min_strahler, config.skeleton.max_strahler
        )
    if config.skeleton.resample:
        processed_skel, new_nid_to_orig_map = skel.resample_segments()
    else:
        processed_skel, new_nid_to_orig_map = skel, {}
    return processed_skel


def _process_results(skel: Skeleton, results) -> Skeleton:
    for node in skel.get_nodes():
        try:
            data = results[node.key]
            if data is not None:
                skel.fill(node.key, data.astype(np.uint8))
                logging.debug(
                    "Node {} had data with max value {}!".format(node.key, data.max())
                )
            else:
                logging.info("Node {} had no data!".format(node.key))
        except KeyError:
            logging.debug("No data for node {}!".format(node.key))
        except TypeError:
            logging.debug("Node {} data was None".format(node.key))
    return skel


def query_diluvian(config, model_weights_file, model_training_config, model_job_config, volume_file):
    from .diluvian_source import DiluvianSource
    from diluvian.config import CONFIG

    volumes = load_volumes([volume_file])
    CONFIG.from_toml(model_training_config, model_job_config)

    processed_skel = _process_skeleton(config)

    diluvian_source = DiluvianSource(volumes, CONFIG, model_weights_file)

    results = diluvian_source.segment_skeleton(processed_skel)

    processed_skel = _process_results(processed_skel, results)

    processed_skel.save_data_for_CATMAID()

    return None


def query_watershed(config):
    from .watershed_source import JanSegmentationSource

    processed_skel = _process_skeleton(config)

    jans_segmentations = JanSegmentationSource(
        sensitives_file="/groups/cardona/home/pattonw/Code/Scripts/error_detection/sensitives.json"
    )

    results = jans_segmentations.segment_skeleton(processed_skel)

    processed_skel = _process_results(processed_skel, results)

    processed_skel.save_data_for_CATMAID()

def query_test_data(config):
    from .test_source import TestSource

    processed_skel = _process_skeleton(config)

    test_source = TestSource()

    results = test_source.segment_skeleton(processed_skel)

    processed_skel = _process_results(processed_skel, results)

    processed_skel.save_data_for_CATMAID()
    

def load_volumes(volume_files, in_memory=False, name_regex=None):
    """Load HDF5 volumes specified in a TOML description file.

    Parameters
    ----------
    volume_file : list of str
        Filenames of the TOML volume descriptions to load.
    in_memory : bool
        If true, the entire dataset is read into an in-memory volume.

    Returns
    -------
    diluvian.volumes.Volume
    """
    # Late import to prevent loading large modules for short CLI commands.
    from diluvian.volumes import HDF5Volume
    from diluvian.volumes import ImageStackVolume
    from diluvian.volumes import N5Volume

    print('Loading volumes...')
    if volume_files:
        volumes = {}
        for volume_file in volume_files:
            volumes.update(HDF5Volume.from_toml(volume_file))
            volumes.update(ImageStackVolume.from_toml(volume_file))
            volumes.update(N5Volume.from_toml(volume_file))
    else:
        volumes = HDF5Volume.from_toml(os.path.join(os.path.dirname(__file__), 'conf', 'cremi_datasets.toml'))

    if name_regex is not None:
        name_regex = re.compile(name_regex)
        volumes = {k: v for k, v in six.iteritems(volumes) if name_regex.match(k)}

    if in_memory:
        print('Copying volumes to memory...')
        volumes = {k: v.to_memory_volume() for k, v in six.iteritems(volumes)}

    print('Done.')
    return volumes