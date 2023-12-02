#!/usr/bin/env python3
"""
This script performs some preliminary actions to the UCSD fMRI datacollected at UCSD. The

import os
import sys

import numpy as np
import nibabel as nib
import json
import logging

def check_func_folder(vetsaid, bids_dir, log):
    """
    Checks if the func and fmap folders exist for the given subject.
    """
    func_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'func')
    fmap_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02','fmap')
    if not os.path.isdir(func_dir):
        log.error(f'No func folder found for subject {vetsaid}')
        return False
    if not os.path.isdir(fmap_dir):
        log.error(f'No fmap folder found for subject {vetsaid}')
        return False
    return True

def get_site(func_file, log):
    """ 
    Checks dwi json file to determine site of data collection based on manufacturer model.
    BU data was collected on a Siemens TrioTim.
    UCSD data was colected on a GE DISCOVERY MR750. 
    """
    func_json_file = func_file.replace('.nii.gz', '.json')
    with open(func_json_file, 'r') as f:
        func_json = json.load(f)
    func_model = func_json["ManufacturersModelName"]
    if func_model == "TrioTim":
        func_site = "BU"
    elif func_model == "DISCOVERY MR750":
        func_site = "UCSD"
    else:
        log.error(f'Error in processing {func_file}. Unknown manufacturer model: {func_model}')
        sys.exit(1)
    return func_site

def get_nvols(func_file):
    """Get the number of volumes from the func file"""
    img = nib.load(func_file)
    data = img.get_fdata()
    return data.shape[3]

def check_func_data(func_file, log):
    """
    Checks that the functional run was acquired at UCSD and has the correct number of volumes.
    It should have 100 volumes.
    """
    # Check that the functional run was acquired at UCSD
    func_site = get_site(func_file, log)
    if func_site != "UCSD":
        log.error(f'Error in processing {func_file}. Functional run was acquired at acquired at {func_site}, not UCSD.')
        return False
    # Check that there are 100 volumes
    func_nvols = get_nvols(func_file)
    if func_nvols != 100:
        log.error(f'Error in processing {func_file}. Functional run has {func_nvols} volumes, not 100.')
        return False
    return True

def split_func_run(func_file, log): 
    """
    Split the data into separate files for each phase encoding direction. Odd numbered volumes (1-based) 
    are A->P, even numbered volumes are P->A. Save as separate nifti files in the same directory as the original file.
    """
    # Load the functional data
    img = nib.load(func_file)
    # Get the image data
    data = img.get_fdata()
    # Get the indices of the AP and PA timepoints
    indices_AP = np.arange(0, data.shape[-1], 2)
    indices_PA = np.arange(1, data.shape[-1], 2)
    # Extract the desired timepoints for each phase encoding direction
    extracted_data_AP = data[:, :, :, indices_AP]
    extracted_data_PA = data[:, :, :, indices_PA]
    # Flip data along the y-axis for the AP data 
    # so that it is in the same orientation as the PA data
    extracted_data_AP = np.flip(extracted_data_AP, axis=1)
    # Save the extracted data
    func_file_AP = func_file.replace('_bold.nii.gz', '_dir-AP_bold.nii.gz')
    func_file_PA = func_file.replace('_bold.nii.gz', '_dir-PA_bold.nii.gz')
    nib.save(nib.Nifti1Image(extracted_data_AP, img.affine, img.header), func_file_AP)
    nib.save(nib.Nifti1Image(extracted_data_PA, img.affine, img.header), func_file_PA)
    return func_file_AP, func_file_PA

def merge_func_files(func_file_AP, func_file_PA, log):
    """
    Merge the distortion corrected AP and PA data back together in an interleaved order. Odd numbered volumes (1-based) 
    should be A->P, even numbered volumes should be P->A. Save as a single nifti file in the same directory as the original 
    files with the dir parameter of the filename removed.
    """
    # Load the functional data
    img_AP = nib.load(func_file_AP)
    img_PA = nib.load(func_file_PA)
    # Get the image data
    data_AP = img_AP.get_fdata()
    data_PA = img_PA.get_fdata()
    # Merge the data back together
    merged_data = np.empty((data_AP.shape[0], data_AP.shape[1], data_AP.shape[2], data_AP.shape[3] + data_PA.shape[3]))
    merged_data[:, :, :, ::2] = data_AP
    merged_data[:, :, :, 1::2] = data_PA
    # Save the merged data
    merged_func_file = func_file_AP.replace('_dir-AP', '')
    nib.save(nib.Nifti1Image(merged_data, img_AP.affine, img_AP.header), merged_func_file)
    return merged_func_file

def create_split_func_json(func_file_AP, func_file_PA, func_json_file, log):
    """
    Create json sidecar for each split file. Use the json sidecar from the original file as a template.
    Set phase encoding direction of AP file to j- and PA file to j, matches the phase encoding direction
    of the fieldmaps.
    """
    # Load the original json file
    with open(func_json_file, 'r') as f:
        func_json = json.load(f)
    func_json_AP = func_json.copy()
    func_json_PA = func_json.copy()
    # Set phase encoding direction of AP file to j- and PA file to j, matches the phase encoding direction
    # of the fieldmaps.
    func_json_AP['PhaseEncodingDirection'] = 'j-'
    func_json_PA['PhaseEncodingDirection'] = 'j'
    # Save the edited json files
    func_json_file_AP = func_file_AP.replace('.nii.gz', '.json')
    func_json_file_PA = func_file_PA.replace('.nii.gz', '.json')
    with open(func_json_file_AP, 'w') as f:
        json.dump(func_json_AP, f, indent=4)
    with open(func_json_file_PA, 'w') as f:
        json.dump(func_json_PA, f, indent=4)
    return func_json_file_AP, func_json_file_PA

def edit_bold_json(func_json_file, log):
    """
    Edits json sidecar of func file. 
    1. Removes the phase encoding direction from the func json file. This is necessary because the
    phase encoding direction is not the same for all volumes in the file and prevents the json file
    from being used to determine the phase encoding direction automatically. Users will need to
    intervene and resolve the issue manually.
    2. Adds TaskName field to the func json file.
    """
    # Remove the phase encoding direction from the func json file
    with open(func_json_file, 'r') as f:
        func_json = json.load(f)
    func_json.pop('PhaseEncodingDirection')
    # Add TaskName field to the func json file
    func_json['TaskName'] = 'rest'
    # Save the edited json file
    with open(func_json_file, 'w') as f:
        json.dump(func_json, f, indent=4)
    return func_json_file

def process_func_run(vetsaid, bids_dir, log):
    """
    Processes the functional run for the given subject.
    """
    # Get the path to the functional run
    func_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'func')
    func_file = os.path.join(func_dir, f'sub-{vetsaid}_ses-02_task-rest_bold.nii.gz')
    # Check that func data was acquired at UCSD and has correct number of volumes
    func_check_correct = check_func_data(func_file, log)
    if not func_check_correct:
        return
    # Split the functional run into separate files for each phase encoding direction
    func_file_AP, func_file_PA = split_func_run(func_file, log)
    # Create json sidecar for each split file
    func_json_file_AP, func_json_file_PA = create_split_func_json(func_file_AP, func_file_PA, func_file.replace('.nii.gz', '.json'), log)
    # Merge the data back together
    merged_func_file = merge_func_files(func_file_AP, func_file_PA, log)
    # Remove phase encoding direction from func json files
    corrected_func_json = edit_bold_json(func_file.replace('.nii.gz', '.json'), log)
    # Return the merged func file and the corrected func json file    
    return merged_func_file, corrected_func_json

def main(bids_dir, subject_list_file):
    # Read the subject list file
    with open(subject_list_file, 'r') as f:
        subject_list = f.read().splitlines()

    # Set up logging
    log_file = os.path.join(bids_dir, 'conversion.log')
    logging.basicConfig(filename=log_file, level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
    log = logging.getLogger()

    # Process each subject in the list
    for vetsaid in subject_list:
        log.info(f'Processing subject {vetsaid}')

        # Check if the func and fmap folders exist
        if not check_func_folder(vetsaid, bids_dir, log):
            continue

        # Process each functional run
        merged_func_file, corrected_func_json = process_func_run(vetsaid, bids_dir, log)

if __name__ == '__main__':
    
    # Check if the correct number of arguments was provided
    if len(sys.argv) != 3:
        print('Usage: python 4_wave2_fmri-sdc-ucsd.py <bids_dir> <subject_list_file>')
        sys.exit(1)

    # Get the path to the BIDS data and the subject list file from the command line arguments
    bids_dir = sys.argv[1]
    subject_list_file = sys.argv[2]

    # Run the main function
    main(bids_dir, subject_list_file)