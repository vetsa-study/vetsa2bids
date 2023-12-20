#!/usr/bin/env python3
"""
This script performs some preliminary actions to fMRI data. The only steps required for 
data colected at BU is to edit json sidecars (1. add "TaskName"=="rest" field, 2. add
"IntendedFor" field to fmap jsons, 3. flip phase encoding direction of AP fmap to "j". 
The UCSD requires more substantial pre-processing steps because the data was acquired using 
an alternating pepolar sequence. Volumes were acquire with 2 phase encoding directions 
alternating each TR (A->P, P->A, A->P, P->A, etc). Additionally, A->P were written to disk 
in reverse order along the y-axis. Visually, this appears as the brain flipping orientation 
along the y-axis on each volume. 

The current script performs the following actions:
1. Checks that the functional run was acquired at UCSD and has the correct number of volumes.
2. Split the data into separate files for each phase encoding direction. Odd numbered volumes 
(1-based) are A->P, even are P->A.
3. Flip the data along the y-axis for the AP data so that it is in the same orientation as 
the PA data.
4. Creates json sidecar for each split file.
5. Merge the data back together in an interleaved order. Odd numbered volumes (1-based) should 
be A->P, even numbered volumes should be P->A. Creates a json file for this merged file. 

There may be several strategies to deal with the alternating phase encoding directions. Some 
examples are:
1. Process each phase encoding direction separately and then merge the data back together after 
all pre-processing steps are complete.
2. Perform distortion correction using TOPUP on each phase encoding direction separately 
(potentially after motion correction is also applied) and then merge the data back together prior
to further pre-processing steps.
3. Perform distortion correction using TOPUP on each phase encoding direction jointly (potentially
after motion correction is also applied). In this scenario, volumes with the same index in split 
file that were acquired consecutively are combined using the least squares resampliong. This would 
be akin to common approaches taken when multiple dwi series are acquired, and will result in an 
fmri timeseries with half the number of volumes as originally acquired. E.g., each new volume would
be the average of two volumes acquired consecutively.

Option 3 has been shown to result in reasonable quality distortion correction, but the reduced number
of volumes (and doubling of effective TR) may not be ideal for fMRI data. Pre-processed images 
resulting from options 1 and 2 should be closely inspected to ensure that the distortion correction
was successful.

If option 1 or 2 are chosen, it may be useful to additionally regress out the phase encoding
direction from the data to remove residual effects of these differences. 
"""

import os, sys
import numpy as np
import nibabel as nib
import nipype.interfaces.fsl as fsl
import json

def check_func_folder(vetsaid, bids_dir):
    """
    Checks if the func and fmap folders exist for the given subject.
    """
    func_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'func')
    fmap_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02','fmap')
    if not os.path.isdir(func_dir):
        print(f'No func folder found for subject {vetsaid}')
        return False
    if not os.path.isdir(fmap_dir):
        print(f'No fmap folder found for subject {vetsaid}')
        return False
    return True

def get_site(func_file):
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
        print(f'Error in processing {func_file}. Unknown manufacturer model: {func_model}')
        return None
    return func_site

def get_nvols(func_file):
    """Get the number of volumes from the func file"""
    img = nib.load(func_file)
    data = img.get_fdata()
    return data.shape[3]


def split_func_run(func_file): 
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


def merge_func_files(func_file_AP, func_file_PA):
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
    # Save the merged data. This overwrites original bold file.
    merged_func_file = func_file_AP.replace('_dir-AP_bold.nii.gz', '_bold.nii.gz')
    nib.save(nib.Nifti1Image(merged_data, img_AP.affine, img_AP.header), merged_func_file)
    return merged_func_file

def create_split_func_json(func_file_AP, func_file_PA, func_json_file):
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

def add_intended(fmap_json, intended_for):
    """
    Adds "IntendedFor" field to the json sidecar for the given fieldmap listing corresponding
    functional run. The path should be relative to the subject directory and start with
    bids:: (e.g., bids::ses-02/func/sub-<vetsaid>_ses-02_task-rest_bold.nii.gz). If the
    fmap json file does not exist, skip.
    """
    if not os.path.isfile(fmap_json):
        print(f'No json file found for {fmap_json}. Skipping...')
        return
    with open(fmap_json, 'r') as f:
        fmap_json = json.load(f)
    fmap_json['IntendedFor'] = intended_for
    with open(fmap_json, 'w') as f:
        json.dump(fmap_json, f, indent=4)

def edit_ucsd_bold_json(func_json_file):
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


