#!/usr/bin/env python3

"""
This script corrects the dwi data for the VETSA1 UCSD and BU datasets. Data from the two sites
were collected with two scans in opposite phase encoding directions in an integrated sequence.
The first scan was collected in the AP direction and the second scan was collected in the PA. 
Each scan starts with 5 b0 volumes followed by 30 diffusion weighted volumes. Therefore, the
integrated sequence contains 70 total volumes. This script:

- Splits the dwi file into two files (one for each phase encoding direction)
- Splits the bvals and bvecs files into two files (one for each phase encoding direction)
- Creates json file for the new PA dwi file
- Edits the json file for the PA epi file to include the correct IntendedFor field
- Saves out the b0 volumes from each phase encoding direction as epi files in the fmap folder
- Creates json files for the fmap files
"""

import os
import sys
import shutil
import numpy as np
import nibabel as nib
from glob import glob
import json
import os

def check_dwi_folder(vetsaid, bids_dir):
    """Check if the dwi folder exists"""
    dwi_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-01', 'dwi')
    if not os.path.isdir(dwi_dir):
        print('No dwi folder found')
        return False
    return True


def check_single_shell_data(vetsaid, bids_dir):
    """Check if the single-shell data exists"""
    single_dwi_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-01', 'dwi', f'sub-{vetsaid}_ses-01_dir-AP_dwi.nii.gz')
    if not os.path.isfile(single_dwi_file):
        print('No single-shell data found')
        return False
    return True


def get_site(vetsaid, bids_dir):
    """ 
    Checks dwi json file to determine site of data collection based on manufacturer model.
    BU data was collected on a Siemens TrioTim.
    UCSD data was colected on a GE DISCOVERY MR750. 
    """
    dwi_json_file = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-01', 'dwi', f'sub-{vetsaid}_ses-01_dir-AP_dwi.json')
    with open(dwi_json_file, 'r') as f:
        dwi_json = json.load(f)
    dwi_model = dwi_json["ManufacturersModelName"]
    if dwi_model == "Avanto":
        dwi_site = "BU"
    elif dwi_model == "Symphony":
        dwi_site = "UCSD"
    else:
        print(f'Error in processing sub-{vetsaid}. Unknown manufacturer model: {dwi_model}')
        sys.exit(1)
    return dwi_site


def split_epis(dwi_file):
    """
    Save the first 5 volumes from the dwi_file as epi files in the fmap folder. 
    """
    # Load the dwi file
    img = nib.load(dwi_file)
    data = img.get_fdata()
    fmap_dir = os.path.dirname(dwi_file).replace('dwi','fmap')
    if not os.path.isdir(fmap_dir):
        os.makedirs(fmap_dir)
    # Get name of epi file. 
    epi_fname = os.path.basename(dwi_file).replace('dwi', 'epi')
    epi_file = os.path.join(fmap_dir, epi_fname)
    # Save out the first 5 volumes as an epi file
    nib.save(nib.Nifti1Image(data[:, :, :, :5], img.affine), epi_file)
    return epi_file


def flip_ap_epi(epi_ap_file):
    """Flip the data of the AP epi in the phase encoding direction"""
    epi_ap_img = nib.load(epi_ap_file)
    epi_ap_data = epi_ap_img.get_fdata()
    epi_ap_data_flipped = np.flip(epi_ap_data, axis=1)
    nib.save(nib.Nifti1Image(epi_ap_data_flipped, epi_ap_img.affine), epi_ap_file)
    return epi_ap_file


def check_dwi_nvols(dwi_file, nvols, alt_nvols=None):
    """Check if the dwi file has the correct number of volumes. nvols is the number of volumes.
    alt_nvols is an alternative number of volumes that is also acceptable. If the dwi file has
    the correct number of volumes, return True. If not, return False."""
    img = nib.load(dwi_file)
    data = img.get_fdata()
    if data.shape[3] == nvols:
        return True
    elif alt_nvols is not None:
        if data.shape[3] == alt_nvols:
            return True
    return False


