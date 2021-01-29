import numpy as np
from scipy import spatial
import cloudvolume
from . import utils


def refine_vertices(
    vertices,
    l2dict_reversed,
    cv,
    refine_inds='all',
    scale_chunk_index=True,
    convert_missing=False,
    return_missing_ids=True,
):
    """Refine vertices in chunk index space by converting to euclidean space using a combination of mesh downloading and simple chunk mapping.

    Parameters
    ----------
    vertices : array
        Nx3 array of vertex locations in chunk index space
    l2dict_reversed : dict or array
        N-length mapping from vertex index to uint64 level 2 id.
    cv : cloudvolume.CloudVolume
        CloudVolume associated with the chunkedgraph instance
    refine_inds : array, string, or None, optional
        Array of indices to refine via mesh download and recentering, None, or 'all'. If 'all', does all vertices. By default 'all'.
    scale_chunk_index : bool, optional
        If True, moves chunk indices to the euclidean space (the center of the chunk) if not refined. by default True.
    convert_missing : bool, optional
        If True, vertices with missing meshes are converted to the center of their chunk. Otherwise, they are given nans. By default, False.
    return_missing_ids : bool, optional
        If True, returns a list of level 2 ids for which meshes were not found, by default True

    Returns
    -------
    new_vertices : array
        Nx3 array of remapped vertex locations in euclidean space
    missing_ids : array, optional
        List of level 2 ids without meshes. Only returned if return_missing_ids is True.
    """
    vertices = vertices.copy()
    if refine_inds == 'all':
        refine_inds = np.arange(0, len(vertices))

    if refine_inds is not None:
        l2ids = [l2dict_reversed[k] for k in refine_inds]
        pt_locs, missing_ids = lvl2_fragment_locs(
            l2ids, cv, return_missing=True)

        if convert_missing:
            missing_inds = np.any(np.isnan(pt_locs), axis=1)
            vertices[refine_inds[~missing_inds]] = pt_locs[~missing_inds]
        else:
            missing_inds = np.full(len(pt_locs), False)
            vertices[refine_inds] = pt_locs

    if scale_chunk_index and len(refine_inds) != len(vertices):
        # Move unrefined vertices to center of chunks
        other_inds = np.full(len(vertices), True)
        if refine_inds is not None:
            other_inds[refine_inds[~missing_inds]] = False
        vertices[other_inds] = (
            utils.chunk_to_nm(vertices[other_inds], cv) +
            utils.chunk_dims(cv) // 2
        )
    if return_missing_ids:
        return vertices, missing_ids
    else:
        return vertices


def get_closest_lvl2_chunk(
    point,
    root_id,
    client,
    cv=None,
    voxel_resolution=[4, 4, 40],
    radius=200,
    return_point=False,
):
    """Get the closest level 2 chunk on a root id

    Parameters
    ----------
    point : array-like
        Point in voxel space.
    root_id : int
        Root id of the object
    client : FrameworkClient
        Framework client to access data
    cv : cloudvolume.CloudVolume or None, optional
        Cloudvolume associated with the dataset. One is created if None.
    voxel_resolution : list, optional
        Point resolution to map between point resolution and mesh resolution, by default [4, 4, 40]
    radius : int, optional
        Max distance to look for a nearby supervoxel. Optional, default is 200.
    return_point : bool, optional
        If True, returns the closest point in addition to the level 2 id. Optional, default is False.

    Returns
    -------
    level2_id : int
        Level 2 id of the object nearest to the point specified.
    close_point : array, optional
        Closest point inside the object to the specified point. Only returned if return_point is True.
    """
    if cv is None:
        cv = cloudvolume.CloudVolume(
            client.info.segmentation_source(),
            use_https=True,
            bounded=False,
            progress=False,
        )

    point = point * np.array(voxel_resolution)
    # Get the closest adjacent point for the root id within the radius.
    mip_scaling = np.array(cv.mip_resolution(0))

    pt = np.array(point) // mip_scaling
    offset = radius // mip_scaling
    lx = np.array(pt) - offset
    ux = np.array(pt) + offset
    bbox = cloudvolume.Bbox(lx, ux)
    vol = cv.download(bbox, segids=[root_id])
    vol = np.squeeze(vol)
    if not bool(np.any(vol > 0)):
        raise ValueError("No point of the root id is near the specified point")

    ctr = offset * point * voxel_resolution
    xyz = np.vstack(np.where(vol > 0)).T
    xyz_nm = xyz * mip_scaling * voxel_resolution

    ind = np.argmin(np.linalg.norm(xyz_nm - ctr, axis=1))
    closest_pt = vol.bounds.minpt + xyz[ind]

    # Look up the level 2 supervoxel for that id.
    closest_sv = int(cv.download_point(closest_pt, size=1))
    lvl2_id = client.chunkedgraph.get_root_id(closest_sv, level2=True)

    if return_point:
        return lvl2_id, closest_pt * mip_scaling * voxel_resolution
    else:
        return lvl2_id


def lvl2_fragment_locs(l2_ids, cv, return_missing=True):
    """ Look up representitive location for a list of level 2 ids.

    The representitive point for a mesh is the mesh vertex nearest to the
    centroid of the mesh fragment.

    Parameters
    ----------
    l2_ids : list-like
        List of N level 2 ids
    cv : cloudvolume.CloudVolume
        Associated cloudvolume object
    return_missing : bool, optional
        If True, returns ids of missing meshes. Default is True

    Returns
    -------
    l2means : np.array   
        Nx3 list of point locations. Missing mesh fragments get a nan for each component.
    missing_ids : np.array
        List of level 2 ids that were not found.
    """
    l2meshes = cv.mesh.get_meshes_on_bypass(l2_ids, allow_missing=True)
    l2means = []
    missing_ids = []
    for l2id in l2_ids:
        try:
            l2m = np.mean(l2meshes[l2id].vertices, axis=0)
            _, ii = spatial.cKDTree(l2meshes[l2id].vertices).query(l2m)
            l2means.append(l2meshes[l2id].vertices[ii])
        except:
            missing_ids.append(l2id)
            l2means.append(np.array([np.nan, np.nan, np.nan]))
    if len(l2means) > 0:
        l2means = np.vstack(l2means)
    else:
        l2means = np.empty((0, 3), dtype=float)
    return l2means, missing_ids
