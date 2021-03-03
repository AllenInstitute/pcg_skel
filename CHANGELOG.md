# Changelog

This project is under active development and, while breaking changes will be avoided where possible, no promises are made until version 1 is released.

## [0.0.5] - 2021-03-03

### Fixed

* The segmentation fallback method has been made more robust to level 2 chunk ids with very small supervoxels.

* `nan_rounds` set to `None` is more correctly handled and the warning actually checks to see if any nans are left.

## [0.0.4] - 2021-02-24

### Added

* `pcg_meshwork` takes the same `save_to_cache` argument as `pcg_skeleton`.

### Changed

* Voxel resolution is always inferred from the mip-0 resolution of the segmentation cloudvolume.
Note that this means that if the segmentation mip-0 resolution is not the same as the normal working resolution, `root_point_resolution` must be explicitly set.

* The package explicitly uses the authentication token set in the client to instantiate cloudvolume objects, enabling it to work with non-default tokens.

* `pcg_meshwork` now sets the point column for synapses for better integration with meshwork features.

### Fixed

* Fixed bug in `get_level2_synapses` prevented `post=True`, `pre=False` situation from working correctly.

* Improved default parameters in call cases where a CloudVolume instance is initialized.

## [0.0.3] - 2021-02-13

### Changed

* Choose your mip level when falling back to segmentation.
This saves a bit of time on the download, and if the level-2 object has been downsampled out of existence at this mip level, it will rerun at mip-0 where it must exist.

* More aggressive handling of segmentation memory use. Requires cloudvolume renumber mode.

## [0.0.2] - 2021-02-13

### Added

* *Localizing level 2 ids via segmentation if the mesh does not exist.*
There are both expected and unexpected an unexpected reasons for mesh fragments not to exist.
Unfortunately, this situation seems to crop up for virtually every neuron.
However, all level 2 ids must be associated with at least one supervoxel, so we can use the segmentation itself to do the same operation.
This is a bit slower, since we have to download the whole chunk, but it's a robust fallback that can be used when no mesh is found.
This is now used by default, but can be turned off with `segmentation_fallback=False` on any of the functions that use level 2 positions.

* *Improved parallelization.*
To speed up the slow segmentation fallback, parallelization occurs in more processing steps.

## [0.0.1] - 2021-02-11

### Initial release