def create_single_shell_epi_jsons(epi_file, dwi_file):
    """Create json sidecars for the single-shell diffusion EPI files"""
    # Create json files for the epi files
    dwi_json = dwi_file.replace('dwi.nii.gz', 'dwi.json')
    epi_json = epi_file.replace('epi.nii.gz', 'epi.json')
    shutil.copyfile(dwi_json, epi_json)
    # Edit the epi json file to include the correct IntendedFor field
    with open(epi_json, 'r') as f:
        epi_json_dict = json.load(f)
    intended_for = dwi_file.replace(f"{bids_dir}/", "bids::")
    epi_json_dict["IntendedFor"] = intended_for
    with open(epi_json, 'w') as f:
        json.dump(epi_json_dict, f, indent=4)
    return epi_json


def split_dwi(single_dwi_file_new):
    """
    Split the dwi file into two files (one for each phase encoding direction). Integrated sequence will have 70 volumes.
    The first 35 volumes are in the AP direction and final 35 volumes are in the PA direction. For each direction, the
    first 5 volumes are b0 volumes and the final 30 volumes are diffusion weighted volumes.
    """
    img = nib.load(single_dwi_file_new)
    data = img.get_fdata()
    nib.save(nib.Nifti1Image(data[:, :, :, :35], img.affine), single_dwi_file_new)
    nib.save(nib.Nifti1Image(data[:, :, :, 35:], img.affine), single_dwi_file_new.replace('dir-AP', 'dir-PA'))
    return single_dwi_file_new, single_dwi_file_new.replace('dir-AP', 'dir-PA')


def split_bval_bvec(dwi_file):
    """
    Splits the bvals and bvecs files into two files (one for each phase encoding direction). 
    The first 35 values from each row should be saved out as the AP file and the final 35
    values from each row should be saved out as the PA file. Takes as input the name of 
    the dwi file in the AP direction to determine the names of the bvals and bvecs files.
    """
    bvals_file = dwi_file.replace('dwi.nii.gz', 'dwi.bval')
    bvecs_file = dwi_file.replace('dwi.nii.gz', 'dwi.bvec')
    bvals_file_AP = bvals_file.replace('dir-AP', 'dir-AP')
    bvecs_file_AP = bvecs_file.replace('dir-AP', 'dir-AP')
    bvals_file_PA = bvals_file.replace('dir-AP', 'dir-PA')
    bvecs_file_PA = bvecs_file.replace('dir-AP', 'dir-PA')
    with open(bvals_file, 'r') as f:
        bvals = f.readlines()
    with open(bvecs_file, 'r') as f:
        bvecs = f.readlines()
    bvals_AP = [row.split()[:35] for row in bvals]
    bvals_PA = [row.split()[35:] for row in bvals]
    bvecs_AP = [row.split()[:35] for row in bvecs]
    bvecs_PA = [row.split()[35:] for row in bvecs]
    bvals_AP_str = '\n'.join([' '.join(row) for row in bvals_AP])
    bvals_PA_str = '\n'.join([' '.join(row) for row in bvals_PA])
    bvecs_AP_str = '\n'.join([' '.join(row) for row in bvecs_AP])
    bvecs_PA_str = '\n'.join([' '.join(row) for row in bvecs_PA])
    with open(bvals_file_AP, 'w') as f:
        f.write(bvals_AP_str)
    with open(bvals_file_PA, 'w') as f:
        f.write(bvals_PA_str)
    with open(bvecs_file_AP, 'w') as f:
        f.write(bvecs_AP_str)
    with open(bvecs_file_PA, 'w') as f:
        f.write(bvecs_PA_str)
    return bvals_file_AP, bvals_file_PA, bvecs_file_AP, bvecs_file_PA



def edit_single_shell_dwi_jsons(single_dwi_json_file_AP):
    """Create json file for the new PA dwi file and edit jsons for both directions"""
    # Get name of PA json file
    single_dwi_json_file_PA = single_dwi_json_file_AP.replace('dir-AP', 'dir-PA')
    # Load the AP json file. Create a copy of this data for the PA json file
    with open(single_dwi_json_file_AP, 'r') as f:
        single_dwi_json_AP = json.load(f)
    single_dwi_json_PA = single_dwi_json_AP.copy()
    # Edit the AP json file to only include the first 35 items in SliceTiming
    single_dwi_json_AP["SliceTiming"] = single_dwi_json_AP["SliceTiming"][:35]
    # Edit the PA json file to only include the final 35 items in SliceTiming
    single_dwi_json_PA["SliceTiming"] = single_dwi_json_PA["SliceTiming"][35:]
    # Edit the PA json file PhaseEncodingDirection to be j
    single_dwi_json_PA["PhaseEncodingDirection"] = "j"
    # Save out the edited json files
    with open(single_dwi_json_file_AP, 'w') as f:
        json.dump(single_dwi_json_AP, f, indent=4)
    with open(single_dwi_json_file_PA, 'w') as f:
        json.dump(single_dwi_json_PA, f, indent=4)
    return single_dwi_json_file_AP, single_dwi_json_file_PA



