#!/usr/bin/env python3
"""
This script applies distortion correction to the fMRI data collected at UCSD. The
data was collected using a pepolar sequence with 2 phase encoding directions alternating
each TR (A->P, P->A, etc). This requires splitting the data into separate files, applying TOPUP distortion 
correction, and then merging the data back together. The steps are as follows:
1. Split the data into separate files for each phase encoding direction. Odd numbered volumes (1-based) are A->P, even are P->A.
2. Calculate distortion correction parameters using TOPUP.
3. Apply distortion correction to each phase encoding direction separately.
4. Merge the data back together.
5. Remove phase encoding direction from func json files. 
"""

import os
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
        sys.exit(1)
    return func_site

def get_nvols(func_file):
    """Get the number of volumes from the func file"""
    img = nib.load(func_file)
    data = img.get_fdata()
    return data.shape[3]

def check_func_data(func_file):
    """
    Checks that the functional run was acquired at UCSD and has the correct number of volumes.
    It should have 100 volumes.
    """
    # Check that the functional run was acquired at UCSD
    func_site = get_site(func_file)
    if func_site != "UCSD":
        print(f'Error in processing {func_file}. Functional run was acquired at acquired at {func_site}, not UCSD.')
        return False
    # Check that there are 100 volumes
    func_nvols = get_nvols(func_file)
    if func_nvols != 100:
        print(f'Error in processing {func_file}. Functional run has {func_nvols} volumes, not 100.')
        return False
    return True

def combine_fmaps(fmap_file_AP, fmap_file_PA):
    """Combines the AP and PA fieldmaps into a single file"""
    fmap_combined = fmap_file_AP.replace('_dir-AP_epi.nii.gz', '_desc-combined_epi.nii.gz')
    fsl_merge = fsl.Merge()
    fsl_merge.inputs.in_files = [fmap_file_AP, fmap_file_PA]
    fsl_merge.inputs.dimension = 't'
    fsl_merge.inputs.merged_file = fmap_combined
    fsl_merge.run()
    return fmap_combined


def create_acqparams_file(fmap_file_AP):
    """Creates the acqparams file for TOPUP. Get total readout time from AP fmap json file.
    Phase encoding direction will be 1 for AP and -1 for PA."""
    fmap_json_file = fmap_file_AP.replace('_dir-AP_epi.nii.gz', '_dir-AP_epi.json')
    with open(fmap_json_file, 'r') as f:
        fmap_json = json.load(f)
    total_readout_time = fmap_json["TotalReadoutTime"]
    acqparams_file = fmap_json_file.replace('_dir-AP_epi.json', '_acqparams.txt')
    with open(acqparams_file, 'w') as f:
        f.write(f'0 1 0 {total_readout_time}\n')
        f.write(f'0 -1 0 {total_readout_time}\n')
    return acqparams_file


def create_topup_input(fmap_file_AP, fmap_file_PA):
    """Creates input files needed for TOPUP. This will include:
        1. A combined fieldmap file with both AP and PA data
        2. An acqparams file with the total readout time for the functional run and phase encode directions
    Requires combining the AP and PA fieldmaps into a single file. The combined file should have the same
    dimensions as the functional data. Phase encoding direction will be 1 for AP and -1 for PA.
    """
    # Combine the AP and PA fieldmaps into a single file
    fmap_combined = combine_fmaps(fmap_file_AP, fmap_file_PA)
    # Create the acqparams file
    acqparams_file = create_acqparams_file(fmap_file_AP)
    return fmap_combined, acqparams_file


