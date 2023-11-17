#!/bin/bash
 
 #script for converting VETSA 1 raw DICOMS to BIDS format

 
 # Activate dcm2bids environment 
#conda activate dcm2bids

for vetsaid in `cat sublist_v1.txt`
do
	echo "Starting conversion of ${vetsaid}..."

	#run dcm2bids.
	dcm2bids -d ~/netshare/SYNVETSACOPY/data/vetsa/VETSA1/orig/${vetsaid}/ -p ${vetsaid} -s ses-01 -c ~/netshare/M/MRI/BIDS/code/dcm2bids_config_v1.json -o ~/netshare/M/MRI/BIDS/data/
	
	echo "Finished converting ${vetsaid}."
done


	
	
