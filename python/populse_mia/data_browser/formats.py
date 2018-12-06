##########################################################################
# Populse_mia - Copyright (C) IRMaGe/CEA, 2018
# Distributed under the terms of the CeCILL license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL_V2.1-en.html
# for details.
##########################################################################

try:
    from soma import aims
except ImportError:
    # no pyaims, oh, well.
    aims = None
    pass

try:
    import nibabel as nib
except ImportError:
    # no nibabel
    nib = None
    pass


def aims_image_formats():
    if aims is None:
        return set()
    vox_types = aims.IOObjectTypesDictionary.objectsTypes()['Volume']
    formats = set()
    for voxtype in vox_types:
        formats.update(aims.IOObjectTypesDictionary.formats('Volume', voxtype))
    # soma-io inspect methods are not exported to python yet
    formats.update(['DICOM', 'GIS', 'NIFTI-1', 'NIFTI-2']) # + OpenSlide
    if '' in formats:
        # empty format may interfere
        formats.remove('')
    return formats


def aims_file_extensions(formats):
    if aims is None:
        return set()
    exts = set()
    for format in formats:
        exts.update(aims.Finder.extensions(format))
        exts.update(aims.soma.DataSourceInfoLoader.extensions(format))
    return exts


def nibabel_image_formats():
    if nib is None:
        return set()
    # I don't know how to inspect that
    return set(['NIFTI-1'])


def nibabel_file_extensions(formats):
    if nib is None:
        return set()
    # I don't know how to inspect that
    return set(['nii', 'nii.gz'])

_all_extensions_ = None

def supported_image_extensions():
    global _all_extensions_
    if _all_extensions_ is not None:
        return _all_extensions_
    exts = aims_file_extensions(aims_image_formats())
    exts.update(nibabel_file_extensions(nibabel_image_formats()))
    _all_extensions_ = exts
    return _all_extensions_