def process_ucsd_func(vetsaid, func_file):
    func_nvols = get_nvols(func_file)
    if func_nvols != 100:
        print(f'Error in processing {func_file}. Functional run has {func_nvols} volumes, not 100.')
        return None
    # Split the functional run into separate files for each phase encoding direction
    func_file_AP, func_file_PA = split_func_run(func_file)
    # Create json sidecar for each split file
    func_json_file_AP, func_json_file_PA = create_split_func_json(func_file_AP, func_file_PA, func_file.replace('.nii.gz', '.json'))
    # Merge the data back together
    merged_func_file = merge_func_files(func_file_AP, func_file_PA)
    # Remove phase encoding direction from func json files
    corrected_func_json = edit_ucsd_bold_json(func_file.replace('.nii.gz', '.json'))
    # Add IntendedFor field to fmap json files
    fmap_AP_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap', f'sub-{vetsaid}_ses-02_acq-func_dir-AP_epi.json')
    intended_for_AP = func_file_AP.replace(f"{bids_dir}/", "bids::")
    add_intended(fmap_AP_json, intended_for_AP)
    fmap_PA_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap', f'sub-{vetsaid}_ses-02_acq-func_dir-PA_epi.json')
    intended_for_PA = func_file_PA.replace(f"{bids_dir}/", "bids::")
    add_intended(fmap_PA_json, intended_for_PA)
    # Return the merged func file and the corrected func json file    
    return merged_func_file, corrected_func_json


def edit_BU_bold_json(func_json_file):
    """
    Edits json sidecar of func file. Adds TaskName field to the func json file. 
    """
    # Add TaskName field to the func json file
    with open(func_json_file, 'r') as f:
        func_json = json.load(f)
    func_json['TaskName'] = 'rest'
    # Save the edited json file
    with open(func_json_file, 'w') as f:
        json.dump(func_json, f, indent=4)
    return func_json_file


def process_bu_func(vetsaid, func_file):
    """
    Adds the "TaskName" field to the json sidecar for the given functional run.
    Adds "IntendedFor" field to the json sidecar for the given fieldmap.
    Change PhaseEncodingDirection to j for AP fieldmap.
    """
    # Edit the json sidecar for the functional run
    func_json_file = func_file.replace('.nii.gz', '.json')
    func_json_file = edit_BU_bold_json(func_json_file)
    # Edit the json sidecar for the AP fieldmap
    fmap_AP_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap', f'sub-{vetsaid}_ses-02_acq-func_dir-AP_epi.json')
    intended_for = func_file.replace(f"{bids_dir}/", "bids::")
    add_intended(fmap_AP_json, intended_for)
    intended_for = func_file.replace(f"{bids_dir}/", "bids::")
    with open(fmap_AP_json, 'r') as f:
        fmap_AP_data = json.load(f)
    fmap_AP_data['PhaseEncodingDirection'] = "j"
    with open(fmap_AP_json, 'w') as f:
        json.dump(fmap_AP_data, f, indent=4)
    # Edit the json sidecar for the AP fieldmap
    fmap_PA_json = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap', f'sub-{vetsaid}_ses-02_acq-func_dir-PA_epi.json')
    add_intended(fmap_PA_json, intended_for)
    return func_file, func_json_file


def process_func_run(vetsaid, bids_dir):
    """
    Processes the functional run for the given subject.
    """
    # Get the path to the functional run
    func_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'func')
    func_file = os.path.join(func_dir, f'sub-{vetsaid}_ses-02_task-rest_bold.nii.gz')
    # Get site where data was collected
    func_site = get_site(func_file)
    if func_site == "BU":
        return process_bu_func(vetsaid, func_file)
    elif func_site == "UCSD":
        return process_ucsd_func(vetsaid, func_file)
    else:
        print(f'Error in processing {func_file}. Unknown site')
        return None


def main(bids_dir, subject_list_file):
    # Read the subject list file
    with open(subject_list_file, 'r') as f:
        subject_list = f.read().splitlines()

        # Initialize empty lists for successful and unsuccessful subjects
        successful_subjects = []
        unsuccessful_subjects = []

        # Process each subject in the list
        for vetsaid in subject_list:
            print(f'Start processing subject {vetsaid}')

            # Check if the func and fmap folders exist
            if not check_func_folder(vetsaid, bids_dir):
                print(f'Functional folders for {vetsaid} not found, skipping...')
                unsuccessful_subjects.append(vetsaid)
                continue

            # Process each functional run
            result = process_func_run(vetsaid, bids_dir)
            if result is None:
                unsuccessful_subjects.append(vetsaid)
                continue
            print(f'Finished processing functional run for subject {vetsaid} successfully')
            successful_subjects.append(vetsaid)

        # Write the lists to files at the end of the script
        with open(os.path.join(bids_dir, 'successful_subjects.txt'), 'w') as f:
            for subject in successful_subjects:
                f.write(f'{subject}\n')

        with open(os.path.join(bids_dir, 'unsuccessful_subjects.txt'), 'w') as f:
            for subject in unsuccessful_subjects:
                f.write(f'{subject}\n')

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