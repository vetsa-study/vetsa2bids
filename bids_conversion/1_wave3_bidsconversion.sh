#!/bin/bash
 
 #script for converting VETSA 3 raw DICOMS to BIDS format
 
 #Need to confirm all filenames are BIDS compatible!

 
 # Activate dcm2bids environment 
conda activate dcm2bids

for vetsaid in `cat sublist_v3.txt`
do
	echo "Starting conversion of ${vetsaid}..."

	#run dcm2bids.
	dcm2bids -d ~/netshare/SYNVETSACOPY/data/vetsa/VETSA3_orig/orig/${vetsaid}_v3/ -p ${vetsaid} -s ses-03 -c ~/netshare/M/MRI/BIDS/code/dcm2bids_config_v3_diffusionONLY.json -o ~/netshare/M/MRI/BIDS/data/
	
	echo "Finished converting ${vetsaid}."
done


	
	
