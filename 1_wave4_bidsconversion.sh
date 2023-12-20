#!/bin/bash
 
 #script for converting VETSA 4 raw DICOMS to BIDS format
 
 #Need to confirm all filenames are BIDS compatible!

 
 # Activate dcm2bids environment 
#conda activate dcm2bids

for vetsaid in `cat sublist_v4_fsdone_11072023.txt`
do
	echo "Starting conversion of ${vetsaid}..."

	#run dcm2bids.
	dcm2bids -d ~/netshare/SYNVETSACOPY/data/vetsa/VETSA4_orig/orig/${vetsaid}_v4/ -p ${vetsaid} -s ses-04 -c ~/netshare/M/MRI/BIDS/code/dcm2bids_config_v4.json -o ~/netshare/M/MRI/BIDS/data/
	
	echo "Finished converting ${vetsaid}."
done


	
	
