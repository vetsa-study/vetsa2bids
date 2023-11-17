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
import nibabel as nib
import nipype.interfaces.fsl as fsl


def check_func_folder(vetsaid, bids_dir):
    """
    Checks if the func and fmap folders exist for the given subject.
    """
    func_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'func')
    fmap_dir = os.path.join(bids_dir, f'sub-{vetsaid}', 'fmap')
    if not os.path.isdir(func_dir):
        print(f'No func folder found for subject {vetsaid}')
        return False
    if not os.path.isdir(fmap_dir):
        print(f'No fmap folder found for subject {vetsaid}')
        return False
    return True


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