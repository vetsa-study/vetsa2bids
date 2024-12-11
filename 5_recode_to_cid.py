"""
This script is used to recode files and folders in a BIDS format directory from VETSAID 
to CID. It takes in a key file containing the mapping from VETSAID to CID and recodes the 
files and folders in the BIDS directory. It should also replace any instances of VETSAID
in the json files with CID.
"""

import os
import argparse
import pandas as pd


def get_vetsaid_to_cid(key):
    """
    Returns a dictionary containing the mapping from VETSAID to CID.
    """
    vetsaid_to_cid = dict(zip(key['VETSAID'], key['CID']))
    return vetsaid_to_cid


def main(bids_dir, key_file, subjects_list=None):
    # Read in the key file. Both columns should be strings
    key = pd.read_csv(key_file, dtype=str)
    # Get the mapping from VETSAID to CID
    id_mapper = get_vetsaid_to_cid(key)
    
    # Get the list of subjects
    if subjects_list is None:
        subjects = [f for f in os.listdir(bids_dir) if f.startswith('sub-')]
    else:
        subjects = subjects_list
    
    # Loop through the subjects
    for subject in subjects:
        # Get the VETSAID
        vetsaid = subject.split('-')[1]
        # If VETSAID is not in the key file, skip it
        if vetsaid not in id_mapper:
            print(f'VETSAID {vetsaid} not in key file. Skipping...')
            continue
        # Get the CID
        cid = id_mapper[vetsaid]
        print(f'Recoding {vetsaid} to {cid}...')
        # Rename the subject folder
        os.rename(os.path.join(bids_dir, subject), os.path.join(bids_dir, 'sub-' + cid))
        # Get a list of all the files and folders in the subject folder containing VETSAID. Search recursively
        subject_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(os.path.join(bids_dir, 'sub-' + cid)) for f in filenames if vetsaid in f]
        # Loop through the files and folders
        for subject_file in subject_files:
            # Get the new file name
            new_file_name = subject_file.replace(vetsaid, cid)
            # Rename the file
            os.rename(subject_file, new_file_name)
            # If the file is a json file, search for substring matching VETSAID in the file contents and replace with CID
            if new_file_name.endswith('.json'):
                with open(new_file_name, 'r+') as f:
                    content = f.read()
                    content = content.replace(vetsaid, cid)
                    f.seek(0)
                    f.write(content)
                    f.truncate()


if __name__ == '__main__':
    # Get the command line arguments
    parser = argparse.ArgumentParser(description='Recodes VETSAID to CID for the VETSA dataset')
    parser.add_argument('-b', '--bids_dir', required=True, help='Path to the bids directory')
    parser.add_argument('-k', '--key', required=True, help='Path to the key file containing the mapping from VETSAID to CID')
    parser.add_argument('-s', '--subjects_list', nargs='*', help='List of subjects to process')
    args = parser.parse_args()
    bids_dir = args.bids_dir
    key_file = args.key
    subjects_list = args.subjects_list

    main(bids_dir, key_file, subjects_list)