def process_single_shell_data(vetsaid, bids_dir):
    """
    Process single-shell data. This includes:
    - Split dwi file into two files (one for each phase encoding direction)
    - Split the bvals and bvecs files into two files (one for each phase encoding direction)
    - Create json file for the new PA dwi file
    - Edit the json file for the PA epi file to include the correct IntendedFor field
    - Save out the b0 volumes from each phase encoding direction as epi files in the fmap folder
    - Create json files for the fmap files
    """
    # Get the site of data collection
    dwi_site = get_site(vetsaid, bids_dir)
    # If site is not BU or UCSD, return None
    if dwi_site not in ["BU", "UCSD"]:
        print(f'Error in processing sub-{vetsaid}. Unknown dwi site: {dwi_site}')
        return None
    single_dwi_file_new = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-01', 'dwi', f'sub-{vetsaid}_ses-01_dir-AP_dwi.nii.gz')
    # Check if the dwi file has the correct number of volumes
    if not check_dwi_nvols(single_dwi_file_new, 70):
        print(f'Error: Incorrect number of volumes in dwi file for subject {vetsaid}')
        return None
    # Split the dwi file into two files (one for each phase encoding direction)
    single_dwi_file_AP, single_dwi_file_PA = split_dwi(single_dwi_file_new)
    # Split the bvals and bvecs files into two files (one for each phase encoding direction)
    bvals_file_AP, bvals_file_PA, bvecs_file_AP, bvecs_file_PA = split_bval_bvec(single_dwi_file_new)
    # Create json file for the new PA dwi file and edit jsons for both directions
    single_dwi_json_file_AP, single_dwi_json_file_PA = edit_single_shell_dwi_jsons(single_dwi_file_new.replace('.nii.gz', '.json'))
    # Create epi files in the fmap folder from the first 5 volumes of each direction
    epi_ap_file = split_epis(single_dwi_file_AP)
    epi_pa_file = split_epis(single_dwi_file_PA)
    # Create json file for the epi files
    single_epi_ap_json = create_single_shell_epi_jsons(epi_ap_file, single_dwi_file_AP)
    single_epi_pa_json = create_single_shell_epi_jsons(epi_pa_file, single_dwi_file_PA)
    return single_dwi_file_AP, single_dwi_file_PA, epi_ap_file, epi_pa_file


def main(bids_dir, subject_list_file):
    # Read the subject list file
    with open(subject_list_file, 'r') as f:
        subject_list = f.read().splitlines()

    # Process each subject in the list
    for vetsaid in subject_list:
        print(f'Processing subject {vetsaid}')

        # Skip if the dwi folder does not exist
        if not check_dwi_folder(vetsaid, bids_dir):
            print(f'No dwi folder found for subject {vetsaid}, skipping...')
            continue

        # Check if the single-shell data exists
        if not check_single_shell_data(vetsaid, bids_dir):
            print(f'No single-shell data found in dwi folder for subject {vetsaid}, skipping...')
            continue     
        # Process the single-shell data    
        result = process_single_shell_data(vetsaid, bids_dir)
        if result is None:
            print(f'Error in processing subject {vetsaid}')
            continue
        print(f'Finished processing subject {vetsaid}')

if __name__ == '__main__':
    
    # Check if the correct number of arguments was provided
    if len(sys.argv) != 3:
        print('Usage: python 3_wave1_correct_dwi_data.py <bids_dir> <subject_list_file>')
        sys.exit(1)

    # Get the path to the BIDS data and the subject list file from the command line arguments
    bids_dir = sys.argv[1]
    subject_list_file = sys.argv[2]

    # Run the main function
    main(bids_dir, subject_list_file)

