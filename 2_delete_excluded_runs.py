#!/usr/bin/env python3

"""
This script deletes files in a BIDS dataset based on a csv file with the
following columns:
    SubjectID
    session
    data_type
    use_run

- The variable session should be in format "ses-01", "ses-02", etc.
- The variable data_type should be in format "anat", "dwi", "func", etc. and
is used to specify the subdirectory under each subject and session.
- The variable use_run should contain all other parts of the filename after
the session, but before the file extension. For example, if the filename is
"sub-01_ses-01_acq-1_run-01_T1w.nii.gz", then the use_run should be
"acq-1_run-01_T1w".

The script will then delete all remaining files with the same SubjectID and
session, but with a "run-##_" in the filename, where ## is the run number. 

Usage:
    python delete_excluded_runs.py <csv_file> <bids_directory>

"""

import os, sys
import pandas as pd
import re
import datetime

# Create function to load csv into pandas dataframe
def load_csv(csv_file):
    df = pd.read_csv(csv_file)
    return df

# Create function to generate BIDS filename from columns
def generate_bids_filename(row):
    return os.path.join(bids_dir, "sub-{SubjectID}", "{session}", "{data_type}", "sub-{SubjectID}_{session}_{use_run}").format(**row)

# Rename each row in filename column to the new_filename column by removing
# the string "run-[0-9][0-9]_" from the filename. 
def rename_files(row):
    # Get the base filename by removing the extension
    base_filename = os.path.basename(row["filename"])

    # Find all files that match the base filename
    files = [f for f in os.listdir(os.path.dirname(row["filename"])) if f.startswith(base_filename)]

    # Rename each file that matches the base filename
    for file in files:
        old_filepath = os.path.join(os.path.dirname(row["filename"]), file)
        new_filepath = os.path.join(os.path.dirname(row["filename"]), re.sub(r"run-[0-9][0-9]_", "", file))
        os.rename(old_filepath, new_filepath)

    # Return the new filename
    return os.path.join(os.path.dirname(row["filename"]), re.sub(r"run-[0-9][0-9]_", "", row["filename"]))

# Delete all files in the specified directory and its subdirectories that contain "run-##_"
def delete_files(directory, subject, session):
    deleted_files = []
    
    # Loop over all files in the specified directory and its subdirectories
    for root, dirs, files in os.walk(os.path.join(directory, f"sub-{subject}", session)):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            # Check if the filename contains "run-##_"
            if re.search(r"run-[0-9][0-9]_", filename):
                # Delete the file
                print(f"Deleting {filepath}")
                os.remove(filepath)
                deleted_files.append(filepath)
    
    return deleted_files

# Run the function
def main(csv_file, bids_dir):
    # Load the csv file
    df = load_csv(csv_file)

    # Generate filenames for each row in the dataframe
    df["filename"] = df.apply(generate_bids_filename, axis=1)

    # Rename files for each row in the dataframe
    df["new_filename"] = df.apply(rename_files, axis=1)

    # Delete unused run files within the same session for each subject
    for subject, session in df[["SubjectID", "session"]].drop_duplicates().values:
        deleted_files = delete_files(bids_dir, subject, session)

    # Save the dataframe to a csv file in the same directory as the input csv file
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    output_filename = f"deleted_files_{timestamp}.csv"
    df.to_csv(os.path.join(os.path.dirname(csv_file), output_filename), index=False)

if __name__ == "__main__":
        # Check if the script is called with the correct number of arguments
    if len(sys.argv) != 3:
        print("Usage: python delete_excluded_runs.py <csv_file> <bids_directory>")
        sys.exit(1)

    # Get the arguments
    csv_file = sys.argv[1]
    bids_dir = sys.argv[2]

    # Run the main function
    main(csv_file, bids_dir)