def calc_topup_params(fmap_combined, acqparams_file):
    """
    Calculates distortion correction parameters using TOPUP. 
    Requires a combined fieldmap file and an acqparams file.
    """
    # Note: When nipype interface for TOPUP takes prefixes for 
    # outputs, it uses os.path.abspath() to create filename and 
    # path. This causes the output files to be saved in the 
    # current working directory. To get around this, change the 
    # current working directory to the fmap directory and only 
    # provide base filename as prefixes.
    #
    # Save the current working directory
    cwd = os.getcwd()
    # Change the current working directory to the fmap directory
    fmap_dir = os.path.dirname(fmap_combined)
    os.chdir(fmap_dir) 
    # Calculate distortion correction parameters using TOPUP
    fsl_topup = fsl.TOPUP()
    fsl_topup.inputs.in_file = fmap_combined
    fsl_topup.inputs.encoding_file = acqparams_file
    fsl_topup.inputs.out_base = os.path.basename(fmap_combined).replace('_desc-combined_epi.nii.gz', '_desc-topup')
    fsl_topup.inputs.out_corrected = os.path.basename(fmap_combined).replace('_desc-combined_epi.nii.gz', '_desc-topup_epi.nii.gz')
    fsl_topup.inputs.out_field = os.path.basename(fmap_combined).replace('_desc-combined_epi.nii.gz', '_desc-topup_fieldcoef.nii.gz')
    fsl_topup.inputs.out_logfile = os.path.basename(fmap_combined).replace('_desc-combined_epi.nii.gz', '_desc-topup.log')
    # Only provide filename for jac, mat and warp outputs
    fsl_topup.inputs.out_jac_prefix = os.path.basename(fmap_combined).replace('_desc-combined_epi.nii.gz', '_desc-topup_jac')
    fsl_topup.inputs.out_mat_prefix = os.path.basename(fmap_combined).replace('_desc-combined_epi.nii.gz', '_desc-topup_xfm')
    fsl_topup.inputs.out_warp_prefix = os.path.basename(fmap_combined).replace('_desc-combined_epi.nii.gz', '_desc-topup_warpfield')
    fsl_topup = fsl_topup.run()
    # Change the current working directory back to the original directory
    os.chdir(cwd)
    return fsl_topup


def apply_topup(func_file, topup_params, in_index):
    """
    Apply TOPUP distortion correction to the functional data. Uses the object returned by calc_topup_params().
    to get relevant parameters.
    UCSD fMRI data should use in_index=[1] for AP and in_index=[2] for PA.
    """
    applytopup = fsl.ApplyTOPUP()
    applytopup.inputs.in_files = func_file
    applytopup.inputs.encoding_file = topup_params.inputs['encoding_file']
    applytopup.inputs.in_index = in_index
    applytopup.inputs.in_topup_fieldcoef = topup_params.outputs.out_field
    applytopup.inputs.in_topup_movpar = topup_params.outputs.out_movpar
    applytopup.inputs.out_corrected = func_file.replace('_bold.nii.gz', '_desc-topup_bold.nii.gz')
    applytopup.inputs.method = "jac"
    applytopup.inputs.output_type = "NIFTI_GZ"
    applytopup = applytopup.run()
    return applytopup.outputs.out_corrected


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
    # Save the merged data
    merged_func_file = func_file_AP.replace('_dir-AP', '')
    nib.save(nib.Nifti1Image(merged_data, img_AP.affine, img_AP.header), merged_func_file)
    return merged_func_file


def edit_bold_json(func_json_file):
    """
    Edits json sidecar of func file. 
    1. Removes the phase encoding direction from the func json file.
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


def process_func_run(vetsaid, bids_dir):
    """
    Processes the functional run for the given subject.
    """
    # Get the path to the functional run
    func_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'func')
    func_file = os.path.join(func_dir, f'sub-{vetsaid}_ses-02_task-rest_bold.nii.gz')
    # Get the path to the fieldmap
    fmap_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'ses-02', 'fmap')
    fmap_file_AP = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-02_task-rest_dir-AP_epi.nii.gz')
    fmap_file_PA = os.path.join(fmap_dir, f'sub-{vetsaid}_ses-02_task-rest_dir-PA_epi.nii.gz')
    # Check that func data was acquired at UCSD and has correct number of volumes
    func_check_correct = check_func_data(func_file)
    if not func_check_correct:
        return
    # Create topup input. 
    fmap_combined, acqparams_file = create_topup_input(fmap_file_AP, fmap_file_PA)
    # Calculate distortion correction parameters using TOPUP
    topup_params = calc_topup_params(fmap_combined, acqparams_file)
    # Split the functional run into separate files for each phase encoding direction
    func_file_AP, func_file_PA = split_func_run(func_file)
    # Apply distortion correction to each phase encoding direction separately
    corrected_func_files_AP = apply_topup(func_file_AP, topup_params, [1])
    corrected_func_files_PA = apply_topup(func_file_PA, topup_params, [2])
    # Merge the data back together
    merged_func_file = merge_func_files(corrected_func_files_AP, corrected_func_files_PA)
    # Remove phase encoding direction from func json files
    corrected_func_json = edit_bold_json(func_file.replace('.nii.gz', '.json'))
    return merged_func_file, corrected_func_json


def main(bids_dir, subject_list_file):
    # Read the subject list file
    with open(subject_list_file, 'r') as f:
        subject_list = f.read().splitlines()

    # Process each subject in the list
    for vetsaid in subject_list:
        print(f'Processing subject {vetsaid}')

        # Check if the func and fmap folders exist
        if not check_func_folder(vetsaid, bids_dir):
            continue

        # Process each functional run
        merged_func_file, corrected_func_json = process_func_run(vetsaid, bids_dir)



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