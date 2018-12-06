##########################################################################
# Populse_mia - Copyright (C) IRMaGe/CEA, 2018
# Distributed under the terms of the CeCILL license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL_V2.1-en.html
# for details.
##########################################################################

import os

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
    ''' Returns all supported image files extensions, using aims or nibabel
    when they are available.
    '''
    global _all_extensions_
    if _all_extensions_ is not None:
        return _all_extensions_
    exts = aims_file_extensions(aims_image_formats())
    exts.update(nibabel_file_extensions(nibabel_image_formats()))
    _all_extensions_ = exts
    return _all_extensions_


def get_format(path):
    ''' determine the format of the file path, and return its format and
    reader module ('aims' or 'nibabel')

    Returns
    -------
    format_info: tuple
        (format, reader)
    '''
    if aims:
        finder = aims.Finder()
        if finder.check(path):
            # file is recognized by Aims / Soma-IO
            return (finder.format(), 'aims')
    for ext in supported_image_extensions():
        if path.endswith('.' + ext):
            if ext in nibabel_file_extensions():
                # should be supported by nibabel, use a single file
                # (just because I don't know how to get more details)
                if ext in ('nii', 'nii.gz'):
                    return ("NIFTI-1", 'nibabel');
    # format is not recognized
    return None


def files_for_data(path):
    ''' Try to determine all files making up the selected data.
    path is one of the needed files, but there may be others
    (ex: .img/.hdr couple)
    '''
    format_info = get_format(path)
    if format_info is None:
        return None
    format, reader = format_info
    if reader == 'aims':
        exts = aims.soma.DataSourceInfoLoader.extensions(format)
        if not exts:
            exts = aims.Finder.extensions(format)
        for ext in exts:
            if path.endswith('.' + ext):
                break
        base_path = path[:-len(ext)-1]
        paths = [base_path + '.' + ext for ext in exts
                 if os.path.exists(base_path + '.' + ext)]
        paths += [p + '.minf' for p in paths if os.path.exists(p + '.minf')]
        return paths
    if reader == 'nibabel':
        # I don't know how to do this right now
        return [path]

